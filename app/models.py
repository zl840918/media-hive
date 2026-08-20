"""ORM 模型：影视条目 / 网盘资源 / API Key / 用量日志。"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MediaItem(Base):
    """影视条目（TMDB 元数据快照 + 本地自增 ID）。"""

    __tablename__ = "media_items"
    __table_args__ = (UniqueConstraint("tmdb_id", "media_type", name="uq_tmdb"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, index=True)
    media_type: Mapped[str] = mapped_column(String(10))  # movie | tv
    title: Mapped[str] = mapped_column(String(255), index=True)
    original_title: Mapped[str] = mapped_column(String(255), default="")
    overview: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_path: Mapped[str] = mapped_column(String(255), default="")
    backdrop_path: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    resources: Mapped[list["Resource"]] = relationship(
        back_populates="media", cascade="all, delete-orphan"
    )


class Resource(Base):
    """网盘分享资源：一条 = 一个网盘分享链接。"""

    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("media_id", "drive_type", "share_url", name="uq_drive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_items.id"), index=True)
    drive_type: Mapped[str] = mapped_column(String(20))  # 115 | 123 | quark | aliyun | baidu
    share_url: Mapped[str] = mapped_column(String(512))
    access_code: Mapped[str] = mapped_column(String(50), default="")  # 提取码/访问码
    quality: Mapped[str] = mapped_column(String(20), default="")  # 4K | 1080P | 720P | ...
    file_format: Mapped[str] = mapped_column(String(30), default="")  # BluRay | Web-DL | Remux
    size_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio: Mapped[str] = mapped_column(String(100), default="")
    subtitle: Mapped[str] = mapped_column(String(100), default="")
    note: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | expired
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    media: Mapped[MediaItem] = relationship(back_populates="resources")


class ApiKey(Base):
    """调用方 API Key。level: guest < member < admin。"""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    owner: Mapped[str] = mapped_column(String(100), default="")
    level: Mapped[str] = mapped_column(String(10), default="guest")  # guest | member | admin
    daily_quota: Mapped[int] = mapped_column(Integer, default=100)
    used_today: Mapped[int] = mapped_column(Integer, default=0)
    quota_date: Mapped[str] = mapped_column(String(10), default="")  # YYYY-MM-DD，跨天重置
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UsageLog(Base):
    """API 调用日志（解锁等计费操作）。"""

    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key_id: Mapped[int | None] = mapped_column(ForeignKey("api_keys.id"), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(100))
    media_type: Mapped[str] = mapped_column(String(10), default="")
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
