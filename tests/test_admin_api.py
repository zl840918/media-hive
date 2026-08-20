"""管理 API 测试：影视/资源录入、Key 管理、guest 访问限制。"""
from tests.conftest import ADMIN_KEY


def _admin_headers():
    return {"X-API-Key": ADMIN_KEY}


def test_admin_requires_admin(client):
    # 先用 admin 创建一个 guest key
    r = client.post(
        "/api/admin/keys",
        headers=_admin_headers(),
        json={"name": "guest-1", "level": "guest"},
    )
    assert r.status_code == 200
    guest_key = r.json()["key"]
    # guest 访问管理接口应 403
    assert client.get("/api/admin/movies", headers={"X-API-Key": guest_key}).status_code == 403


def test_create_and_update_movie(client):
    h = _admin_headers()
    r = client.post(
        "/api/admin/movies",
        headers=h,
        json={
            "tmdb_id": 777,
            "media_type": "tv",
            "title": "测试剧集",
            "original_title": "Test TV",
            "year": 2023,
        },
    )
    assert r.status_code == 200
    item_id = r.json()["id"]

    r2 = client.get(f"/api/admin/movies/{item_id}", headers=h)
    assert r2.status_code == 200
    assert r2.json()["title"] == "测试剧集"


def test_duplicate_movie_409(client):
    h = _admin_headers()
    payload = {"tmdb_id": 888, "media_type": "movie", "title": "重复测试"}
    assert client.post("/api/admin/movies", headers=h, json=payload).status_code == 200
    assert client.post("/api/admin/movies", headers=h, json=payload).status_code == 409


def test_duplicate_resource_409(client):
    h = _admin_headers()
    r = client.post("/api/admin/movies/tmdb/movie/11111", headers=h)
    item_id = r.json()["id"]
    res = {"drive_type": "quark", "share_url": "https://pan.quark.cn/s/xyz", "quality": "4K"}
    assert client.post(f"/api/admin/movies/{item_id}/resources", headers=h, json=res).status_code == 200
    assert client.post(f"/api/admin/movies/{item_id}/resources", headers=h, json=res).status_code == 409


def test_resource_crud(client):
    h = _admin_headers()
    r = client.post("/api/admin/movies/tmdb/movie/22222", headers=h)
    item_id = r.json()["id"]
    res = {"drive_type": "aliyun", "share_url": "https://www.alipan.com/s/abc", "quality": "4K", "size_gb": 30.0}
    rr = client.post(f"/api/admin/movies/{item_id}/resources", headers=h, json=res)
    assert rr.status_code == 200
    res_id = rr.json()["id"]

    # 更新状态为失效
    r2 = client.patch(f"/api/admin/resources/{res_id}", headers=h, json={"status": "expired"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "expired"

    # 删除
    r3 = client.delete(f"/api/admin/resources/{res_id}", headers=h)
    assert r3.status_code == 204
    assert client.get(f"/api/admin/movies/{item_id}", headers=h).json()["resources"] == []


def test_key_lifecycle(client):
    h = _admin_headers()
    r = client.post("/api/admin/keys", headers=h, json={"name": "member-1", "level": "member", "daily_quota": 10})
    assert r.status_code == 200
    key_id = r.json()["id"]
    key = r.json()["key"]
    assert len(key) >= 20  # 创建时回显完整 key

    # 列表里不应回显 key
    keys = client.get("/api/admin/keys", headers=h).json()
    listed = next(k for k in keys if k["id"] == key_id)
    assert "key" not in listed

    # 禁用后调用失败
    r2 = client.patch("/api/admin/keys/{key_id}".replace("{key_id}", str(key_id)), headers=h, json={"name": "member-1", "level": "member", "daily_quota": 10, "expires_at": None})
    assert r2.status_code == 200
    # 直接禁用：用 update 接口改 is_active（通过 name 传入不可行，走数据库层面验证）
    from app.database import SessionLocal
    from app.models import ApiKey as AK

    with SessionLocal() as db:
        ak = db.get(AK, key_id)
        ak.is_active = False
        db.commit()
    assert client.get("/api/open/ping", headers={"X-API-Key": key}).status_code == 403


def test_guest_max_quality_filter(client):
    """guest 只能解锁 ≤720P 的资源。"""
    h = _admin_headers()
    client.post("/api/admin/movies/tmdb/movie/33333", headers=h)
    item_id = client.get("/api/admin/movies", headers=h).json()[0]["id"]
    # 找到刚建的
    for m in client.get("/api/admin/movies", headers=h).json():
        if m["tmdb_id"] == 33333:
            item_id = m["id"]
    for res in [
        {"drive_type": "115", "share_url": "https://115.com/s/g1", "quality": "4K"},
        {"drive_type": "123", "share_url": "https://www.123pan.com/s/g2", "quality": "720P"},
    ]:
        client.post(f"/api/admin/movies/{item_id}/resources", headers=h, json=res)

    # 创建 guest key 并解锁
    gk = client.post("/api/admin/keys", headers=h, json={"name": "g", "level": "guest"}).json()["key"]
    r = client.post(
        "/api/open/resources/movie/33333/unlock",
        headers={"X-API-Key": gk},
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["quality"] == "720P"
