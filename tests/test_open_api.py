"""开放 API 测试：鉴权、配额、资源查询/解锁、guest 清晰度限制。"""


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ping_without_key_401(client):
    assert client.get("/api/open/ping").status_code == 401


def test_ping_with_invalid_key_401(client):
    assert client.get("/api/open/ping", headers={"X-API-Key": "wrong"}).status_code == 401


def test_ping_ok(client):
    r = client.get("/api/open/ping", headers={"X-API-Key": "test-admin-key-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["level"] == "admin"


def test_quota(client):
    r = client.get("/api/open/quota", headers={"X-API-Key": "test-admin-key-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["daily_quota"] > 0
    assert body["remaining"] >= 0


def _seed_movie_with_resources(client):
    """创建影视条目 + 2 条资源（1080P 一条、720P 一条），返回条目 id。"""
    h = {"X-API-Key": "test-admin-key-123"}
    r = client.post("/api/admin/movies/tmdb/movie/12345", headers=h)
    assert r.status_code == 200
    item_id = r.json()["id"]
    for res in [
        {"drive_type": "115", "share_url": "https://115.com/s/aaa", "quality": "1080P", "file_format": "BluRay", "size_gb": 18.5},
        {"drive_type": "123", "share_url": "https://www.123pan.com/s/bbb", "quality": "720P", "file_format": "Web-DL", "size_gb": 4.2},
    ]:
        rr = client.post(f"/api/admin/movies/{item_id}/resources", headers=h, json=res)
        assert rr.status_code == 200, rr.text
    return item_id


def test_resources_list_hides_links(client):
    _seed_movie_with_resources(client)
    r = client.get("/api/open/resources/movie/12345", headers={"X-API-Key": "test-admin-key-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "测试电影"
    assert len(body["resources"]) == 2
    # 链接必须被隐藏
    assert "share_url" not in body["resources"][0]
    assert "115.com/s/aaa" not in r.text


def test_unlock_returns_links(client):
    _seed_movie_with_resources(client)
    r = client.post(
        "/api/open/resources/movie/12345/unlock",
        headers={"X-API-Key": "test-admin-key-123"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert any(x["share_url"].startswith("https://115.com") for x in rows)


def test_unlock_unknown_tmdb_auto_creates(client):
    """本地无记录时，解锁会自动从 TMDB 拉取并创建条目。"""
    r = client.post(
        "/api/open/resources/movie/99999/unlock",
        headers={"X-API-Key": "test-admin-key-123"},
    )
    assert r.status_code == 404  # 创建了条目但没有资源


def test_quota_exhaustion_429(client):
    """创建一个日配额 5 的 key，连打 10 次应触发 429。"""
    h = {"X-API-Key": "test-admin-key-123"}
    r = client.post("/api/admin/keys", headers=h, json={"name": "low-quota", "level": "member", "daily_quota": 5})
    low_key = r.json()["key"]
    statuses = [client.get("/api/open/ping", headers={"X-API-Key": low_key}).status_code for _ in range(10)]
    assert statuses[:5] == [200] * 5
    assert statuses[5:] == [429] * 5
