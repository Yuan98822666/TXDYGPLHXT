# test_sentiment.py
import akshare as ak
import pandas as pd

print("=== 测试 AKShare 快讯 ===")
try:
    news = ak.stock_news_em()
    print("快讯字段:", news.columns.tolist())
    if not news.empty:
        print("最新快讯:", news.iloc[0]['新闻标题'])
except Exception as e:
    print("快讯失败:", e)

print("\n=== 测试 巨潮公告 ===")
try:
    ann = ak.stock_notice_report(symbol="全部")
    print("公告字段:", ann.columns.tolist())
    if not ann.empty:
        print("最新公告:", ann.iloc[0]['公告标题'])
except Exception as e:
    print("公告失败:", e)

print("\n=== 测试 Pydantic Settings ===")
from pydantic_settings import BaseSettings
class Config(BaseSettings):
    TEST: bool = True
config = Config()
print("配置加载成功:", config.TEST)