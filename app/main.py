"""
天下第一股票量化系统 - FastAPI 入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 导入 API 路由
from app.api.collector.base_collector import router as base_collector_router

# 配置日志
logging.basicConfig(level=logging.INFO)

# 创建 FastAPI 实例
app = FastAPI(
    title="天下第一股票量化系统",
    description="基础数据采集接口",
    version="2.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(base_collector_router, prefix="/api/collector/base", tags=["基础数据采集"])


@app.get("/")
async def root():
    return {
        "message": "天下第一股票量化系统",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="localhost", port=8084, reload=True)
