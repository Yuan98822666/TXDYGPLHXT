# -*- coding: utf-8 -*-
"""
采集调度器 API 接口

接口列表：
  POST /api/collector/scheduler/start  → 启动调度器
  POST /api/collector/scheduler/stop   → 停止调度器
  GET  /api/collector/scheduler/status → 获取调度器状态
  POST /api/collector/scheduler/run-now → 立即执行采集
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/collector/scheduler", tags=["采集调度器"])


@router.post("/start", summary="启动采集调度器")
async def start_scheduler():
    """
    启动采集调度器

    说明：
        - 读取配置文件，按策略自动执行采集
        - 快照采集：交易时间内按配置的时间段执行
        - 特殊股票池：按配置的时间段执行
        - 日K采集：收盘后执行一次
    """
    try:
        from app.scheduler.collector_scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.start()

        return {
            "status": "success",
            "message": "采集调度器已启动",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/stop", summary="停止采集调度器")
async def stop_scheduler():
    """
    停止采集调度器
    """
    try:
        from app.scheduler.collector_scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.stop()

        return {
            "status": "success",
            "message": "采集调度器已停止",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")


@router.get("/status", summary="获取调度器状态")
async def get_scheduler_status():
    """
    获取采集调度器状态
    """
    try:
        from app.scheduler.collector_scheduler import get_scheduler

        scheduler = get_scheduler()

        return {
            "status": "success",
            "data": {
                "running": scheduler._running,
                "config_loaded": bool(scheduler.config),
                "last_run_times": scheduler.last_run_times,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-now", summary="立即执行采集")
async def run_collection_now():
    """
    立即执行一次采集（不受调度器控制）

    说明：
        - 立即执行快照采集和特殊股票池采集
        - 日K采集仅在收盘后执行
    """
    try:
        from app.collectors.stock_raw_collector import StockRawCollector
        from app.collectors.block_raw_collector import BlockRawCollector
        from app.collectors.special_pool_collector import SpecialPoolCollector

        # 快照采集
        StockRawCollector.collect()
        BlockRawCollector.collect()

        # 特殊股票池采集
        SpecialPoolCollector.collect_all()

        return {
            "status": "success",
            "message": "采集任务已执行",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")
