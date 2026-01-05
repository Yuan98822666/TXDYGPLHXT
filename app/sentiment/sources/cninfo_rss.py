# sentiment/sources/cninfo_announcement.py （重命名）
import akshare as ak
from .base import NewsSource
from ..models import NewsItem, SentimentSource
from datetime import datetime
import pandas as pd


class CninfoAnnouncementSource(NewsSource):
    def fetch_latest(self, limit: int = 20) -> list[NewsItem]:
        try:
            df = ak.stock_notice_report(symbol="全部")
            if df.empty:
                return []

            df = df.rename(columns={
                '代码': 'symbol',
                '公告标题': 'title',
                '公告日期': 'publish_time'
            })
            df['publish_time'] = pd.to_datetime(df['publish_time'])

            results = []
            for _, row in df.head(limit).iterrows():
                results.append(
                    NewsItem(
                        title=row['title'],
                        content="",  # 公告内容需点开链接，此处留空
                        publish_time=row['publish_time'],
                        source=SentimentSource.CNINFO,
                        symbol=row['symbol'],
                        url=f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={row['symbol']}"
                    )
                )
            return results
        except Exception as e:
            logger.error(f"巨潮公告抓取失败: {e}")
            return []