import time
from datetime import datetime
from typing import Dict, List
from .config import settings
from .sources.caifenglian import CaiFengLianSource
from .sources.cninfo_announcement import CninfoAnnouncementSource
from .models import RiskAssessment
import logging

logger = logging.getLogger(__name__)


class SentimentService:
    def __init__(self):
        self.sources = []
        if settings.ENABLE_CAIFENGLIAN:
            self.sources.append(CaiFengLianSource())
        if settings.ENABLE_CNINFO:
            self.sources.append(CninfoAnnouncementSource())

        self._load_risk_keywords()
        self._cache: Dict[str, tuple[float, RiskAssessment]] = {}

    def _load_risk_keywords(self):
        with open(settings.RISK_KEYWORDS_FILE, encoding="utf-8") as f:
            self.risk_keywords = [line.strip() for line in f if line.strip()]

    def check_risk(self, symbol: str) -> RiskAssessment:
        cache_key = f"risk_{symbol}"
        now = time.time()

        # 缓存检查
        if cache_key in self._cache:
            cached_time, result = self._cache[cache_key]
            if now - cached_time < settings.NEWS_CACHE_SECONDS:
                return result

        risk_sources = []
        for source in self.sources:
            try:
                news_list = source.fetch_by_symbol(symbol, hours=24)
                for news in news_list:
                    text = (news.title + " " + news.content).lower()
                    if any(kw in text for kw in self.risk_keywords):
                        risk_sources.append(f"{news.source.value}: {news.title[:30]}...")
            except Exception as e:
                logger.warning(f"Source {source.__class__.__name__} error: {e}")

        assessment = RiskAssessment(
            symbol=symbol,
            has_risk=len(risk_sources) > 0,
            risk_sources=risk_sources,
            latest_check=datetime.now()
        )
        self._cache[cache_key] = (now, assessment)
        return assessment