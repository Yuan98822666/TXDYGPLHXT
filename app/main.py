from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 如果前端跨域需要

# 导入你的 API 路由
from app.api.snapshot import router as snapshot_router

# 创建 FastAPI 应用实例
app = FastAPI(title="TXDYGPLHXT 后台服务", description="提供板块活跃度快照采集与查询接口", version="1.0.0" )

# 注册路由
app.include_router(snapshot_router)


# 可选：根路径欢迎信息
@app.get("/")
async def root():
    return {"message": "欢迎使用 TXDYGPLHXT 快照服务", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8084,
        reload=True,  # 开发期强烈建议打开
    )
