"""pytest 共享 fixture：隔离数据库 + 固定管理员 Key + TMDB mock。

注意：环境变量必须在导入 app 模块之前设置，故本文件顶部直接设置。
"""
import os

os.environ["MH_DATABASE_URL"] = "sqlite:///./test_media_hive.db"
os.environ["MH_BOOTSTRAP_ADMIN_KEY"] = "test-admin-key-123"
os.environ["MH_GUEST_MAX_QUALITY"] = "720P"
os.environ["MH_DEFAULT_DAILY_QUOTA"] = "50"

import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.main import app

ADMIN_KEY = "test-admin-key-123"
FAKE_TMDB_DETAIL = {
    "tmdb_id": 12345,
    "media_type": "movie",
    "title": "测试电影",
    "original_title": "Test Movie",
    "overview": "一部测试电影",
    "year": 2024,
    "poster_path": "/poster.jpg",
    "backdrop_path": "/backdrop.jpg",
}


@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前清空所有表并重建 admin key（不删文件，避免 Windows 文件锁）。"""
    from sqlalchemy import text

    from app.models import ApiKey

    database.init_db()
    with database.SessionLocal() as db:
        db.execute(text("DELETE FROM usage_logs"))
        db.execute(text("DELETE FROM resources"))
        db.execute(text("DELETE FROM media_items"))
        db.execute(text("DELETE FROM api_keys"))
        db.add(ApiKey(key=ADMIN_KEY, name="bootstrap-admin", owner="system", level="admin", daily_quota=100000))
        db.commit()
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def mock_tmdb(monkeypatch):
    """让 TMDB 详情/搜索返回假数据，不发起真实网络请求。"""

    class FakeTmdbClient:
        def __init__(self, *args, **kwargs):
            pass

        def detail(self, media_type, tmdb_id):
            data = dict(FAKE_TMDB_DETAIL)
            data["tmdb_id"] = tmdb_id
            data["media_type"] = media_type
            return data

        def search(self, media_type, query, year=None, limit=8):
            return [dict(FAKE_TMDB_DETAIL)]

    monkeypatch.setattr("app.api.open_api.TmdbClient", FakeTmdbClient)
    monkeypatch.setattr("app.api.admin_api.TmdbClient", FakeTmdbClient)
