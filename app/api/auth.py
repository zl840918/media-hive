"""API Key 鉴权依赖：校验 Key、等级、过期与每日配额。"""
from datetime import date

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, UsageLog

LEVEL_RANK = {"guest": 0, "member": 1, "admin": 2}


def get_api_key(key: str | None = Header(None, alias="X-API-Key")) -> str | None:
    if not key:
        raise HTTPException(status_code=401, detail="缺少 X-API-Key 请求头")
    return key


def _load_key(db: Session, key: str) -> ApiKey:
    api_key = db.query(ApiKey).filter(ApiKey.key == key).first()
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key 无效")
    if not api_key.is_active:
        raise HTTPException(status_code=403, detail="API Key 已被禁用")
    if api_key.expires_at and api_key.expires_at.date() < date.today():
        raise HTTPException(status_code=403, detail="API Key 已过期")
    return api_key


def _check_quota(db: Session, api_key: ApiKey) -> None:
    today = date.today().isoformat()
    if api_key.quota_date != today:
        api_key.quota_date = today
        api_key.used_today = 0
        db.commit()
    if api_key.used_today >= api_key.daily_quota:
        raise HTTPException(status_code=429, detail="今日配额已用尽")


def require_key(
    key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> ApiKey:
    """任意有效 Key（计一次配额）。"""
    api_key = _load_key(db, key)
    _check_quota(db, api_key)
    api_key.used_today += 1
    db.commit()
    return api_key


def require_level(min_level: str = "member"):
    """按等级限制的依赖工厂。"""

    def _dep(
        key: str = Depends(get_api_key),
        db: Session = Depends(get_db),
    ) -> ApiKey:
        api_key = _load_key(db, key)
        if LEVEL_RANK[api_key.level] < LEVEL_RANK[min_level]:
            raise HTTPException(status_code=403, detail=f"需要 {min_level} 及以上等级")
        return api_key

    return _dep


def require_admin(key: str = Depends(get_api_key), db: Session = Depends(get_db)) -> ApiKey:
    api_key = _load_key(db, key)
    if api_key.level != "admin":
        raise HTTPException(status_code=403, detail="需要 admin 等级")
    return api_key


def log_usage(db: Session, api_key: ApiKey | None, endpoint: str, media_type: str = "", tmdb_id: int | None = None) -> None:
    db.add(
        UsageLog(
            api_key_id=api_key.id if api_key else None,
            endpoint=endpoint,
            media_type=media_type,
            tmdb_id=tmdb_id,
        )
    )
    db.commit()
