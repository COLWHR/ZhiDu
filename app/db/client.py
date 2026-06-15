from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import libsql_client
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    columns: list[str] | None = None
    rowcount: int = 0

    def fetchone(self) -> Optional[dict[str, Any]]:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self.rows)

    def __iter__(self):
        return iter(self.rows)


def _is_select_like(query: str) -> bool:
    normalized = " ".join((query or "").strip().lower().split())
    return normalized.startswith("select") or normalized.startswith("with") or " returning " in f" {normalized} "


def _rows_to_dicts(rows: Iterable[Any], columns: Optional[list[str]] = None) -> list[dict[str, Any]]:
    materialized = list(rows)
    if not materialized:
        return []

    if isinstance(materialized[0], dict):
        return [dict(row) for row in materialized]

    if columns:
        return [dict(zip(columns, row)) for row in materialized]

    return [dict(row) if hasattr(row, "keys") else {"value": row} for row in materialized]


def _wrap_result(raw: Any) -> QueryResult:
    if raw is None:
        return QueryResult(rows=[])

    if isinstance(raw, QueryResult):
        return raw

    if isinstance(raw, list):
        return QueryResult(rows=_rows_to_dicts(raw), rowcount=len(raw))

    if hasattr(raw, "rows"):
        columns = list(getattr(raw, "columns", []) or [])
        rows = _rows_to_dicts(getattr(raw, "rows", []), columns=columns or None)
        return QueryResult(rows=rows, columns=columns or None, rowcount=len(rows))

    if hasattr(raw, "fetchall"):
        try:
            fetched = raw.fetchall()
        except Exception:
            fetched = []
        rows = _rows_to_dicts(fetched)
        rowcount = getattr(raw, "rowcount", len(rows)) or len(rows)
        return QueryResult(rows=rows, rowcount=rowcount)

    return QueryResult(rows=[])


class PostgresTransaction:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, query, params=None):
        query = query.replace("?", "%s")
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall() if _is_select_like(query) else []
        return QueryResult(rows=_rows_to_dicts(rows), rowcount=self.cursor.rowcount)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()


class PostgresClient:
    def __init__(self, url):
        self.url = url
        self.conn = psycopg2.connect(url)
        self.conn.autocommit = True

    def execute(self, query, params=None):
        query = query.replace("?", "%s")
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall() if _is_select_like(query) else []
            return QueryResult(rows=_rows_to_dicts(rows), rowcount=cur.rowcount)

    def transaction(self):
        self.conn.autocommit = False
        return PostgresTransaction(self.conn)

    def close(self):
        self.conn.close()


class RetryingTransaction:
    """Wrapper for libsql transactions with lock retry."""

    def __init__(self, tx):
        self._tx = tx

    def execute(self, stmt, args=None):
        max_retries = 5
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                return _wrap_result(self._tx.execute(stmt, args))
            except Exception as exc:
                error_msg = str(exc).lower()
                if "database is locked" in error_msg and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Database locked in transaction, retrying in %.2fs (attempt %s/%s)",
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue
                raise

    def commit(self):
        if hasattr(self._tx, "commit"):
            return self._tx.commit()

    def __getattr__(self, name):
        return getattr(self._tx, name)


class RetryingLibsqlClient:
    """Wrapper around libsql_client with retry logic for lock errors."""

    def __init__(self, client):
        self._client = client

    def execute(self, stmt, args=None):
        max_retries = 5
        base_delay = 0.1

        for attempt in range(max_retries):
            try:
                return _wrap_result(self._client.execute(stmt, args))
            except Exception as exc:
                error_msg = str(exc).lower()
                if "database is locked" in error_msg and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Database locked, retrying in %.2fs (attempt %s/%s)",
                        delay,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue
                raise

    @contextmanager
    def transaction(self):
        with self._client.transaction() as tx:
            yield RetryingTransaction(tx)

    def close(self):
        return self._client.close()

    def __getattr__(self, name):
        return getattr(self._client, name)


class Database:
    def __init__(self):
        self.url = settings.DATABASE_URL
        self.auth_token = settings.TURSO_AUTH_TOKEN
        self.is_postgres = False
        self.is_remote = False
        self._sync_backend_flags()

    def _sync_backend_flags(self):
        self.is_postgres = self.url.startswith("postgresql://") or self.url.startswith("postgres://")
        self.is_remote = self.url.startswith("libsql://") or self.url.startswith("https://")

    def get_connection(self):
        self._sync_backend_flags()

        if self.is_postgres:
            return PostgresClient(self.url)

        token = self.auth_token if self.is_remote else None

        if not self.is_remote and self.url.startswith("file:"):
            db_path = self.url.replace("file:", "")
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    logger.info("Created database directory: %s", db_dir)
                except OSError as exc:
                    logger.warning("Failed to create database directory: %s", exc)

        try:
            client = libsql_client.create_client_sync(
                url=self.url,
                auth_token=token,
            )
        except Exception as exc:
            logger.error("Failed to create database client: %s", exc)
            raise

        if not self.is_remote:
            try:
                client.execute("PRAGMA journal_mode = WAL")
                client.execute("PRAGMA synchronous = NORMAL")
                client.execute("PRAGMA cache_size = -10000")
                client.execute("PRAGMA foreign_keys = ON")
                client.execute("PRAGMA busy_timeout = 30000")
            except Exception as exc:
                logger.warning("Failed to set SQLite PRAGMA: %s", exc)

        return RetryingLibsqlClient(client)

    def init_db(self, schema_path="app/db/schema.sql"):
        self._sync_backend_flags()

        if self.is_postgres:
            logger.info("PostgreSQL detected, skipping schema.sql init. Use Alembic or schema_pg.sql.")
            return

        if not os.path.exists(schema_path):
            logger.warning("Schema file not found: %s", schema_path)
            return

        conn = self.get_connection()
        try:
            with open(schema_path, "r", encoding="utf-8") as handle:
                script = handle.read()
                statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]
                for stmt in statements:
                    conn.execute(stmt)
            logger.info("Database initialized successfully.")
        except Exception as exc:
            logger.error("Failed to initialize database: %s", exc)
        finally:
            conn.close()


db_manager = Database()


def get_db():
    db = db_manager.get_connection()
    try:
        yield db
    finally:
        db.close()


class RowObject:
    def __init__(self, data):
        self.__dict__.update(data)


def fetch_one(rs):
    if rs is None:
        return None
    if isinstance(rs, QueryResult):
        row = rs.fetchone()
        return RowObject(row) if row else None
    if isinstance(rs, list):
        return RowObject(rs[0]) if rs else None
    if hasattr(rs, "rows"):
        rows = getattr(rs, "rows", [])
        return RowObject(dict(zip(rs.columns, rows[0]))) if rows else None
    if hasattr(rs, "fetchone"):
        row = rs.fetchone()
        return RowObject(dict(row)) if row else None
    return None


def fetch_all(rs):
    if rs is None:
        return []
    if isinstance(rs, QueryResult):
        return [RowObject(row) for row in rs.fetchall()]
    if isinstance(rs, list):
        return [RowObject(r) for r in rs]
    if hasattr(rs, "rows"):
        return [RowObject(dict(zip(rs.columns, row))) for row in rs.rows]
    if hasattr(rs, "fetchall"):
        return [RowObject(dict(row)) for row in rs.fetchall()]
    return []


@contextmanager
def db_transaction(db):
    """
    Unified transaction context manager.
    - If `db` is a connection (has `.transaction()`), starts a new transaction.
    - If `db` is already a transaction object, reuses it.
    """
    if hasattr(db, "transaction") and callable(db.transaction):
        with db.transaction() as tx:
            yield tx
    else:
        yield db


def db_execute_commit(db, query, params=None):
    """
    Execute a query inside a transaction and return the normalized result.
    """
    if hasattr(db, "transaction") and callable(db.transaction):
        with db.transaction() as tx:
            result = tx.execute(query, params)
            if hasattr(tx, "commit"):
                tx.commit()
            elif hasattr(db, "commit"):
                db.commit()
            return result
    return db.execute(query, params)
