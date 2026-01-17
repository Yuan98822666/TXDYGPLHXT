# app/api/decision/decision_daily.py
"""
盘尾决策 API
调用方式：POST /api/v1/decision/run-daily?trade_date=2026-01-17
通常由调度器在 14:30 自动触发
"""

from fastapi import APIRouter, Depends, Query
from datetime import date
from app.db.session import get_db
from app.services.decision.decision_stock_daily_service import DecisionStockDailyService
from app.services.decision.decision_open_validation_service import DecisionOpenValidationService

router = APIRouter()

@router.post("/run-daily", summary=["盘尾决策"])
def run_daily_decision(trade_date: date = Query(..., description="交易日期"),db = Depends(get_db)):
    service = DecisionStockDailyService(db)
    return service.run_daily_decision(trade_date)


@router.post("/validate-open", summary=["竞价验证"])
def validate_open(trade_date: date = Query(..., description="验证日期（T+1日）"),db = Depends(get_db)):
    service = DecisionOpenValidationService(db)
    count = service.validate_open(trade_date)
    return {"validated_count": count, "trade_date": trade_date.isoformat()}