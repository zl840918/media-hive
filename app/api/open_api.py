"""开放 API：ping / quota / TMDB 代理 / 资源查询与解锁。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import log_usage, require_key
from app.config import get_settings
from app.database import get_db
from app.models import ApiKey, MediaItem, Resource
from app.schemas import (
    MediaDetail,
    MediaOut,
    QuotaOut,
    ResourceOut,
    ResourceUnlocked,
    TmdbSearchResult,
)
from app.services.tmdb_client import TmdbClient, TmdbError

router = APIRouter()

LEVEL_RANK = {"guest": 0, "member": 1, "admin": 2}


def _get_or_create_media(db: Session, media_type: str, tmdb_id: int) -> MediaItem:
    """按 tmdb_id 查本地；没有则从 TMDB 拉取并自动录入。"""
    item = (
        db.query(MediaItem)
        .filter(MediaItem.tmdb_id == tmdb_id, MediaItem.media_type == media_type)
        .first()
    )
    if item:
        return item
    try:
        data = TmdbClient().detail(media_type, tmdb_id)
    except TmdbError as e:
        raise HTTPException(status_code=e.status_code, detail=e.args[0])
    try:
        item = MediaItem(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        # 并发下可能刚被别的请求创建，再查一次
        item = (
            db.query(MediaItem)
            .filter(MediaItem.tmdb_id == tmdb_id, MediaItem.media_type == media_type)
            .first()
        )
        if item:
            return item
        raise HTTPException(status_code=500, detail="创建条目失败")


def _visible_resources(item: MediaItem, api_key: ApiKey) -> list[Resource]:
    """按等级过滤资源：guest 只能看 ≤ guest_max_quality。"""
    rows = [r for r in item.resources if r.status == "active"]
    if api_key.level == "guest":
        cap = get_settings().guest_max_quality
        if cap:
            order = {"720P": 1, "1080P": 2, "4K": 3}
            rows = [r for r in rows if order.get(r.quality.upper(), 0) <= order.get(cap, 0)]
    return rows


@router.get("/ping")
def ping(key: ApiKey = Depends(require_key)) -> dict:
    return {"status": "ok", "level": key.level, "name": key.name}


@router.get("/quota")
def quota(key: ApiKey = Depends(require_key)) -> QuotaOut:
    return QuotaOut(
        level=key.level,
        daily_quota=key.daily_quota,
        used_today=key.used_today,
        remaining=max(0, key.daily_quota - key.used_today),
        expires_at=key.expires_at,
    )


# ---------- TMDB 代理 ----------
@router.get("/tmdb/search/{media_type}", response_model=list[TmdbSearchResult])
def tmdb_search(
    media_type: str,
    query: str = Query(..., min_length=1),
    year: int | None = None,
    key: ApiKey = Depends(require_key),
) -> list[dict]:
    try:
        return TmdbClient().search(media_type, query, year)
    except TmdbError as e:
        raise HTTPException(status_code=e.status_code, detail=e.args[0])


@router.get("/tmdb/{media_type}/{tmdb_id}", response_model=MediaOut)
def tmdb_detail(media_type: str, tmdb_id: int, key: ApiKey = Depends(require_key)) -> dict:
    try:
        return TmdbClient().detail(media_type, tmdb_id)
    except TmdbError as e:
        raise HTTPException(status_code=e.status_code, detail=e.args[0])


# ---------- 资源 ----------
@router.get("/resources/{media_type}/{tmdb_id}", response_model=MediaDetail)
def list_resources(
    media_type: str,
    tmdb_id: int,
    key: ApiKey = Depends(require_key),
    db: Session = Depends(get_db),
) -> MediaDetail:
    item = _get_or_create_media(db, media_type, tmdb_id)
    detail = MediaDetail.model_validate(item)
    detail.resources = [ResourceOut.model_validate(r) for r in _visible_resources(item, key)]
    return detail


@router.post("/resources/{media_type}/{tmdb_id}/unlock", response_model=list[ResourceUnlocked])
def unlock_resources(
    media_type: str,
    tmdb_id: int,
    key: ApiKey = Depends(require_key),
    db: Session = Depends(get_db),
) -> list[ResourceUnlocked]:
    """解锁资源，返回完整分享链接。member 及以上全部解锁；guest 受限。"""
    item = _get_or_create_media(db, media_type, tmdb_id)
    rows = _visible_resources(item, key)
    if not rows:
        raise HTTPException(status_code=404, detail="该条目暂无可用资源")
    log_usage(db, key, "unlock", media_type, tmdb_id)
    return [ResourceUnlocked.model_validate(r) for r in rows]
