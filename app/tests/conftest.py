import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.db.client import get_db, db_manager
from app.core.cache import cache_service
from app.main import app as fastapi_app

@pytest.fixture(scope="function")
def db(tmp_path):
    test_db_path = Path(tmp_path) / "test_madf.db"
    test_db_url = f"file:{test_db_path}"

    cache_service.delete_keys_pattern("*")

    original_url = db_manager.url
    original_is_remote = db_manager.is_remote
    original_is_postgres = db_manager.is_postgres

    db_manager.url = test_db_url
    db_manager.is_remote = False
    db_manager.is_postgres = False

    db_manager.init_db()
    client = db_manager.get_connection()
    try:
        yield client
    finally:
        client.close()
        db_manager.url = original_url
        db_manager.is_remote = original_is_remote
        db_manager.is_postgres = original_is_postgres
        cache_service.delete_keys_pattern("*")

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        client = db_manager.get_connection()
        try:
            yield client
        finally:
            client.close()
    
    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
