from pydantic_settings import BaseSettings
from pathlib import Path

class SentimentConfig(BaseSettings):
    ENABLE_CAIFENGLIAN: bool = True
    ENABLE_CNINFO: bool = True
    NEWS_CACHE_SECONDS: int = 60
    RISK_KEYWORDS_FILE: str = str(Path(__file__).parent / "keywords.txt")

    class Config:
        env_file = ".env"
        extra = "ignore"

# 全局配置实例
settings = SentimentConfig()