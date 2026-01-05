import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from .base import NewsSource
from ..models import NewsItem, SentimentSource
import logging

logger = logging.getLogger(__name__)


class CaiFengLianSource(NewsSource):
    def fetch_latest(self, limit: int = 20) -> list[NewsItem]:
        try:
            df = ak.stock_news_em()
            if df.empty:
                return []

            # 重命名中文字段
            df = df.rename(columns={
                '新闻标题': 'title',
                '新闻内容': 'content',
                '发布时间': 'publish_time',
                '新闻链接': 'url'
            })
            df['publish_time'] = pd.to_datetime(df['publish_time'])

            results = []
            for _, row in df.head(limit).iterrows():
                results.append(
                    NewsItem(
                        title=row['title'],
                        content=row['content'],
                        publish_time=row['publish_time'],
                        source=SentimentSource.CAIFENGLIAN,
                        url=row.get('url')
                    )
                )
            return results
        except Exception as e:
            logger.error(f"财联社抓取失败: {e}")
            return []

    def fetch_by_symbol(self, symbol: str, hours: int = 24) -> list[NewsItem]:
        all_news = self.fetch_latest(limit=100)
        cutoff = datetime.now() - timedelta(hours=hours)
        filtered = []
        for news in all_news:
            if news.publish_time < cutoff:
                continue
            # 检查股票代码或名称是否在标题/内容中（简化版）
            if symbol in news.title or symbol in news.content:
                filtered.append(news)
        return filtered