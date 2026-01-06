from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging

# 导入你的 API
from app.api.v1.snapshot import router as snapshot_router

from fastapi.middleware.cors import CORSMiddleware
# 新增导入调度器
from app.services.auto_snapshot_scheduler import auto_snapshot_scheduler_loop

# 配置日志
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动自动快照调度器（默认开启）
    asyncio.create_task(auto_snapshot_scheduler_loop())
    yield

app = FastAPI(title="TXDYGPLHXT 后台服务", description="提供板块活跃度快照采集与查询接口", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 允许前端开发服务器访问
    allow_credentials=True,
    allow_methods=["*"],                      # 允许所有 HTTP 方法（GET, POST 等）
    allow_headers=["*"],                      # 允许所有请求头
)


app.include_router(snapshot_router)
# app.include_router(hot_stocks_router)
@app.get("/")
async def root():
    return {"message": "欢迎使用 TXDYGPLHXT 快照服务", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="localhost", port=8084, reload=True)