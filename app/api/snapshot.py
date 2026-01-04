from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.collectors.dispatcher import run_snapshot_cycle

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

