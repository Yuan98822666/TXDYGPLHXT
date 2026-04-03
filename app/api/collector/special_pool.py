# -*- coding: utf-8 -*-
"""
特殊股票池采集 API 路由

接口列表：
  POST /api/collector/special/collect  → 手动触发特殊股票池采集
  GET  /api/collector/special/types    → 获取股票池类型列表
  GET  /api/collector/special/test     → 测试接口连通性
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class CollectRequest(BaseModel):
    """采集请求"""
    pool_type: Optional[str] = None  # 不传则采集全部，传值则采集指定类型


@router.post("/collect", summary="手动触发特殊股票池采集")
async def collect_special_pools(
    request: CollectRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    手动触发特殊股票池采集

    说明：
        - 不传 pool_type：采集全部5个池
        - 传 pool_type：采集指定池（zt/zrzt/qs/zb/dt）
        - 后台执行，立即返回

    池类型：
        - zt：涨停池（最近交易日）
        - zrzt：昨日涨停池（次近交易日）
        - qs：强势股池（最近交易日）
        - zb：炸板池（最近交易日）
        - dt：跌停池（最近交易日）
    """
    try:
        from app.collectors.special_pool_collector import SpecialPoolCollector

        if request and request.pool_type:
            pool_type = request.pool_type
            background_tasks.add_task(SpecialPoolCollector.collect, pool_type)
            return {
                "status": "success",
                "message": f"{pool_type} 股票池采集任务已启动，后台执行中",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        else:
            background_tasks.add_task(SpecialPoolCollector.collect_all)
            return {
                "status": "success",
                "message": "全部特殊股票池采集任务已启动，后台执行中",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.get("/types", summary="获取股票池类型列表")
async def get_pool_types():
    """
    获取所有股票池类型

    返回：股票池类型代码和名称
    """
    return {
        "types": [
            {"code": "zt", "name": "涨停池", "date": "最近交易日"},
            {"code": "zrzt", "name": "昨日涨停池", "date": "次近交易日"},
            {"code": "zb", "name": "炸板池", "date": "最近交易日"},
            {"code": "dt", "name": "跌停池", "date": "最近交易日"},
        ]
    }


@router.get("/test", summary="测试接口连通性")
async def test_connection():
    """测试接口连通性"""
    return {
        "status": "success",
        "message": "特殊股票池采集接口正常",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
