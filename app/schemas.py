"""Pydantic Schema：API 请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 资源 ----------
class ResourceCreate(BaseModel):
    drive_type: str = Field(..., pattern="^(115|123|quark|aliyun|baidu)$")
    share_url: str = Field(..., min_length=5, max_length=512)
    access_code: str = ""
    quality: str = ""  # 4K | 1080P | 720P | ...
    file_format: str = ""  # BluRay | Web-DL | Remux
    size_gb: float | None = None
    audio: str = ""
    subtitle: str = ""
    note: str = ""
    status: str = "active"


class ResourceUpdate(BaseModel):
    share_url: str | None = None
    access_code: str | None = None
    quality: str | None = None
    file_format: str | None = None
    size_gb: float | None = None
    audio: str | None = None
    subtitle: str | None = None
    note: str | None = None
    status: str | None = None


class ResourceOut(BaseModel):
    """公开输出：默认隐藏分享链接（解锁后才返回）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_type: str
    quality: str
    file_format: str
    size_gb: float | None
    audio: str
    subtitle: str
    note: str
    status: str
    created_at: datetime


class ResourceUnlocked(ResourceOut):
    """解锁后的完整资源：带分享链接和访问码。"""

    share_url: str
    access_code: str


# ---------- 影视条目 ----------
class MediaCreate(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: str
    original_title: str = ""
    overview: str = ""
    year: int | None = None
    poster_path: str = ""
    backdrop_path: str = ""


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_id: int
    media_type: str
    title: str
    original_title: str
    overview: str
    year: int | None
    poster_path: str
    backdrop_path: str
    created_at: datetime


class MediaDetail(MediaOut):
    resources: list[ResourceOut] = []


# ---------- API Key ----------
class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    owner: str = ""
    level: str = Field("guest", pattern="^(guest|member|admin)$")
    daily_quota: int = Field(100, ge=1, le=100000)
    expires_at: datetime | None = None


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner: str
    level: str
    daily_quota: int
    used_today: int
    is_active: bool
    expires_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    """创建时一次性回显完整 Key。"""

    key: str


# ---------- TMDB ----------
class TmdbSearchResult(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    original_title: str
    overview: str
    year: int | None
    poster_path: str
    backdrop_path: str


# ---------- 配额 ----------
class QuotaOut(BaseModel):
    level: str
    daily_quota: int
    used_today: int
    remaining: int
    expires_at: datetime | None
