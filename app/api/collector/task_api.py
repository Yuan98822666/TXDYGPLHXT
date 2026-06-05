# -*- coding: utf-8 -*-
"""
任务管理 API 接口

功能：
    - 自动任务管理（开启/关闭/执行）
    - 调度配置管理（查看/编辑/删除）
    - 状态查看

接口列表：
    GET    /api/task/status              → 获取所有任务状态
    POST   /api/task/start-all           → 开启所有任务
    POST   /api/task/stop-all            → 关闭所有任务
    
    GET    /api/task/runtime-config      → 获取运行时配置
    PUT    /api/task/runtime-config      → 更新运行时配置
    POST   /api/task/runtime-config/reset → 重置运行时配置
    
    POST   /api/task/{task_name}/enable  → 开启单个任务
    POST   /api/task/{task_name}/disable → 关闭单个任务
    POST   /api/task/{task_name}/run     → 手动执行单个任务
    
    GET    /api/task/{task_name}/schedule        → 获取任务调度配置
    PUT    /api/task/{task_name}/schedule        → 更新调度配置项
    POST   /api/task/{task_name}/schedule        → 添加调度配置项
    DELETE /api/task/{task_name}/schedule/{idx}  → 删除调度配置项
    
    POST   /api/task/scheduler/start    → 启动调度器
    POST   /api/task/scheduler/stop     → 停止调度器
    GET    /api/task/scheduler/status   → 调度器状态
    
    POST   /api/task/config/save        → 保存配置到文件
    POST   /api/task/config/reload      → 重新加载配置
"""
from fastapi import APIRouter, HTTPException, Path, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

router = APIRouter(tags=["任务管理"])


# ==================== 请求模型 ====================

class ScheduleUpdateRequest(BaseModel):
    """调度配置更新请求"""
    index: int
    updates: Dict[str, Any]


class ScheduleAddRequest(BaseModel):
    """调度配置添加请求"""
    name: str
    type: str = "once"
    time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    interval_seconds: int = 30
    action: Optional[str] = None


class RuntimeConfigResponse(BaseModel):
    """运行时配置响应"""
    status: str
    data: Dict[str, Any]
    timestamp: str


class RuntimeConfigUpdateRequest(BaseModel):
    """运行时配置更新请求"""
    db_pool_size: Optional[int] = Field(None, ge=5, le=100, description="数据库连接池大小")
    db_max_overflow: Optional[int] = Field(None, ge=0, le=100, description="数据库最大溢出连接")
    stock_max_workers: Optional[int] = Field(None, ge=1, le=50, description="股票采集器最大并发数")
    stock_batch_size: Optional[int] = Field(None, ge=10, le=500, description="批次大小")
    stock_batch_delay: Optional[float] = Field(None, ge=0.1, le=10.0, description="批次间隔(秒)")
    http_timeout_default: Optional[int] = Field(None, ge=5, le=60, description="HTTP默认超时(秒)")
    http_timeout_fast: Optional[int] = Field(None, ge=1, le=30, description="HTTP快速超时(秒)")


# ==================== 任务状态接口 ====================

@router.get("/status", summary="获取所有任务状态")
async def get_all_tasks_status():
    """
    获取所有任务状态
    
    返回：
        - scheduler_running: 调度器是否运行
        - tasks: 任务列表（包含每个任务的状态、上次执行时间等）
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        return {
            "status": "success",
            "data": manager.get_all_tasks_status(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


# ==================== 任务控制接口 ====================

@router.post("/start-all", summary="开启所有任务")
async def enable_all_tasks():
    """
    开启所有任务
    
    说明：
        - 将所有任务的 enabled 设为 True
        - 调度器会自动检查并执行启用的任务
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        manager.enable_all_tasks()
        
        return {
            "status": "success",
            "message": "所有任务已开启",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/stop-all", summary="关闭所有任务")
async def disable_all_tasks():
    """
    关闭所有任务
    
    说明：
        - 将所有任务的 enabled 设为 False
        - 调度器继续运行，但不会执行任何任务
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        manager.disable_all_tasks()
        
        return {
            "status": "success",
            "message": "所有任务已关闭",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


# ==================== 运行时配置接口（必须在动态路由之前）====================

@router.get("/runtime-config", summary="获取运行时配置", response_model=RuntimeConfigResponse)
async def get_runtime_config_api():
    """获取当前运行时配置"""
    try:
        from app.config.runtime_config import runtime_config
        
        return {
            "status": "success",
            "data": runtime_config.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/runtime-config", summary="更新运行时配置")
async def update_runtime_config_api(request: RuntimeConfigUpdateRequest):
    """更新运行时配置（仅内存）"""
    try:
        from app.config.runtime_config import runtime_config
        
        updates = request.dict(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供要更新的配置项")
        
        success = runtime_config.update(**updates)
        
        if success:
            return {
                "status": "success",
                "message": "配置已更新（仅内存）",
                "data": runtime_config.to_dict(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=500, detail="配置更新失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/runtime-config/reset", summary="重置运行时配置")
async def reset_runtime_config_api():
    """重置运行时配置为默认值"""
    try:
        from app.config.runtime_config import runtime_config
        
        runtime_config.reset_to_defaults()
        
        return {
            "status": "success",
            "message": "配置已重置为默认值",
            "data": runtime_config.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


# ==================== 单个任务控制接口（动态路由）====================

@router.post("/{task_name}/enable", summary="开启单个任务")
async def enable_task(task_name: str = Path(..., description="任务名称（raw/special_pool/day_k）")):
    """
    开启单个任务
    
    参数：
        task_name: 任务名称
            - raw: 快照采集
            - special_pool: 特殊股票池采集
            - day_k: 日K采集
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        success = manager.enable_task(task_name)
        
        if success:
            return {
                "status": "success",
                "message": f"任务 {task_name} 已开启",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/{task_name}/disable", summary="关闭单个任务")
async def disable_task(task_name: str = Path(..., description="任务名称")):
    """
    关闭单个任务
    
    参数：
        task_name: 任务名称
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        success = manager.disable_task(task_name)
        
        if success:
            return {
                "status": "success",
                "message": f"任务 {task_name} 已关闭",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/{task_name}/run", summary="手动执行单个任务")
async def run_task_once(task_name: str = Path(..., description="任务名称")):
    """
    手动执行单个任务（立即执行）
    
    说明：
        - 不受调度控制，立即执行一次
        - 执行完成后更新任务状态
    
    参数：
        task_name: 任务名称
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        result = manager.run_task_once(task_name)
        
        if result.startswith("failed"):
            return {
                "status": "error",
                "message": f"任务执行失败: {result}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "success",
                "message": f"任务 {task_name} 执行完成",
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


# ==================== 调度配置管理接口 ====================

@router.get("/{task_name}/schedule", summary="获取任务调度配置")
async def get_task_schedule(task_name: str = Path(..., description="任务名称")):
    """
    获取任务的调度配置
    
    返回：
        - 任务的所有调度配置项
        - 包括定点执行和区间执行配置
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        
        if task_name not in manager.tasks:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
        
        task = manager.tasks[task_name]
        
        return {
            "status": "success",
            "data": {
                "task_name": task_name,
                "display_name": task.display_name,
                "enabled": task.enabled,
                "schedules": [s.to_dict() for s in task.schedules],
            },
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@router.put("/{task_name}/schedule", summary="更新调度配置项")
async def update_task_schedule(
    task_name: str = Path(..., description="任务名称"),
    request: ScheduleUpdateRequest = Body(..., description="更新请求")
):
    """
    更新任务的调度配置项
    
    请求体：
        - index: 调度项索引（从0开始）
        - updates: 更新内容（如 {"interval_seconds": 60, "start_time": "09:35:00"}）
    
    示例：
        {
            "index": 1,
            "updates": {
                "interval_seconds": 60,
                "start_time": "09:35:00"
            }
        }
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        success = manager.update_task_schedule(task_name, request.index, request.updates)
        
        if success:
            return {
                "status": "success",
                "message": f"调度配置已更新",
                "task_name": task_name,
                "index": request.index,
                "updates": request.updates,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=400, detail="更新失败：任务不存在或索引越界")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/{task_name}/schedule", summary="添加调度配置项")
async def add_task_schedule(
    task_name: str = Path(..., description="任务名称"),
    request: ScheduleAddRequest = Body(..., description="添加请求")
):
    """
    添加调度配置项
    
    请求体：
        - name: 调度名称
        - type: 类型（once=定点, interval=区间）
        - time: 定点执行时间（type=once时必填）
        - start_time: 区间开始时间（type=interval时必填）
        - end_time: 区间结束时间（type=interval时必填）
        - interval_seconds: 执行间隔（秒）
        - action: 动作类型（日K专用：append/replace）
    
    示例：
        {
            "name": "早盘采集",
            "type": "interval",
            "start_time": "09:35:00",
            "end_time": "11:25:00",
            "interval_seconds": 60
        }
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        schedule_data = request.model_dump()
        success = manager.add_task_schedule(task_name, schedule_data)
        
        if success:
            return {
                "status": "success",
                "message": f"调度配置已添加",
                "task_name": task_name,
                "schedule": schedule_data,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_name}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.delete("/{task_name}/schedule/{schedule_index}", summary="删除调度配置项")
async def remove_task_schedule(
    task_name: str = Path(..., description="任务名称"),
    schedule_index: int = Path(..., description="调度项索引")
):
    """
    删除调度配置项
    
    参数：
        - task_name: 任务名称
        - schedule_index: 调度项索引（从0开始）
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        success = manager.remove_task_schedule(task_name, schedule_index)
        
        if success:
            return {
                "status": "success",
                "message": f"调度配置已删除",
                "task_name": task_name,
                "index": schedule_index,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=400, detail="删除失败：任务不存在或索引越界")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ==================== 调度器控制接口 ====================

@router.post("/scheduler/start", summary="启动调度器")
async def start_scheduler():
    """
    启动任务调度器
    
    说明：
        - 启动后台调度线程
        - 按配置自动执行任务
        - 如果在交易时段内启动，会立即执行一次初始化采集
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        manager.start()
        
        return {
            "status": "success",
            "message": "调度器已启动",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/scheduler/stop", summary="停止调度器")
async def stop_scheduler():
    """
    停止任务调度器
    
    说明：
        - 停止后台调度线程
        - 正在执行的任务会继续完成
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        manager.stop()
        
        return {
            "status": "success",
            "message": "调度器已停止",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")


@router.get("/scheduler/status", summary="调度器状态")
async def get_scheduler_status():
    """
    获取调度器状态
    
    返回：
        - running: 是否运行中
        - tasks: 各任务状态
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        
        return {
            "status": "success",
            "data": {
                "running": manager.is_running(),
                "tasks": {name: task.to_dict() for name, task in manager.tasks.items()},
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


# ==================== 配置管理接口 ====================

@router.post("/config/save", summary="保存配置到文件")
async def save_config():
    """
    保存当前配置到文件
    
    说明：
        - 将内存中的配置持久化到 YAML 文件
        - 包括任务开关、调度配置等
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        success = manager.save_config()
        
        if success:
            return {
                "status": "success",
                "message": "配置已保存到文件",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=500, detail="保存失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/config/reload", summary="重新加载配置")
async def reload_config():
    """
    从文件重新加载配置
    
    说明：
        - 放弃内存中的修改
        - 从 YAML 文件重新读取配置
    """
    try:
        from app.scheduler.task_manager import get_task_manager
        
        manager = get_task_manager()
        success = manager.load_config()
        
        if success:
            return {
                "status": "success",
                "message": "配置已重新加载",
                "data": manager.get_all_tasks_status(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=500, detail="加载失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载失败: {str(e)}")
