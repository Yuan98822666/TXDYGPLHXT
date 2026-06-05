"""
天下第一股票量化系统 - FastAPI 入口

版本：v0.3.0

更新：
    - 新增任务管理模块（TaskManager）
    - 支持任务级别的开关控制
    - 支持调度配置动态修改
    - 配置完全内存化
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 配置日志
import os
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# 创建日志目录
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 配置日志格式
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(log_format)

# 控制台处理器（使用 UTF-8 编码）
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
# 强制控制台使用 UTF-8
if hasattr(console_handler.stream, 'reconfigure'):
    console_handler.stream.reconfigure(encoding='utf-8')

# 文件处理器（按日期滚动）
file_handler = TimedRotatingFileHandler(
    filename=log_dir / "app.log",
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# 配置根日志器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = []  # 清除已有处理器
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


# ==========================================
# Lifespan 上下文管理器（替代 on_event）
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时：
        - 加载任务配置到内存
        - 启动任务调度器
    
    关闭时：
        - 停止调度器
        - 可选：保存配置到文件
    """
    # 启动
    try:
        from app.scheduler.task_manager import get_task_manager, start_scheduler
        # 初始化任务管理器（加载配置）
        manager = get_task_manager()
        logger.info(f"任务配置加载完成，共 {len(manager.tasks)} 个任务")
        
        # 启动调度器
        start_scheduler()
        logger.info("任务调度器已自动启动")
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
    
    yield  # 运行中
    
    # 关闭
    try:
        from app.scheduler.task_manager import stop_scheduler
        stop_scheduler()
        logger.info("任务调度器已停止")
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
from app.api.collector.task_api import router as task_router
from app.api.cookiemanager.eastmoney_cookie_router import router as cookie_router
from app.api.stock.stock_mark_api import router as stock_mark_router
from app.api.block.block_flow_api import router as block_flow_router
from app.api.analysis.zt_potential_api import router as zt_potential_router

app.include_router(base_collector_router, prefix="/api/collector/base", tags=["基础数据采集"])
app.include_router(raw_collector_router, prefix="/api/collector/raw", tags=["快照数据采集"])
app.include_router(special_pool_router, prefix="/api/collector/special", tags=["特殊股票池采集"])
app.include_router(schedule_router, prefix="/api/collector/schedule", tags=["采集频率配置"])
app.include_router(scheduler_router, tags=["采集调度器（旧）"])
app.include_router(task_router, prefix="/api/task", tags=["任务管理"])
app.include_router(cookie_router, prefix="/api/cookie", tags=["Cookie 管理"])
app.include_router(stock_mark_router, tags=["股票标记管理"])
app.include_router(block_flow_router, prefix="/api/block-flow", tags=["板块资金流向"])
app.include_router(zt_potential_router, prefix="/api", tags=["涨停潜力分析"])


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