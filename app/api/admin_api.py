"""管理 API：影视/资源录入维护、API Key 管理、用量查看（需 admin）。"""
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.database import get_db
from app.models import ApiKey, MediaItem, Resource, UsageLog
from app.schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    MediaCreate,
    MediaDetail,
    MediaOut,
    ResourceCreate,
    ResourceUpdate,
    ResourceUnlocked,
)
from app.services.tmdb_client import TmdbClient, TmdbError

router = APIRouter(dependencies=[Depends(require_admin)])


# ---------- 影视条目 ----------
@router.post("/movies", response_model=MediaOut)
def create_movie(data: MediaCreate, db: Session = Depends(get_db)) -> MediaItem:
    exists = (
        db.query(MediaItem)
        .filter(MediaItem.tmdb_id == data.tmdb_id, MediaItem.media_type == data.media_type)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="该条目已存在")
    item = MediaItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/movies/tmdb/{media_type}/{tmdb_id}", response_model=MediaOut)
def create_movie_from_tmdb(media_type: str, tmdb_id: int, db: Session = Depends(get_db)) -> MediaItem:
    """从 TMDB 拉取详情并创建条目。"""
    try:
        data = TmdbClient().detail(media_type, tmdb_id)
    except TmdbError as e:
        raise HTTPException(status_code=e.status_code, detail=e.args[0])
    exists = (
        db.query(MediaItem)
        .filter(MediaItem.tmdb_id == tmdb_id, MediaItem.media_type == media_type)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="该条目已存在")
    item = MediaItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/movies", response_model=list[MediaOut])
def list_movies(db: Session = Depends(get_db)) -> list[MediaItem]:
    return db.query(MediaItem).order_by(MediaItem.created_at.desc()).limit(200).all()


@router.get("/movies/{item_id}", response_model=MediaDetail)
def movie_detail(item_id: int, db: Session = Depends(get_db)) -> MediaDetail:
    item = db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")
    detail = MediaDetail.model_validate(item)
    detail.resources = [ResourceUnlocked.model_validate(r) for r in item.resources]
    return detail


# ---------- 资源 ----------
@router.post("/movies/{item_id}/resources", response_model=ResourceUnlocked)
def add_resource(item_id: int, data: ResourceCreate, db: Session = Depends(get_db)) -> Resource:
    item = db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="条目不存在")
    dup = (
        db.query(Resource)
        .filter(
            Resource.media_id == item_id,
            Resource.drive_type == data.drive_type,
            Resource.share_url == data.share_url,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=409, detail="同网盘同链接资源已存在")
    res = Resource(media_id=item_id, **data.model_dump())
    db.add(res)
    db.commit()
    db.refresh(res)
    return res


@router.patch("/resources/{res_id}", response_model=ResourceUnlocked)
def update_resource(res_id: int, data: ResourceUpdate, db: Session = Depends(get_db)) -> Resource:
    res = db.get(Resource, res_id)
    if not res:
        raise HTTPException(status_code=404, detail="资源不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(res, field, value)
    db.commit()
    db.refresh(res)
    return res


@router.delete("/resources/{res_id}", status_code=204)
def delete_resource(res_id: int, db: Session = Depends(get_db)) -> None:
    res = db.get(Resource, res_id)
    if not res:
        raise HTTPException(status_code=404, detail="资源不存在")
    db.delete(res)
    db.commit()


# ---------- API Key ----------
@router.post("/keys", response_model=ApiKeyCreated)
def create_key(data: ApiKeyCreate, db: Session = Depends(get_db)) -> ApiKey:
    key = secrets.token_urlsafe(24)
    api_key = ApiKey(key=key, **data.model_dump())
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


@router.get("/keys", response_model=list[ApiKeyOut])
def list_keys(db: Session = Depends(get_db)) -> list[ApiKey]:
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.patch("/keys/{key_id}", response_model=ApiKeyOut)
def update_key(key_id: int, data: ApiKeyCreate, db: Session = Depends(get_db)) -> ApiKey:
    api_key = db.get(ApiKey, key_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="Key 不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(api_key, field, value)
    db.commit()
    db.refresh(api_key)
    return api_key


@router.get("/usage", response_model=list[dict])
def usage(db: Session = Depends(get_db), limit: int = 100) -> list[dict]:
    rows = db.query(UsageLog).order_by(UsageLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": r.id,
            "endpoint": r.endpoint,
            "media_type": r.media_type,
            "tmdb_id": r.tmdb_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
