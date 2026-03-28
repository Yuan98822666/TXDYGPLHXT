"""
基础数据采集 API 路由

接口列表：
  POST /api/collector/base/stock/update                    → 采集基础股票数据
  POST /api/collector/base/block/update                    → 采集基础板块数据
  POST /api/collector/base/block-stock-lnk/update          → 采集板块成分股关联数据
  POST /api/collector/base/block-stock-lnk/update-feng-ge  → 手动更新风格板块成分股
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.collectors.base_stock_collector import collect_base_stocks
from app.collectors.base_block_collector import collect_base_blocks
from app.collectors.base_block_stock_lnk_collector import collect_base_block_stock_lnk

router = APIRouter()


class FengGeUpdateRequest(BaseModel):
    """风格板块更新请求"""
    block_codes: Optional[List[str]] = None  # 如果为空，则更新所有 block_type='FG' 的板块


@router.post("/stock/update", summary="采集基础股票数据")
async def trigger_base_stock_update(background_tasks: BackgroundTasks):
    """触发基础股票数据采集（约 30~60 秒）"""
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
    """触发基础板块数据采集（约 10~20 秒）"""
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
    """触发板块成分股关联数据采集（约 20~40 分钟，600+ 板块）"""
    try:
        background_tasks.add_task(collect_base_block_stock_lnk)
        return {
            "status": "success",
            "message": "板块成分股关联采集任务已启动，后台执行中，预计耗时 20~40 分钟",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


@router.post("/block-stock-lnk/update-feng-ge", summary="手动更新风格板块成分股")
async def trigger_feng_ge_update(request: FengGeUpdateRequest, background_tasks: BackgroundTasks):
    """
    手动更新风格板块（block_type='FG'）的成分股
    
    说明:
        - 风格板块成分股变化频繁，需要每天手动更新
        - 其他板块（GN/HY）成分股相对稳定，可以定期全量采集
    
    参数:
        block_codes: 指定要更新的板块代码列表，如 ["BK0001", "BK0002"]
                    如果为空或不传，则更新所有 block_type='FG' 的板块
    """
    try:
        from app.collectors.base_block_stock_lnk_collector import update_feng_ge_blocks
        
        background_tasks.add_task(
            update_feng_ge_blocks,
            block_codes=request.block_codes
        )
        return {
            "status": "success",
            "message": "风格板块更新任务已启动，后台执行中",
            "block_codes": request.block_codes,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")


