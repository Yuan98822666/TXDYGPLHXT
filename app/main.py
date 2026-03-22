from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging

# 导入 API 路由
# from app.api.collector.snapshot import router as snapshot_router
# from app.api.derived.minute_snapshot import router as derived_router
# from app.api.event.events import router as events_router
# from app.api.decision.pwjc_routes import router as decision_router
# from app.api.analysis.named_stock_routes import router as named_stock_router

from fastapi.middleware.cors import CORSMiddleware

# 导入调度器
# from app.autotask.auto_snapshot_scheduler import auto_snapshot_scheduler_loop
# from app.autotask.auto_decision_scheduler import schedule_decision_tasks

# 新增：APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 配置日志
logging.basicConfig(level=logging.INFO)

# 创建全局调度器（用于决策任务）
decision_scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动快照调度器（协程循环）
    # asyncio.create_task(auto_snapshot_scheduler_loop())

    # 启动决策调度器（基于 APScheduler）
    decision_scheduler.start()
    # schedule_decision_tasks(decision_scheduler)  # ← 传入 scheduler 实例

    logging.info("✅ 快照循环 + 决策定时任务均已启动")

    yield

    # 关闭调度器
    decision_scheduler.shutdown()


app = FastAPI(
    title="TXDYGPLHXT 后台服务",
    description="提供板块活跃度快照采集与查询接口",
    version="1.1.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(snapshot_router, prefix="/api/snapshot", tags=["快照采集"])
# app.include_router(derived_router, prefix="/api/minute", tags=["1分钟计算"])
# app.include_router(named_stock_router, prefix="/api/analysis", tags=["前端星图"])

@app.get("/")
async def root():
    return {
        "message": "欢迎来到 天下第一A股票股量化分析决策系统",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="localhost", port=8084, reload=True)