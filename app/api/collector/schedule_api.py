# -*- coding: utf-8 -*-
"""
采集频率配置 API 接口

接口列表：
  GET  /api/collector/schedule/config    → 获取完整配置
  GET  /api/collector/schedule/raw      → 获取快照采集配置
  GET  /api/collector/schedule/day-k    → 获取日K采集配置
  GET  /api/collector/schedule/special → 获取特殊股票池配置
  PUT  /api/collector/schedule/update   → 更新配置项
  POST /api/collector/schedule/reload   → 重新加载配置
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Dict

router = APIRouter(tags=["采集频率配置"])


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    key: str
    value: Any


@router.get("/config", summary="获取完整采集配置")
async def get_config():
    """获取完整的采集频率配置"""
    from app.utils.schedule_config import ScheduleConfig
    return {
        "status": "success",
        "data": ScheduleConfig.load()
    }


@router.get("/raw", summary="获取快照采集配置")
async def get_raw_config():
    """获取快照采集配置"""
    from app.utils.schedule_config import ScheduleConfig
    return {
        "status": "success",
        "data": ScheduleConfig.get_raw_config()
    }


@router.get("/day-k", summary="获取日K采集配置")
async def get_day_k_config():
    """获取日K采集配置"""
    from app.utils.schedule_config import ScheduleConfig
    return {
        "status": "success",
        "data": ScheduleConfig.get_day_k_config()
    }


@router.get("/special", summary="获取特殊股票池配置")
async def get_special_config():
    """获取特殊股票池配置"""
    from app.utils.schedule_config import ScheduleConfig
    return {
        "status": "success",
        "data": ScheduleConfig.get_special_pool_config()
    }


@router.put("/update", summary="更新配置项")
async def update_config(request: ConfigUpdateRequest):
    """
    更新指定配置项

    参数：
        key: 配置键（支持点号分隔，如 "raw.threads.stock"）
        value: 配置值
    """
    from app.utils.schedule_config import ScheduleConfig

    success = ScheduleConfig.update(request.key, request.value)

    if success:
        return {
            "success": True,
            "message": "配置更新成功",
            "key": request.key,
            "value": request.value
        }
    else:
        raise HTTPException(status_code=500, detail="配置更新失败")


@router.post("/reload", summary="重新加载配置")
async def reload_config():
    """重新从文件加载配置"""
    from app.utils.schedule_config import ScheduleConfig
    config = ScheduleConfig.reload()
    return {
        "status": "success",
        "message": "配置已重新加载",
        "data": config
    }


@router.get("/schedules", summary="获取快照采集时间段")
async def get_schedules():
    """获取快照采集的时间段配置"""
    from app.utils.schedule_config import ScheduleConfig
    schedules = ScheduleConfig.get_raw_schedules()
    return {
        "status": "success",
        "data": {
            "schedules": schedules,
            "description": {
                "09:25:00": "开盘集合竞价后采集一次",
                "09:31:30~11:30:00": "早盘连续竞价，每30秒采集",
                "13:00:00~14:27:00": "午盘连续竞价，每30秒采集",
                "15:00:00": "收盘采集一次"
            }
        }
    }
