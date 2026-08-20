"""应用配置。环境变量优先，.env 文件可选。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MH_", extra="ignore")

    # 数据库
    database_url: str = "sqlite:///./media_hive.db"

    # TMDB
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.tmdb.org/3"

    # 鉴权
    # 首个管理员 Key 用固定 seed 从环境变量生成；为空则启动时打印随机 key 一次
    bootstrap_admin_key: str = ""

    # 解锁策略
    # guest 能看到的最高清晰度（"" 表示不限）
    guest_max_quality: str = "720P"

    # 配额默认值
    default_daily_quota: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
