import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
from .base import NewsSource
from ..models import NewsItem, SentimentSource
import logging

logger = logging.getLogger(__name__)


class CninfoAnnouncementSource(NewsSource):
    # 类级缓存：所有实例共享（单例模式下等效于全局缓存）
    _last_full_fetch: float | None = None
    _last_full_data: pd.DataFrame | None = None
    _cache_lock = False  # 简易防并发重入（FastAPI 异步下非严格必要）

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
                        content="",  # AKShare 不提供全文
                        publish_time=row['publish_time'],
                        source=SentimentSource.CNINFO,
                        symbol=row['symbol'],
                        url=f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={row['symbol']}"
                    )
                )
            return results
        except Exception as e:
            logger.error(f"巨潮最新公告抓取失败: {e}")
            return []

    def fetch_by_symbol(self, symbol: str, hours: int = 24) -> list[NewsItem]:
        """
        获取某股票最近 N 小时的公告（通过全量拉取 + 本地过滤实现）
        """
        try:
            now = time.time()
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # 🔥 缓存机制：60秒内不重复请求巨潮
            if (CninfoAnnouncementSource._last_full_fetch is None or
                    now - CninfoAnnouncementSource._last_full_fetch > 60):

                if CninfoAnnouncementSource._cache_lock:
                    # 如果正在拉取，短暂等待（简单处理）
                    time.sleep(0.5)
                    if CninfoAnnouncementSource._last_full_data is not None:
                        df = CninfoAnnouncementSource._last_full_data
                    else:
                        df = pd.DataFrame()
                else:
                    CninfoAnnouncementSource._cache_lock = True
                    try:
                        df = ak.stock_notice_report(symbol="全部")
                        CninfoAnnouncementSource._last_full_data = df
                        CninfoAnnouncementSource._last_full_fetch = now
                    finally:
                        CninfoAnnouncementSource._cache_lock = False
            else:
                df = CninfoAnnouncementSource._last_full_data

            if df is None or df.empty:
                return []

            # 转换时间列（确保是 datetime）
            if not pd.api.types.is_datetime64_any_dtype(df['公告日期']):
                df['公告日期'] = pd.to_datetime(df['公告日期'])

            # 本地过滤：代码匹配 + 时间范围
            filtered_df = df[
                (df['代码'] == symbol) &
                (df['公告日期'] >= cutoff_time)
                ]

            results = []
            for _, row in filtered_df.iterrows():
                results.append(
                    NewsItem(
                        title=row['公告标题'],
                        content="",
                        publish_time=row['公告日期'],
                        source=SentimentSource.CNINFO,
                        symbol=symbol,
                        url=f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={symbol}"
                    )
                )
            return results

        except Exception as e:
            logger.error(f"巨潮个股公告抓取失败 ({symbol}): {e}")
            return []