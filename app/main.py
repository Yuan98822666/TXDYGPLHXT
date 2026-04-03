"""
天下第一股票量化系统 - FastAPI 入口

版本：v0.2.0
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ==========================================
# Lifespan 上下文管理器（替代 on_event）
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    try:
        from app.scheduler.collector_scheduler import start_scheduler
        start_scheduler()
        logger.info("采集调度器已自动启动")
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
    
    yield  # 运行中
    
    # 关闭
    try:
        from app.scheduler.collector_scheduler import stop_scheduler
        stop_scheduler()
        logger.info("采集调度器已停止")
    except Exception as e:
        logger.error(f"停止调度器失败: {e}")


# 创建 FastAPI 实例
app = FastAPI(
    title="天下第一股票量化系统",
    description="基础数据采集 + 快照数据采集 + 自动调度",
    version="0.2.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 导入并注册 API 路由
# ==========================================
from app.api.collector.base_collector import router as base_collector_router
from app.api.collector.raw_collector import router as raw_collector_router
from app.api.collector.special_pool import router as special_pool_router
from app.api.collector.schedule_api import router as schedule_router
from app.api.collector.scheduler_api import router as scheduler_router
from app.api.cookiemanager.eastmoney_cookie_router import router as cookie_router

app.include_router(base_collector_router, prefix="/api/collector/base", tags=["基础数据采集"])
app.include_router(raw_collector_router, prefix="/api/collector/raw", tags=["快照数据采集"])
app.include_router(special_pool_router, prefix="/api/collector/special", tags=["特殊股票池采集"])
app.include_router(schedule_router, prefix="/api/collector/schedule", tags=["采集频率配置"])
app.include_router(scheduler_router, tags=["采集调度器"])
app.include_router(cookie_router, prefix="/api/cookie", tags=["Cookie 管理"])


@app.get("/")
async def root():
    return {
        "message": "天下第一股票量化系统",
        "version": "v0.3.0",
        "docs": "/docs",
        "scheduler": "自动启动"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="localhost", port=8084, reload=True)