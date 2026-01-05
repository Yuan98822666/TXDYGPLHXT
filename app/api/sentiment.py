# app/api/v1/sentiment.py
from fastapi import APIRouter, Query
from app.sentiment.service import SentimentService

router = APIRouter(prefix="/sentiment", tags=["Sentiment"])

# 单例服务（可在模块级初始化）
sentiment_service = SentimentService()

@router.get("/risk-check")
async def risk_check(symbol: str = Query(..., min_length=6, max_length=6, regex=r"^\d{6}$")):
    """
    检查股票是否有负面舆情风险
    - symbol: 6位A股代码，如 600000
    """
    return sentiment_service.check_risk(symbol)