"""Media-Hive 核心引擎入口。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8890
"""
import logging
import secrets

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api import admin_api, open_api
from app.config import get_settings
from app.database import SessionLocal, engine, init_db
from app.models import ApiKey

logger = logging.getLogger("media-hive")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Media-Hive 网盘影视资源索引引擎",
    version="0.1.0",
    description="TMDB 元数据 + 网盘资源管理 + 开放解锁 API（Open API）",
)

app.include_router(open_api.router, prefix="/api/open", tags=["开放 API"])
app.include_router(admin_api.router, prefix="/api/admin", tags=["管理 API"])


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


def _bootstrap_admin_key() -> None:
    """确保存在一个 admin Key。有 MH_BOOTSTRAP_ADMIN_KEY 则用之，否则生成并打印。"""
    with SessionLocal() as db:
        has_admin = db.query(ApiKey).filter(ApiKey.level == "admin").first()
        if has_admin:
            return
        settings = get_settings()
        key = settings.bootstrap_admin_key or secrets.token_urlsafe(24)
        db.add(ApiKey(key=key, name="bootstrap-admin", owner="system", level="admin", daily_quota=100000))
        db.commit()
        if not settings.bootstrap_admin_key:
            logger.info("=" * 60)
            logger.info("首次启动生成的管理员 Key（请立即保存）：%s", key)
            logger.info("=" * 60)
        else:
            logger.info("管理员 Key 已从环境变量加载")


@app.on_event("startup")
def startup() -> None:
    init_db()
    _bootstrap_admin_key()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8890, reload=True)


if __name__ == "__main__":
    run()
