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

# =========================
# 创建主应用
# =========================
app = FastAPI(title="TXDYGPLHXT", description="体系化板块-个股联动量化系统", version="0.1.0")

# 使用 include_router 注册路由



# ===== 新增：内置 Uvicorn 启动器 =====
if __name__ == "__main__":
    import uvicorn

    # 指定 host、port、reload 等参数
    uvicorn.run(        "app.main:app",  # 与命令行一致的模块路径
        host="127.0.0.1",
        port=8011,  # ← 你想要的端口
        reload=True,  # 开发时自动重载
        log_level="info"
    )