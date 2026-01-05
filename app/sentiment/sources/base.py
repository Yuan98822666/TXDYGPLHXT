from abc import ABC, abstractmethod
from typing import List
from ..models import NewsItem

class NewsSource(ABC):
    @abstractmethod
    def fetch_latest(self, limit: int = 20) -> List[NewsItem]:
        pass

    @abstractmethod
    def fetch_by_symbol(self, symbol: str, hours: int = 24) -> List[NewsItem]:
        pass