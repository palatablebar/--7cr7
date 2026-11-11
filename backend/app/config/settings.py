"""Runtime configuration. Every value can be overridden by an env var of the same name."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # --- database ---
    DB_NAME: str = "lakepack_db"
    DB_USER: str = "lakepack_user"
    DB_PASSWORD: str = "lakepack_pwd"
    DB_ROOT_PASSWORD: str = "lakepack_root_pwd"
    DB_HOST: str = "db"
    DB_PORT: int = 3306

    # --- auth ---
    JWT_SECRET: str = "lakepack_dev_jwt_secret_change_me_in_prod_0611"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    # --- infra ---
    REDIS_URL: str = "redis://redis:6379/0"
    LAKE_ARTIFACT_DIR: str = "/data/lake"
    LAKE_BUCKET: str = "s3://shiguang-lake"

    # --- compaction cost model (documented in README §cost model) ---
    BANDWIDTH_MBPS: float = 80.0           # rewrite throughput used by the estimator
    PER_FILE_OVERHEAD_S: float = 0.3       # per-file open/close overhead
    UNIT_COST_PER_GB: float = 0.85         # object-storage read+write+compute per GB
    COST_PER_FILE_DAY: float = 0.0004      # metadata/list overhead per file per day

    # --- limits ---
    PLAN_DAILY_QUOTA: int = 8
    RATE_WINDOW_SECONDS: int = 60
    RATE_WINDOW_MAX: int = 30

    # --- demo seed ---
    SEED_DEMO: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
