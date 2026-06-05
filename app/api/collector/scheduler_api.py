# -*- coding: utf-8 -*-
"""
【已废弃】采集调度器 API 接口

⚠️ 警告：此API已废弃，请使用 TaskManager API (/api/collector/tasks/*)

废弃原因：
- TaskManager 提供更灵活的内存化配置
- TaskManager 支持动态修改配置无需重启
- TaskManager 有更好的任务隔离和错误处理

迁移指南：
- 启动/停止任务：POST /api/collector/tasks/{task_id}/start, POST /api/collector/tasks/{task_id}/stop
- 查看任务状态：GET /api/collector/tasks/status
- 立即执行：POST /api/collector/tasks/{task_id}/run-now

保留此文件仅用于向后兼容，所有接口返回迁移提示。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/collector/scheduler", tags=["采集调度器(已废弃)"])

DEPRECATED_MESSAGE = {
    "status": "deprecated",
    "message": "此API已废弃，请使用 TaskManager API",
    "migration": {
        "启动任务": "POST /api/collector/tasks/{task_id}/start",
        "停止任务": "POST /api/collector/tasks/{task_id}/stop",
        "任务状态": "GET /api/collector/tasks/status",
        "立即执行": "POST /api/collector/tasks/{task_id}/run-now",
    },
    "available_tasks": ["raw", "special_pool", "day_k", "cls_telegram"],
}


@router.post("/start", summary="【已废弃】启动采集调度器")
async def start_scheduler():
    """
    【已废弃】启动采集调度器
    
    请使用 TaskManager API:
    - POST /api/collector/tasks/raw/start
    - POST /api/collector/tasks/special_pool/start
    - POST /api/collector/tasks/day_k/start
    """
    raise HTTPException(
        status_code=410,  # Gone
        detail=DEPRECATED_MESSAGE
    )


@router.post("/stop", summary="【已废弃】停止采集调度器")
async def stop_scheduler():
    """
    【已废弃】停止采集调度器
    
    请使用 TaskManager API:
    - POST /api/collector/tasks/raw/stop
    - POST /api/collector/tasks/special_pool/stop
    - POST /api/collector/tasks/day_k/stop
    """
    raise HTTPException(
        status_code=410,  # Gone
        detail=DEPRECATED_MESSAGE
    )


@router.get("/status", summary="【已废弃】获取调度器状态")
async def get_scheduler_status():
    """
    【已废弃】获取调度器状态
    
    请使用 TaskManager API:
    - GET /api/collector/tasks/status
    """
    raise HTTPException(
        status_code=410,  # Gone
        detail=DEPRECATED_MESSAGE
    )


@router.post("/run-now", summary="立即执行采集")
async def run_collection_now():
    """
    立即执行一次采集（不受调度器控制）

    说明：
        - 立即执行快照采集和特殊股票池采集
        - 日K采集仅在收盘后执行
        - 使用统一批次号确保股票和板块数据一致性
    """
    try:
        from app.collectors.stock_raw_collector import StockRawCollector
        from app.collectors.block_raw_collector import BlockRawCollector
        from app.collectors.special_pool_collector import SpecialPoolCollector
        from app.utils.batch_no import generate_batch_no

        # 统一生成批次号，确保股票和板块数据使用相同的批次号
        raw_no, trade_date, snapshot_time = generate_batch_no()

        # 快照采集（使用统一批次号）
        BlockRawCollector.collect(raw_no=raw_no, trade_date=trade_date, snapshot_time=snapshot_time)
        StockRawCollector.collect(raw_no=raw_no, trade_date=trade_date, snapshot_time=snapshot_time)

        # 特殊股票池采集
        SpecialPoolCollector.collect_all()

        return {
            "status": "success",
            "message": "采集任务已执行",
            "raw_no": raw_no,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "note": "此API保留向后兼容，建议使用 POST /api/collector/tasks/raw/run-now",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")
