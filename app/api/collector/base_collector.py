"""
文件路径：app/api/collector/base_collector.py
作用说明：基础数据采集 API 路由控制器

功能说明：
- 提供手动触发基础数据采集的 HTTP 接口
- 包括：基础股票采集、基础板块采集
- 返回采集统计信息和耗时

接口设计原则：
- 手动触发使用 POST 方法（有副作用操作）
- 使用后台任务避免阻塞 HTTP 响应
- 返回采集统计信息（更新数、新增数、总数、耗时）
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.collectors.base_collector import collect_base_stocks
from app.collectors.base_block_collector import collect_base_blocks
from datetime import datetime

# 创建 API 路由器
router = APIRouter()


@router.post("/stock/update", summary="手动采集基础股票信息")
async def trigger_base_stock_update(background_tasks: BackgroundTasks):
    """
    手动触发一次基础股票信息采集与更新

    HTTP 方法：POST
    路径：/api/collector/base/stock/update
    标签：基础股票采集

    功能说明：
        - 立即启动一次完整的基础股票采集周期
        - 从东方财富 API 采集所有股票信息
        - 与数据库对比，更新或新增记录
        - 使用后台任务避免阻塞 HTTP 请求响应

    返回:
        {
            "status": "success",
            "message": "基础股票采集任务已启动",
            "timestamp": "..."
        }
    """
    try:
        background_tasks.add_task(collect_base_stocks)
        timestamp = datetime.utcnow().isoformat() + "Z"
        print(f"[{timestamp}] 基础股票采集任务已启动")
        return {
            "status": "success",
            "message": "基础股票采集任务已启动，请稍后查看数据库。",
            "timestamp": timestamp,
            "note": "采集完成后，可查看数据库 base_stock 表的更新情况。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集触发失败: {str(e)}")


@router.post("/block/update", summary="手动采集基础板块信息")
async def trigger_base_block_update(background_tasks: BackgroundTasks):
    """
    手动触发一次基础板块信息采集与更新

    HTTP 方法：POST
    路径：/api/collector/base/block/update
    标签：基础板块采集

    功能说明：
        - 立即启动一次完整的基础板块采集周期
        - 从东方财富 API 采集所有板块信息（概念板块 + 行业板块）
        - 与数据库对比，更新或新增记录（以 block_code 为唯一标识）
        - 使用后台任务避免阻塞 HTTP 请求响应

    返回:
        {
            "status": "success",
            "message": "基础板块采集任务已启动",
            "timestamp": "..."
        }
    """
    try:
        background_tasks.add_task(collect_base_blocks)
        timestamp = datetime.utcnow().isoformat() + "Z"
        print(f"[{timestamp}] 基础板块采集任务已启动")
        return {
            "status": "success",
            "message": "基础板块采集任务已启动，请稍后查看数据库。",
            "timestamp": timestamp,
            "note": "采集完成后，可查看数据库 base_block 表的更新情况。"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集触发失败: {str(e)}")
