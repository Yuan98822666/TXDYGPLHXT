# E:\Python Project\TXDYGPLHXT\app\autotask\auto_decision_scheduler.py
"""
决策调度器（独立于快照采集）
职责：
  1. 每日 14:30 触发「盘尾决策」——生成 decision_stock_daily 表
  2. 每日 09:25 触发「竞价验证」——生成 decision_open_validation 表

设计原则：
  - 不做数据采集，只调用已存在的 API
  - 严格依赖交易日历（非交易日不执行）
  - 使用异步 HTTP 客户端调用本地 FastAPI 接口（解耦）
"""

import logging
from datetime import date, datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx

from app.utils.trading_day import TradingDayUtils  # 判断是否交易日
from app.config.settings  import settings

# 配置日志
logger = logging.getLogger(__name__)

# 本地 API 基础地址（假设服务运行在 localhost:8000）
BASE_URL = f"http://localhost:{settings.APP_PORT}"


async def trigger_daily_decision():
    """
    触发盘尾决策（14:30 执行）
    功能：调用 /api/v1/decision/run-daily?trade_date=今日
    """
    today = date.today()

    # 仅在交易日执行
    if not TradingDayUtils.is_trading_day(today):
        logger.info(f"[决策调度] {today} 非交易日，跳过盘尾决策")
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/pwjc/run-daily",params={"trade_date": today.isoformat()})
            response.raise_for_status()
            result = response.json()
            logger.info(f"[决策调度] 盘尾决策完成: {result}")
    except Exception as e:
        logger.error(f"[决策调度] 盘尾决策失败: {e}")


async def trigger_open_validation():
    """
    触发竞价验证（09:25 执行）
    功能：调用 /api/v1/decision/validate-open?trade_date=今日
    注意：验证的是“今日”的开盘，对应昨日的 ALLOW 决策
    """
    today = date.today()

    if not TradingDayUtils.is_trading_day(today):
        logger.info(f"[决策调度] {today} 非交易日，跳过竞价验证")
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/pwjc/validate-open",params={"trade_date": today.isoformat()})
            response.raise_for_status()
            result = response.json()
            logger.info(f"[决策调度] 竞价验证完成: {result}")
    except Exception as e:
        logger.error(f"[决策调度] 竞价验证失败: {e}")


def schedule_decision_tasks(scheduler: AsyncIOScheduler):
    """
    注册决策相关定时任务到调度器
    调用时机：在 main.py 的 lifespan 中调用
    """
    logger.info("注册决策调度任务...")

    # 任务1: 每日 14:30 执行盘尾决策 # 允许5分钟内补触发
    scheduler.add_job(trigger_daily_decision, trigger=CronTrigger(hour=14, minute=30), id='daily_decision',replace_existing=True, misfire_grace_time=300)
    logger.info("✅ 已注册: 盘尾决策 (14:30)")

    # 任务2: 每日 09:25 执行竞价验证  # 允许2分钟内补触发（集合竞价关键）
    scheduler.add_job(trigger_open_validation, trigger=CronTrigger(hour=9, minute=25), id='open_validation',replace_existing=True, misfire_grace_time=120)
    logger.info("✅ 已注册: 竞价验证 (09:25)")