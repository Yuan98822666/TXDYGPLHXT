#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息采集任务配置 API

提供消息采集任务的配置管理：
- 获取消息采集任务列表
- 更新采集间隔
- 启用/禁用任务
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.scheduler.task_manager import get_task_manager

router = APIRouter(prefix="/api/messagesrc/config", tags=["消息采集配置"])


class MessageTaskConfig(BaseModel):
    """消息采集任务配置"""
    name: str
    display_name: str
    enabled: bool
    interval_minutes: int
    last_run_time: Optional[str] = None
    last_run_status: Optional[str] = None


class UpdateIntervalRequest(BaseModel):
    """更新间隔请求"""
    interval_minutes: int


# 消息采集任务名称列表
MESSAGE_TASK_NAMES = [
    "cls_telegram",
    "cls_a_share", 
    "cls_company_depth",
    "cls_headline",
    "cls_global",
]


@router.get("/tasks")
async def get_message_tasks():
    """
    获取所有消息采集任务配置
    """
    manager = get_task_manager()
    tasks = []
    
    for task_name in MESSAGE_TASK_NAMES:
        if task_name not in manager.tasks:
            continue
            
        task = manager.tasks[task_name]
        
        # 计算间隔分钟数（从调度配置中获取）
        interval_minutes = 5  # 默认值
        if task.schedules:
            # 获取第一个调度配置的间隔
            schedule = task.schedules[0]
            if schedule.interval_seconds:
                interval_minutes = schedule.interval_seconds // 60
        
        tasks.append({
            "name": task.name,
            "display_name": task.display_name,
            "enabled": task.enabled,
            "interval_minutes": interval_minutes,
            "last_run_time": task.last_run_time.isoformat() if task.last_run_time else None,
            "last_run_status": task.last_run_status,
        })
    
    return {
        "status": "success",
        "data": tasks
    }


@router.put("/tasks/{task_name}/interval")
async def update_task_interval(task_name: str, request: UpdateIntervalRequest):
    """
    更新消息采集任务的间隔时间
    
    Args:
        task_name: 任务名称
        request: 包含新的间隔时间（分钟）
    """
    if task_name not in MESSAGE_TASK_NAMES:
        raise HTTPException(status_code=400, detail=f"无效的任务名称: {task_name}")
    
    if request.interval_minutes < 1:
        raise HTTPException(status_code=400, detail="间隔时间不能小于1分钟")
    
    manager = get_task_manager()
    
    if task_name not in manager.tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
    
    task = manager.tasks[task_name]
    
    # 更新所有调度配置的间隔
    interval_seconds = request.interval_minutes * 60
    for schedule in task.schedules:
        schedule.interval_seconds = interval_seconds
    
    # 保存配置到文件
    manager.save_config()
    
    return {
        "status": "success",
        "message": f"任务 {task.display_name} 的采集间隔已更新为 {request.interval_minutes} 分钟",
        "data": {
            "task_name": task_name,
            "interval_minutes": request.interval_minutes,
        }
    }


@router.post("/tasks/{task_name}/enable")
async def enable_message_task(task_name: str):
    """启用消息采集任务"""
    if task_name not in MESSAGE_TASK_NAMES:
        raise HTTPException(status_code=400, detail=f"无效的任务名称: {task_name}")
    
    manager = get_task_manager()
    success = manager.enable_task(task_name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
    
    manager.save_config()
    
    return {
        "status": "success",
        "message": f"任务 {task_name} 已启用"
    }


@router.post("/tasks/{task_name}/disable")
async def disable_message_task(task_name: str):
    """禁用消息采集任务"""
    if task_name not in MESSAGE_TASK_NAMES:
        raise HTTPException(status_code=400, detail=f"无效的任务名称: {task_name}")
    
    manager = get_task_manager()
    success = manager.disable_task(task_name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
    
    manager.save_config()
    
    return {
        "status": "success",
        "message": f"任务 {task_name} 已禁用"
    }


@router.post("/tasks/{task_name}/run")
async def run_message_task(task_name: str):
    """
    手动执行消息采集任务
    
    首次执行时自动检测数据库状态，决定全量或增量采集
    """
    if task_name not in MESSAGE_TASK_NAMES:
        raise HTTPException(status_code=400, detail=f"无效的任务名称: {task_name}")
    
    manager = get_task_manager()
    result = manager.run_task_once(task_name)
    
    return {
        "status": "success" if result == "started" else "error",
        "message": result,
    }
