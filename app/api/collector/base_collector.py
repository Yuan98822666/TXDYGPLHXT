"""
文件路径：app/api/collector/base_collector.py
作用说明：基础数据采集 API 路由

接口列表：
  POST /api/collector/base/stock/update           → 采集基础股票数据
  POST /api/collector/base/block/update           → 采集基础板块数据
  POST /api/collector/base/block-stock-lnk/update → 采集板块成分股关联数据

设计原则：
  - 所有采集任务通过 BackgroundTasks 异步执行，避免 HTTP 超时
  - 接口只负责触发，不等待结果（采集耗时较长）
  - 统一返回格式：status + message + timestamp
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.collectors.base_stock_collector import collect_base_stocks
from app.collectors.base_block_collector import collect_base_blocks
from app.collectors.base_block_stock_lnk_collector import collect_base_block_stock_lnk
from datetime import datetime

router = APIRouter()


@router.post("/stock/update", summary="采集基础股票数据")
async def trigger_base_stock_update(background_tasks: BackgroundTasks):
    """
    触发基础股票数据采集

    路径：POST /api/collector/base/stock/update
    说明：采集 A 股全市场股票基础信息，写入 base_stock 表
    耗时：约 30~60 秒（全量约 5000 条）
    """
    try:
        background_tasks.add_task(collect_base_stocks)
        return {
            "status": "success",
            "message": "股票采集任务已启动，后台执行中",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/block/update", summary="采集基础板块数据")
async def trigger_base_block_update(background_tasks: BackgroundTasks):
    """
    触发基础板块数据采集

    路径：POST /api/collector/base/block/update
    说明：采集概念板块（GN）+ 行业板块（HY）基础信息，写入 base_block 表
    耗时：约 10~20 秒
    """
    try:
        background_tasks.add_task(collect_base_blocks)
        return {
            "status": "success",
            "message": "板块采集任务已启动，后台执行中",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/block-stock-lnk/update", summary="采集板块成分股关联数据")
async def trigger_base_block_stock_lnk_update(background_tasks: BackgroundTasks):
    """
    触发板块成分股关联数据采集

    路径：POST /api/collector/base/block-stock-lnk/update
    说明：遍历 base_block 表中所有板块，逐个采集成分股，写入 base_block_stock_lnk 表
    耗时：约 10~30 分钟（约 1000+ 个板块，每板块 0.2s 延迟）
    前置条件：base_block 表必须有数据（先调用 /block/update）
    """
    try:
        background_tasks.add_task(collect_base_block_stock_lnk)
        return {
            "status": "success",
            "message": "板块成分股关联采集任务已启动，后台执行中（耗时较长，约10~30分钟）",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")
