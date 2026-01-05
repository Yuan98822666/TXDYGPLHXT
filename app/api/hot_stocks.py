# app/api/v1/hot_stocks.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import SessionLocal  # ← 你已有的 session 工厂
from app.services.mentioned_stock_service import MentionedStockService
from app.behavior.mentioned_stock_behavior import MentionedStockBehavior
from typing import List

router = APIRouter(prefix="/hot", tags=["热点股票"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/mentioned-stocks")
def get_mentioned_stocks(
    sort_by: str = Query("mention_count", description="排序字段: mention_count, stock_ltsz, stock_zdf, stock_zl_zb, stock_cd_zb"),
    top_n: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    获取最新快照批次中被板块“点名”的股票（领涨股 + 资金流入最多股）
    """
    service = MentionedStockService(db)
    behavior = MentionedStockBehavior(service)

    data = behavior.get_hot_mentioned_stocks()
    sorted_stocks = behavior.sort_stocks(data["stocks"], sort_by=sort_by)

    return {
        "kz_no": data["kz_no"],
        "total_count": len(sorted_stocks),
        "stocks": sorted_stocks[:top_n]
    }