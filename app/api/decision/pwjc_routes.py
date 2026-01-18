from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from app.db.session import get_db

# === 仅导入你已有的服务 ===
from app.services.event.capital_persistence_service import CapitalPersistenceService
from app.services.event.stock_dominance_service import StockDominanceService
from app.services.event.stock_consensus_service import StockConsensusService
from app.services.decision.decision_stock_daily_service import DecisionStockDailyService
from app.services.decision.decision_open_validation_service import DecisionOpenValidationService
from app.services.event.block_start_service import BlockStartService

router = APIRouter(prefix="/api/pwjc", tags=["盘尾决策闭环"])


@router.post("/events/intraday")
def generate_intraday_events(
        trade_date: date = Query(...),
        from_time: str = Query(...),
        to_time: str = Query(...),
        db: Session = Depends(get_db)
):
    """盘中增量生成四类临时事件（is_final=False）"""
    services = [
        BlockStartService,  # 板块启动（环境信号）
        CapitalPersistenceService,  # 资金持续
        StockDominanceService,  # 控盘稳定
        StockConsensusService,  # 群体共识
    ]
    for svc in services:
        svc.generate_events_for_date(
            db=db,
            trade_date=trade_date,
            is_final=False,
            from_time=from_time,
            to_time=to_time
        )
    return {"status": "success", "message": f"盘中事件生成完成 ({from_time}-{to_time})"}


@router.post("/run-daily-decision")
def run_daily_decision(
        trade_date: date = Query(...),
        db: Session = Depends(get_db)
):
    """
    生成四类最终事件并执行隔夜下注决策

    🔔 注意：当前决策逻辑仅基于三类个股事件（资金/控盘/共识），
    板块启动事件（BlockStart）暂不参与自动决策，仅用于环境监控。
    """
    # Step 1: 生成四类最终事件（含板块）
    services = [
        BlockStartService,
        CapitalPersistenceService,
        StockDominanceService,
        StockConsensusService,
    ]
    for svc in services:
        svc.generate_events_for_date(
            db=db,
            trade_date=trade_date,
            is_final=True
        )

    # Step 2: 执行决策（仅使用三类个股事件）
    decisions = DecisionStockDailyService.run_daily_decision(db, trade_date)
    allow_count = len([d for d in decisions if d.decision_status == "ALLOW"])

    return {
        "status": "success",
        "trade_date": trade_date,
        "total_decisions": len(decisions),
        "allow_count": allow_count,
        "note": "板块启动事件已生成，但未纳入自动决策（需板块-股票映射支持）"
    }


@router.post("/validate-open")
def validate_open_performance(
        trade_date: date = Query(...),
        db: Session = Depends(get_db)
):
    """验证前一交易日 ALLOW 股票的开盘表现"""
    validations = DecisionOpenValidationService.validate_open_for_date(db, trade_date)
    success = len([v for v in validations if v.validation_status == "SUCCESS"])
    total_valid = len([v for v in validations if v.validation_status != "NO_DATA"])
    win_rate = round(success / total_valid * 100, 1) if total_valid > 0 else 0.0

    return {
        "status": "success",
        "validate_date": trade_date,
        "validated_count": len(validations),
        "win_rate_percent": win_rate
    }