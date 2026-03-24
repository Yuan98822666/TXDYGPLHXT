"""
快照 API 路由控制器

功能说明：
- 提供手动触发快照采集的 HTTP 接口
- 提供查询和控制自动快照状态的 HTTP 接口
- 作为 FastAPI 应用的路由层，协调后台任务执行

接口设计原则：
- 手动触发使用 POST 方法（有副作用操作）
- 状态查询使用 GET 方法（只读操作）  
- 状态切换使用 POST 方法（修改状态）
- 所有耗时操作都放入后台任务，避免阻塞 HTTP 响应

依赖组件：
- run_snapshot_cycle: 实际的快照采集执行函数
- auto_snapshot_state: 自动快照状态管理器（内存中）
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.collectors.dispatcher import run_snapshot_cycle
from app.autotask.auto_snapshot_state import auto_snapshot_state
from datetime import datetime

# 创建 API 路由器，所有路由以 "/snapshot" 为前缀
router = APIRouter()


@router.post("/blockstock", summary=["手动下载数据板块股票数据1次"])
async def trigger_snapshot(background_tasks: BackgroundTasks):
    """
    手动触发一次板块快照采集与入库

    HTTP 方法：POST
    路径：/snapshot/blockstock
    标签：手动下载数据板块股票数据1次

    功能说明：
        - 立即启动一次完整的快照采集周期
        - 使用后台任务避免阻塞 HTTP 请求响应
        - 返回成功消息，实际执行结果需要查看数据库或日志

    参数:
        background_tasks (BackgroundTasks): FastAPI 后台任务管理器

    返回:
        dict: 包含状态和消息的 JSON 响应
        {
            "status": "success",
            "message": "快照任务已启动，请稍后查看数据库。"
        }

    异常处理:
        - 捕获所有异常并转换为 500 错误响应
        - 返回具体的错误信息便于调试

    设计考虑:
        - 即使直接调用 run_snapshot_cycle() 也不会超时（通常几秒内完成）
        - 但使用后台任务是更好的实践，保证 HTTP 响应快速返回
        - 适用于手动测试、紧急数据补采等场景
    """
    try:
        # 将耗时任务加入后台（可选：也可直接调用，看是否超时）
        background_tasks.add_task(run_snapshot_cycle)
        print("下载数据开始：   \t"  + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return {"status": "success", "message": "快照任务已启动，请稍后查看数据库。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"快照触发失败: {str(e)}")


@router.get("/auto-status", summary=["自动快照状态"])
async def get_auto_snapshot_status():
    """
    获取自动快照当前状态（内存中）

    HTTP 方法：GET  
    路径：/snapshot/auto-status
    标签：自动快照状态

    功能说明：
        - 查询当前自动快照调度器的开关状态
        - 状态存储在内存中，服务重启后会恢复默认值

    返回:
        dict: 包含启用状态的 JSON 响应
        {
            "enabled": true  # 或 false
        }

    状态说明:
        - true: 自动快照已开启，调度器会按计划执行采集
        - false: 自动快照已关闭，调度器会跳过所有采集逻辑

    使用场景:
        - 监控系统检查自动采集是否正常运行
        - 前端界面显示当前状态
        - 自动化脚本根据状态决定是否执行其他操作
    """
    enabled = await auto_snapshot_state.is_enabled()
    return {"enabled": enabled}


@router.post("/auto-toggle", summary=["自动快照控制"])
async def toggle_auto_snapshot():
    """
    切换自动快照开关（仅内存，重启恢复默认开启）

    HTTP 方法：POST
    路径：/snapshot/auto-toggle  
    标签：自动快照控制

    功能说明：
        - 切换自动快照的启用/禁用状态
        - 状态仅保存在内存中，服务重启后会恢复为默认开启状态
        - 返回切换后的状态和操作描述

    返回:
        dict: 包含新状态和消息的 JSON 响应
        {
            "enabled": false,  # 切换后的新状态
            "message": "自动快照已关闭（服务重启后自动恢复开启）"
        }

    状态持久性说明:
        - 内存状态：适合临时调试、维护期间临时关闭
        - 重启恢复：确保服务意外重启后自动采集功能正常
        - 如需持久化状态，需要扩展为数据库存储

    使用场景:
        - 维护期间临时关闭自动采集
        - 调试时手动控制采集节奏
        - 应急情况下暂停自动任务
    """
    new_status = await auto_snapshot_state.toggle()
    action = "开启" if new_status else "关闭"
    return {
        "enabled": new_status,
        "message": f"自动快照已{action}（服务重启后自动恢复开启）"
    }