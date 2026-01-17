"""
事件生成 API 控制器（增强版）

📌 核心设计原则：
- 事件分为两类：盘中观察事件（is_final=False）和收盘冻结事件（is_final=True）
- 决策服务仅依赖 is_final=True 的事件
- 接口按业务场景划分，避免参数组合歧义

🎯 主要接口：
1. 单事件生成（调试用）：/block-start, /capital-persistence 等
2. 盘中批量生成：/generate/intraday → 生成4类 is_final=False 事件
3. 收盘流程执行：/generate/closing → 生成 is_final=True 事件 + 决策分

🔐 安全建议：
- 生产环境应加 JWT 鉴权或 IP 白名单
- 避免高频调用（可加 Redis 分布式锁）
"""

from datetime import date, datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.event.block_start_service import BlockStartService
from app.services.event.capital_persistence_service import CapitalPersistenceService
from app.services.event.stock_dominance_service import StockDominanceService
from app.services.event.stock_consensus_service import StockConsensusService
from app.services.decision.decision_confidence_score_service import DecisionConfidenceScoreService


# ====== 辅助函数 ======
def is_trading_day(check_date: date) -> bool:
    """
    判断是否为交易日（简化版：排除周末）

    🔔 生产环境建议替换为真实交易日历（如从数据库读取 holiday 表）
    """
    return check_date.weekday() < 5  # Monday=0, Sunday=6


def standard_response(*, success: bool = True, message: str = "", data: Optional[Dict[str, Any]] = None, ) -> Dict[str, Any]:
    """
    统一 API 成功响应格式（按业务需求定制）。

    成功时返回：
    {
        "状态": "成功",
        "结果": {
            "event_block_start": "12条",
            ...
        }
    }

    ⚠️ 注意：错误情况由 FastAPI 自动处理（通过 raise HTTPException），
    不在此函数中返回失败结构，以保持 HTTP 状态码语义清晰。
    """
    return {
        "状态": "成功",
        "结果": data or {}
    }


# ====== 路由注册 ======
router = APIRouter()


# ==============================
# 单事件生成接口（用于调试/回测）
# ==============================

@router.post("/generate/block-start", summary="生成板块启动事件")
def generate_block_start(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    is_final: bool = Query(False, description="是否为收盘冻结事件（默认 False）"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    生成「板块启动」事件，识别主线板块的持续启动信号。

    ### 参数说明
    - `trade_date`: 必填，交易日
    - `is_final`:
        - `False`（默认）：生成盘中观察事件（每10分钟可运行）
        - `True`：生成收盘冻结事件（15:10后运行）

    ### 使用场景
    - 回测某日板块行为
    - 手动补数据
    - 调试事件逻辑

    ### 示例
    ```bash
    curl -X POST "http://localhost:8000/events/generate/block-start?trade_date=2026-01-16&is_final=false"
    ```
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，无法生成事件")

    events = BlockStartService.run_for_date(db, trade_date, is_final=is_final)
    return standard_response(
        data={
            "event_block_start": f"{len(events)}条"
        }
    )


@router.post("/generate/capital-persistence", summary="生成资本持续性事件")
def generate_capital_persistence(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    is_final: bool = Query(False, description="是否为收盘冻结事件（默认 False）"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    生成「资本持续性」事件，识别主力资金持续流入的个股。

    ### 参数 & 场景
    同 /block-start，适用于个股资金流分析。
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，无法生成事件")

    events = CapitalPersistenceService.run_for_date(db, trade_date, is_final=is_final)
    return standard_response(
        data={
            "event_capital_persistence": f"{len(events)}条"
        }
    )


@router.post("/generate/stock-dominance", summary="生成控盘程度事件")
def generate_stock_dominance(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    is_final: bool = Query(False, description="是否为收盘冻结事件（默认 False）"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    生成「控盘程度」事件，判断主力是否有效控制股价波动。
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，无法生成事件")

    events = StockDominanceService.run_for_date(db, trade_date, is_final=is_final)
    return standard_response(
        data={
            "event_stock_dominance": f"{len(events)}条"
        }
    )


@router.post("/generate/stock-consensus", summary="生成群体共识事件")
def generate_stock_consensus(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    is_final: bool = Query(False, description="是否为收盘冻结事件（默认 False）"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    生成「群体共识」事件，识别被多个板块反复点名的核心股。
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，无法生成事件")

    events = StockConsensusService.run_for_date(db, trade_date, is_final=is_final)
    return standard_response(
        data={
            "event_stock_consensus": f"{len(events)}条"
        }
    )


@router.post("/generate/decision-score", summary="生成决策信心分（仅收盘）")
def generate_decision_score(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    **仅基于 is_final=True 的事件**，生成当日最终决策信心分。

    ### 重要规则
    - 此接口**不接受 is_final 参数**
    - 内部自动查询 `is_final=True` 的四类事件
    - 若当日无收盘事件，将返回空结果

    ### 使用时机
    - 每日 15:10 后手动触发
    - 补历史决策数据

    ### ⚠️ 注意
    请确保已先运行过 `/generate/closing` 或四类 `is_final=True` 事件生成。
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，无法生成决策")

    decisions = DecisionConfidenceScoreService.run_for_date(db, trade_date)
    return standard_response(
        data={
            "decision_confidence_score": f"{len(decisions)}条"
        }
    )


# ==============================
# 批量场景接口（推荐使用）
# ==============================

@router.post("/generate/intraday", summary="【盘中】批量生成观察事件")
def generate_intraday_events(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    **盘中模式**：生成四类 `is_final=False` 的实时观察事件。

    ### 自动生成内容
    - 板块启动事件（is_final=False）
    - 资本持续性事件（is_final=False）
    - 控盘程度事件（is_final=False）
    - 群体共识事件（is_final=False）

    ### 不包含
    - ❌ 决策信心分（因依赖收盘事件）

    ### 使用场景
    - 日内监控系统调用（如每10分钟）
    - 手动触发盘中快照

    ### 示例
    ```bash
    curl -X POST "http://localhost:8000/events/generate/intraday?trade_date=2026-01-16"
    ```
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，跳过盘中事件生成")

    count1 = len(BlockStartService.run_for_date(db, trade_date, is_final=False))
    count2 = len(CapitalPersistenceService.run_for_date(db, trade_date, is_final=False))
    count3 = len(StockDominanceService.run_for_date(db, trade_date, is_final=False))
    count4 = len(StockConsensusService.run_for_date(db, trade_date, is_final=False))

    return standard_response(
        data={
            "event_block_start": f"{count1}条",
            "event_capital_persistence": f"{count2}条",
            "event_stock_dominance": f"{count3}条",
            "event_stock_consensus": f"{count4}条"
        }
    )


@router.post("/generate/closing", summary="【收盘】执行完整收盘流程")
def generate_closing_routine(
    trade_date: date = Query(..., description="目标交易日，格式：YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    ### 功能说明
    **收盘模式**：执行完整日终流程，生成最终决策依据。

    ### 自动生成内容
    1. 四类 `is_final=True` 的收盘冻结事件
    2. 决策信心分（基于上述事件）

    ### 使用场景
    - 每日 15:10 自动调度
    - 手动补全某日最终决策

    ### 业务意义
    - 生成的事件和决策将作为次日交易的唯一合法输入
    - 确保“过程事实”与“决策事实”分离

    ### 示例
    ```bash
    curl -X POST "http://localhost:8000/events/generate/closing?trade_date=2026-01-16"
    ```
    """
    if not is_trading_day(trade_date):
        raise HTTPException(status_code=400, detail="非交易日，跳过收盘流程")

    # Step 1: 生成四类收盘事件
    c1 = len(BlockStartService.run_for_date(db, trade_date, is_final=True))
    c2 = len(CapitalPersistenceService.run_for_date(db, trade_date, is_final=True))
    c3 = len(StockDominanceService.run_for_date(db, trade_date, is_final=True))
    c4 = len(StockConsensusService.run_for_date(db, trade_date, is_final=True))

    # Step 2: 生成决策
    d1 = len(DecisionConfidenceScoreService.run_for_date(db, trade_date))

    return standard_response(
        data={
            "event_block_start": f"{c1}条",
            "event_capital_persistence": f"{c2}条",
            "event_stock_dominance": f"{c3}条",
            "event_stock_consensus": f"{c4}条",
            "decision_confidence_score": f"{d1}条"
        }
    )