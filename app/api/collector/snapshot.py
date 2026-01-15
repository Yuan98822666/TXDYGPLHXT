from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.collectors.dispatcher import run_snapshot_cycle
from app.autotask.auto_snapshot_state import auto_snapshot_state

router = APIRouter(prefix="/snapshot")
@router.post("/blockstock", tags=["手动下载数据板块股票数据1次"])
async def trigger_snapshot(background_tasks: BackgroundTasks):
    """
    手动触发一次板块快照采集与入库。
    使用后台任务避免阻塞 HTTP 请求。
    """
    try:
        # 将耗时任务加入后台（可选：也可直接调用，看是否超时）
        background_tasks.add_task(run_snapshot_cycle)
        return {"status": "success", "message": "快照任务已启动，请稍后查看数据库。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"快照触发失败: {str(e)}")

# === 新增接口 ===
@router.get("/auto-status", tags=["自动快照控制"])
async def get_auto_snapshot_status():
    """获取自动快照当前状态（内存中）"""
    enabled = await auto_snapshot_state.is_enabled()
    return {"enabled": enabled}


@router.post("/auto-toggle", tags=["自动快照控制"])
async def toggle_auto_snapshot():
    """切换自动快照开关（仅内存，重启恢复默认开启）"""
    new_status = await auto_snapshot_state.toggle()
    action = "开启" if new_status else "关闭"
    return {
        "enabled": new_status,
        "message": f"自动快照已{action}（服务重启后自动恢复开启）"
    }
