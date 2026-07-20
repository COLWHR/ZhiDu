from __future__ import annotations

import io
import zipfile


class FakeResponse:
    def __init__(self, payload=None, content: bytes = b"", headers=None):
        self._payload = payload
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self):
        self.urls: list[str] = []

    def get(self, url, timeout=30):
        self.urls.append(url)
        if url.endswith("/api/skills?sortBy=score&pageSize=1"):
            return FakeResponse(
                {
                    "code": 0,
                    "data": {
                        "skills": [
                            {
                                "slug": "web-tools-guide",
                                "name": "web-tools-guide",
                                "category": "knowledge-management",
                                "description_zh": "联网检索工具指南",
                                "downloads": 100,
                                "installs": 20,
                                "stars": 5,
                                "score": 99.5,
                                "version": "1.0.2",
                                "ownerName": "skillhub-user",
                                "homepage": "https://api.skillhub.cn/skillhub-user/web-tools-guide",
                                "iconUrl": "https://example.com/icon.png",
                                "labels": {"requires_api_key": "false"},
                                "subCategories": [{"key": "knowledge-retrieval", "name": "信息检索"}],
                            }
                        ]
                    },
                }
            )
        if url.endswith("/api/v1/skills/web-tools-guide"):
            return FakeResponse(
                {
                    "latestVersion": {"version": "1.0.2"},
                    "securityReports": {"keen": {"status": "benign", "statusText": "安全，无风险"}},
                    "skill": {"summary_zh": "联网检索工具指南"},
                }
            )
        if url.endswith("/api/v1/download?slug=web-tools-guide"):
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                archive.writestr("SKILL.md", "# Web Tools Guide\n\nUse web tools safely.")
                archive.writestr("references/guide.md", "Guide")
            return FakeResponse(content=data.getvalue(), headers={"Content-Type": "application/zip"})
        raise AssertionError(f"unexpected URL: {url}")


def auth_headers(client, username: str = "skillhub_user"):
    password = "password123"
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    response = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_map_skillhub_summary_to_project_skill():
    from app.services.skillhub_repository import map_skillhub_summary

    skill = map_skillhub_summary(
        {
            "slug": "web-tools-guide",
            "name": "web-tools-guide",
            "category": "knowledge-management",
            "description_zh": "联网检索工具指南",
            "labels": {"requires_api_key": "true"},
            "subCategories": [{"name": "信息检索"}],
            "downloads": 100,
            "installs": 20,
            "stars": 5,
            "score": 99.5,
            "version": "1.0.2",
            "ownerName": "skillhub-user",
            "homepage": "https://api.skillhub.cn/skillhub-user/web-tools-guide",
            "iconUrl": "https://example.com/icon.png",
        },
        rank=1,
    )

    assert skill["skill_key"] == "skillhub.web-tools-guide"
    assert skill["name"] == "web-tools-guide"
    assert skill["category"] == "knowledge-management"
    assert skill["description"] == "联网检索工具指南"
    assert skill["required_tools"] == ["external_api_key"]
    assert skill["source"] == "skillhub"
    assert skill["source_slug"] == "web-tools-guide"
    assert skill["source_rank"] == 1


def test_sync_skillhub_skills_writes_repository_manifest_and_package(tmp_path):
    from app.services.skillhub_repository import load_repository_skills, sync_skillhub_skills

    synced = sync_skillhub_skills(root=tmp_path, limit=1, session=FakeSession())

    assert [skill["skill_key"] for skill in synced] == ["skillhub.web-tools-guide"]
    skill_dir = tmp_path / "skillhub" / "web-tools-guide"
    assert (skill_dir / "skill.json").exists()
    assert (skill_dir / "SKILL.md").read_text(encoding="utf-8").startswith("# Web Tools Guide")

    loaded = load_repository_skills(root=tmp_path)
    assert loaded[0]["skill_key"] == "skillhub.web-tools-guide"
    assert loaded[0]["source_url"] == "https://www.skillhub.cn/skills/web-tools-guide"


def test_skill_runtime_merges_local_skill_repository(tmp_path, monkeypatch):
    from app.services import skill_runtime

    skill_dir = tmp_path / "skillhub" / "web-tools-guide"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.json").write_text(
        """{
  "skill_key": "skillhub.web-tools-guide",
  "name": "web-tools-guide",
  "category": "knowledge-management",
  "description": "联网检索工具指南",
  "input_modalities": ["text"],
  "output_types": ["text"],
  "required_models": ["fast"],
  "required_tools": [],
  "params_schema": {},
  "permission_scope": ["skillhub"],
  "cost_level": "low",
  "status": "active",
  "source": "skillhub",
  "source_url": "https://www.skillhub.cn/skills/web-tools-guide",
  "source_slug": "web-tools-guide",
  "source_rank": 1
}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(skill_runtime, "SKILL_REPOSITORY_ROOT", tmp_path)

    catalog = skill_runtime.get_skill_catalog()
    skill_keys = {skill["skill_key"] for skill in catalog}

    assert "chat.reply" in skill_keys
    assert "skillhub.web-tools-guide" in skill_keys


def test_skill_response_preserves_skillhub_metadata():
    from datetime import datetime

    from app.schemas import SkillResponse

    response = SkillResponse(
        id=1,
        created_at=datetime.now(),
        skill_key="skillhub.web-tools-guide",
        name="web-tools-guide",
        category="knowledge-management",
        source="skillhub",
        source_url="https://www.skillhub.cn/skills/web-tools-guide",
        source_slug="web-tools-guide",
        source_rank=1,
        icon_url="https://example.com/icon.png",
        downloads=100,
        installs=20,
        stars=5,
        sub_categories=["信息检索"],
    )

    data = response.model_dump()

    assert data["source"] == "skillhub"
    assert data["source_url"] == "https://www.skillhub.cn/skills/web-tools-guide"
    assert data["source_rank"] == 1
    assert data["sub_categories"] == ["信息检索"]


def test_skillhub_sync_endpoint_returns_synced_skills(client, monkeypatch):
    from app.services import skillhub_repository

    def fake_sync_skillhub_skills(limit=50, **kwargs):
        assert limit == 3
        return [
            {
                "skill_key": "skillhub.web-tools-guide",
                "name": "web-tools-guide",
                "category": "knowledge-management",
                "description": "联网检索工具指南",
                "input_modalities": ["text"],
                "output_types": ["text"],
                "required_models": ["fast"],
                "required_tools": [],
                "params_schema": {},
                "permission_scope": ["skillhub"],
                "cost_level": "low",
                "status": "active",
                "source": "skillhub",
                "source_url": "https://www.skillhub.cn/skills/web-tools-guide",
                "source_slug": "web-tools-guide",
                "source_rank": 1,
            }
        ]

    monkeypatch.setattr(skillhub_repository, "sync_skillhub_skills", fake_sync_skillhub_skills)

    response = client.post("/api/v1/skills/sync/skillhub?limit=3", headers=auth_headers(client))

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["skills"][0]["skill_key"] == "skillhub.web-tools-guide"
