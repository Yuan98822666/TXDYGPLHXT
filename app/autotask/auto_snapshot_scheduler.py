# app/autotask/auto_snapshot_scheduler.py
import asyncio
import logging
from datetime import datetime, time, date
from sqlalchemy.orm import sessionmaker
from app.db.session import engine
from app.autotask.auto_snapshot_state import auto_snapshot_state
from app.collectors.dispatcher import run_snapshot_cycle
from app.utils.trading_day import TradingDayUtils
from app.config.settings import settings

logger = logging.getLogger(__name__)

# 精确的采集时间点配置
_EXACT_CAPTURE_TIMES = [
    time(9, 25, 0),  # 早晨9:25:00
    time(14, 27, 0),  # 下午2:27:00  
    time(15, 0, 0),  # 下午3:00:00
]

# 高频采集时间段
_HIGH_FREQ_PERIODS = [
    (time(9, 30), time(11, 30)),  # 上午9:30-11:30
    (time(13, 0), time(14, 27)),  # 下午1:00-2:27
]


def _is_in_high_freq_period(current_time: time) -> bool:
    """判断当前时间是否在高频采集时间段内"""
    for start, end in _HIGH_FREQ_PERIODS:
        if start <= current_time <= end:
            return True
    return False


def _is_exact_capture_time(current_time: time) -> bool:
    """判断当前时间是否为精确采集时间点（允许1秒误差）"""
    for exact_time in _EXACT_CAPTURE_TIMES:
        time_diff = abs(
            (current_time.hour * 3600 + current_time.minute * 60 + current_time.second) -
            (exact_time.hour * 3600 + exact_time.minute * 60 + exact_time.second)
        )
        if time_diff <= 1:  # 允许1秒误差
            return True
    return False


def _should_execute_snapshot(current_time: time) -> tuple[bool, str]:
    """
    判断是否应该执行快照采集

    Returns:
        tuple[bool, str]: (是否执行, 执行原因)
    """
    # 检查精确时间点
    if _is_exact_capture_time(current_time):
        return True, "精确时间点采集"

    # 检查高频采集期（每分钟的0秒和30秒）
    if _is_in_high_freq_period(current_time):
        if current_time.second in [0, 30]:
            return True, f"高频期采集 ({current_time.second}秒)"

    return False, ""


async def auto_snapshot_scheduler_loop():
    """
    改进的自动快照调度器

    采集策略：
    1. 早晨9:25:00自动采集一次
    2. 下午2:27:00采集一次  
    3. 下午3:00:00采集一次
    4. 上午9:30-11:30期间，每分钟的0秒和30秒各采集一次
    5. 下午1:00-2:27:00期间，每分钟的0秒和30秒各采集一次
    """
    logger.info("🔄 自动快照调度器启动（精确交易日模式）")
    SessionLocal = sessionmaker(bind=engine)

    # 用于避免重复执行精确时间点
    executed_exact_times = set()

    while True:
        try:
            # 检查全局开关状态
            enabled = await auto_snapshot_state.is_enabled()
            if not enabled:
                await asyncio.sleep(0.5)
                continue

            with SessionLocal() as db:
                # 检查今天是否为交易日
                if not TradingDayUtils.is_today_trading_day(db):
                    logger.debug("📅 今日非交易日，跳过采集")
                    await asyncio.sleep(60)  # 非交易日等待1分钟
                    continue

                now = datetime.now()
                current_time = now.time()
                should_execute, reason = _should_execute_snapshot(current_time)

                if should_execute:
                    # 避免精确时间点重复执行
                    time_key = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                    if "精确时间点" in reason:
                        if time_key in executed_exact_times:
                            await asyncio.sleep(0.1)
                            continue
                        executed_exact_times.add(time_key)
                        # 每天最多重置3次精确时间点记录
                        if len(executed_exact_times) >= 3:
                            executed_exact_times.clear()

                    logger.info(f"✅ 触发自动快照 ({reason})")
                    try:
                        run_snapshot_cycle()
                    except Exception as e:
                        logger.error(f"❌ 快照执行失败: {e}")

                # 动态调整睡眠时间以提高精度
                if _is_in_high_freq_period(current_time) or _is_exact_capture_time(current_time):
                    await asyncio.sleep(0.1)  # 高精度轮询
                else:
                    await asyncio.sleep(1)  # 普通轮询

        except Exception as e:
            logger.exception(f"🚨 调度器异常: {e}")
            await asyncio.sleep(1)