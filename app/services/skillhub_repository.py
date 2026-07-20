from __future__ import annotations

import json
import logging
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

logger = logging.getLogger(__name__)

SKILLHUB_API_BASE = "https://api.skillhub.cn"
SKILLHUB_WEB_BASE = "https://www.skillhub.cn"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILL_REPOSITORY_ROOT = PROJECT_ROOT / "skills"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or "unknown-skill"


def _json_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _requires_api_key(item: dict[str, Any]) -> bool:
    labels = item.get("labels")
    if not isinstance(labels, dict):
        return False
    return str(labels.get("requires_api_key", "")).strip().lower() == "true"


def map_skillhub_summary(item: dict[str, Any], rank: int) -> dict[str, Any]:
    slug = _safe_slug(_as_str(item.get("slug") or item.get("name")))
    sub_categories = _json_list(item.get("subCategories"))
    sub_category_names = [
        _as_str(entry.get("name"))
        for entry in sub_categories
        if isinstance(entry, dict) and _as_str(entry.get("name"))
    ]
    description = _as_str(item.get("description_zh") or item.get("description") or item.get("summary_zh") or item.get("summary"))
    source_url = f"{SKILLHUB_WEB_BASE}/skills/{slug}"
    required_tools = ["external_api_key"] if _requires_api_key(item) else []

    return {
        "skill_key": f"skillhub.{slug}",
        "name": _as_str(item.get("name") or item.get("displayName") or slug, slug),
        "category": _as_str(item.get("category"), "skillhub"),
        "description": description,
        "input_modalities": ["text"],
        "output_types": ["text"],
        "required_models": ["fast", "reasoning"],
        "required_tools": required_tools,
        "params_schema": {},
        "permission_scope": ["skillhub"],
        "cost_level": "medium" if required_tools else "low",
        "status": "active",
        "source": "skillhub",
        "source_url": source_url,
        "source_slug": slug,
        "source_rank": rank,
        "source_owner": _as_str(item.get("ownerName") or item.get("owner")),
        "source_version": _as_str(item.get("version") or item.get("latestVersion", {}).get("version")),
        "icon_url": _as_str(item.get("iconUrl")),
        "downloads": _as_int(item.get("downloads")),
        "installs": _as_int(item.get("installs")),
        "stars": _as_int(item.get("stars")),
        "score": item.get("score") or 0,
        "sub_categories": sub_category_names,
        "synced_at": _utc_now_iso(),
    }


def _merge_detail(skill: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    detail_skill = detail.get("skill") if isinstance(detail.get("skill"), dict) else {}
    latest = detail.get("latestVersion") if isinstance(detail.get("latestVersion"), dict) else {}
    security = detail.get("securityReports") if isinstance(detail.get("securityReports"), dict) else {}
    merged = dict(skill)

    summary = _as_str(detail_skill.get("summary_zh") or detail_skill.get("summary"))
    if summary:
        merged["description"] = summary
    if latest.get("version"):
        merged["source_version"] = _as_str(latest.get("version"))
    if security:
        merged["security_reports"] = security
    return merged


def _iter_zip_members(archive: zipfile.ZipFile) -> Iterable[zipfile.ZipInfo]:
    for info in archive.infolist():
        normalized = Path(info.filename)
        parts = normalized.parts
        if info.is_dir() or not parts:
            continue
        if any(part in {"", ".", ".."} for part in parts):
            continue
        if Path(info.filename).is_absolute():
            continue
        yield info


def _extract_zip_safely(content: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(__import__("io").BytesIO(content)) as archive:
        for info in _iter_zip_members(archive):
            target = (destination / info.filename).resolve()
            if not str(target).startswith(str(destination.resolve())):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as handle:
                shutil.copyfileobj(source, handle)


def _write_manifest(skill_dir: Path, skill: dict[str, Any]) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "skill.json").write_text(
        json.dumps(skill, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_repository_skills(root: Path | str = DEFAULT_SKILL_REPOSITORY_ROOT) -> list[dict[str, Any]]:
    repo_root = Path(root)
    if not repo_root.exists():
        return []

    skills: list[dict[str, Any]] = []
    for manifest in sorted(repo_root.glob("*/*/skill.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Skipping invalid skill manifest %s: %s", manifest, exc)
            continue
        if isinstance(data, dict) and data.get("skill_key") and data.get("name"):
            skills.append(data)
    return sorted(skills, key=lambda skill: (_as_int(skill.get("source_rank"), 999999), _as_str(skill.get("skill_key"))))


def fetch_skillhub_summaries(limit: int = 50, session: Any | None = None) -> list[dict[str, Any]]:
    http = session or requests.Session()
    page_size = max(1, min(int(limit), 100))
    response = http.get(f"{SKILLHUB_API_BASE}/api/skills?sortBy=score&pageSize={page_size}", timeout=30)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else {}
    items = data.get("skills") if isinstance(data, dict) else []
    return _json_list(items)[:page_size]


def sync_skillhub_skills(
    root: Path | str = DEFAULT_SKILL_REPOSITORY_ROOT,
    limit: int = 50,
    session: Any | None = None,
    download_packages: bool = True,
) -> list[dict[str, Any]]:
    repo_root = Path(root)
    http = session or requests.Session()
    synced: list[dict[str, Any]] = []

    for rank, item in enumerate(fetch_skillhub_summaries(limit=limit, session=http), start=1):
        if not isinstance(item, dict):
            continue
        skill = map_skillhub_summary(item, rank=rank)
        slug = skill["source_slug"]
        skill_dir = repo_root / "skillhub" / slug

        try:
            detail_response = http.get(f"{SKILLHUB_API_BASE}/api/v1/skills/{slug}", timeout=30)
            detail_response.raise_for_status()
            skill = _merge_detail(skill, detail_response.json())
        except Exception as exc:
            logger.warning("Failed to fetch SkillHub detail for %s: %s", slug, exc)

        if download_packages:
            try:
                package_response = http.get(f"{SKILLHUB_API_BASE}/api/v1/download?slug={slug}", timeout=60)
                package_response.raise_for_status()
                _extract_zip_safely(package_response.content, skill_dir)
            except Exception as exc:
                logger.warning("Failed to download SkillHub package for %s: %s", slug, exc)

        _write_manifest(skill_dir, skill)
        synced.append(skill)

    return synced
