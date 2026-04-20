"""
股票相关 API 路由
"""
from fastapi import APIRouter
from app.api.stock.stock_mark_api import router as stock_mark_router

router = APIRouter()
router.include_router(stock_mark_router)
