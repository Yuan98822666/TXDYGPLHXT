import asyncio
import logging
from sqlalchemy.orm import sessionmaker

from app.db.session import engine
from app.autotask.auto_snapshot_state import auto_snapshot_state
from app.utils.trading_schedule import is_today_a_trading_day, is_currently_in_trading_hours
from app.collectors.dispatcher import run_snapshot_cycle

# 新增导入 settings
from app.config.settings import settings  # 👈 关键修改

logger = logging.getLogger(__name__)


async def auto_snapshot_scheduler_loop():
    logger.info(f"🔄 自动快照调度器启动（间隔: {settings.AUTO_SNAPSHOT_INTERVAL_SECONDS}秒，默认开启）")
    SessionLocal = sessionmaker(bind=engine)

    while True:
        try:
            enabled = await auto_snapshot_state.is_enabled()
            if not enabled:
                # 即使关闭，也按配置间隔轮询（避免频繁检查）
                await asyncio.sleep(settings.AUTO_SNAPSHOT_INTERVAL_SECONDS)
                continue

            with SessionLocal() as db:
                if not is_today_a_trading_day(db):
                    logger.debug("📅 今日非交易日，延长等待")
                    await asyncio.sleep(60)  # 非交易日可等久一点
                    continue

            if not is_currently_in_trading_hours():
                await asyncio.sleep(settings.AUTO_SNAPSHOT_INTERVAL_SECONDS)
                continue

            logger.info("✅ 触发自动快照")
            run_snapshot_cycle()

        except Exception as e:
            logger.exception(f"🚨 调度异常: {e}")

        # 使用配置的间隔
        await asyncio.sleep(settings.AUTO_SNAPSHOT_INTERVAL_SECONDS)
