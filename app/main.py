"""
文件名：main.py
作用说明：
    项目 API 总入口。
    负责：
        1. 创建 FastAPI 应用
        2. 注册各类子 API（swagger 测试 / 正式接口）
        3. 提供 uvicorn 启动入口

所属层级：
    项目启动层（Application Entry）
"""

from fastapi import FastAPI

# =========================
# 引入 Swagger 测试 API
# =========================
from app.api.swagger.test_block_api import router as block_test_router  # ← 改这里！

# =========================
# 创建主应用
# =========================
app = FastAPI  (
    title="TXDYGPLHXT",
    description="体系化板块-个股联动量化系统",
    version="0.1.0"
)

# 使用 include_router 注册路由
app.include_router(block_test_router, prefix="/debug")

@app.get("/health")
def health_check():
    return {"status": "ok"}
    """
    服务健康检查接口
    """
    return {"status": "ok"}
