"""
文件名：settings.py
作用说明：
    项目全局配置加载器
    统一从 .env 中读取环境变量
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础
    APP_ENV: str = "dev"
    APP_NAME: str = "TXDYGPLHXT"

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # SQLAlchemy
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ===== EastMoney =====
    EASTMONEY_UT: str
    EASTMONEY_CB_PREFIX: str = "jQuery112308004600294897531_1767433763641"
    EASTMONEY_PAGE_SIZE: int = 50
    EASTMONEY_TIMEOUT: int = 10
    # ===== 自动快照调度 =====
    AUTO_SNAPSHOT_INTERVAL_SECONDS: int = 30  # 默认 30 秒（1分钟2次）



settings = Settings()
