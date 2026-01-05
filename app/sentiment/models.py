from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional

class SentimentSource(str, Enum):
    CAIFENGLIAN = "caifenglian"
    CNINFO = "cninfo"

class NewsItem(BaseModel):
    title: str
    content: str
    publish_time: datetime
    source: SentimentSource
    symbol: Optional[str] = None
    url: Optional[str] = None

class RiskAssessment(BaseModel):
    symbol: str
    has_risk: bool
    risk_sources: list[str]
    latest_check: datetime