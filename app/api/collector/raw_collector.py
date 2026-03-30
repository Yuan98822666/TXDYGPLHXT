# -*- coding: utf-8 -*-
"""
快照数据采集 API 路由

接口列表：
  POST /api/collector/raw/run      → 手动触发快照采集（股票+板块）
  POST /api/collector/raw/run-stock → 只采集股票快照
  POST /api/collector/raw/run-block → 只采集板块快照
  POST /api/collector/raw/run-day  → 手动触发日K数据采集
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()


class SnapshotRunRequest(BaseModel):
    """快照采集请求"""
    mode: Optional[str] = "all"  # all / stock / block


@router.post("/run", summary="手动触发快照采集（股票+板块）")
async def run_raw(background_tasks: BackgroundTasks):
    """
    手动触发快照采集任务

    说明：
        - 同时采集股票快照和板块快照
        - 股票快照：采集 stock_imp=1 的股票
        - 板块快照：采集所有板块（GN+HY+FG）
        - 后台执行，立即返回
    """
    try:
        from app.collectors.stock_raw_collector import StockRawCollector
        from app.collectors.block_raw_collector import BlockRawCollector

        background_tasks.add_task(StockRawCollector.collect)
        background_tasks.add_task(BlockRawCollector.collect)

        return {
            "status": "success",
            "message": "快照采集任务已启动（股票+板块），后台执行中",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/run-stock", summary="只采集股票快照")
async def run_stock_raw(background_tasks: BackgroundTasks):
    """
    只采集股票快照

    说明：
        - 采集 stock_imp=1 的股票
        - 后台执行，立即返回
    """
    try:
        from app.collectors.stock_raw_collector import StockRawCollector

        background_tasks.add_task(StockRawCollector.collect)

        return {
            "status": "success",
            "message": "股票快照采集任务已启动，后台执行中",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/run-block", summary="只采集板块快照")
async def run_block_raw(background_tasks: BackgroundTasks):
    """
    只采集板块快照

    说明：
        - 采集所有板块（GN+HY+FG）
        - 后台执行，立即返回
    """
    try:
        from app.collectors.block_raw_collector import BlockRawCollector

        background_tasks.add_task(BlockRawCollector.collect)

        return {
            "status": "success",
            "message": "板块快照采集任务已启动，后台执行中",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/run-day", summary="手动触发日K数据采集")
async def run_day_raw(background_tasks: BackgroundTasks):
    """
    手动触发日K数据采集

    说明：
        - 从 raw_min_* 快照表复制当天收盘数据到 raw_day_* 表
        - 仅在收盘后（15:00后）执行
        - 后台执行，立即返回
    """
    try:
        from app.collectors.day_collector import DayCollector

        background_tasks.add_task(DayCollector.collect_all)

        return {
            "status": "success",
            "message": "日K数据采集任务已启动，后台执行中",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")
