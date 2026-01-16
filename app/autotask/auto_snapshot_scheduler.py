"""
自动快照调度器

功能说明：
- 实现精确的交易日自动快照采集策略
- 支持多种采集频率：精确时间点 + 高频时间段
- 智能判断交易日，非交易日自动跳过
- 支持运行时动态开关控制

采集策略详解：
1. 精确时间点采集（每天3次）：
   - 09:25:00 早晨集合竞价结束
   - 14:27:00 下午临近收盘
   - 15:00:00 收盘时刻

2. 高频时间段采集（每30秒一次）：
   - 上午：09:30-11:30（连续竞价时段）
   - 下午：13:00-14:27（连续竞价时段）

3. 非交易日处理：
   - 自动检测是否为交易日
   - 非交易日每分钟检查一次，避免资源浪费

设计特点：
- 高精度时间轮询（高频期0.1秒，普通期1秒）
- 防重复执行机制（精确时间点去重）
- 完善的日志记录和异常处理
- 与全局状态管理器集成
"""

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

# =============================================================================
# 采集时间配置
# =============================================================================

# 精确的采集时间点配置（每天固定3个时间点）
_EXACT_CAPTURE_TIMES = [
    time(9, 25, 0),  # 早晨9:25:00 - 集合竞价结束
    time(14, 27, 0),  # 下午2:27:00 - 临近收盘
    time(15, 0, 0),  # 下午3:00:00 - 收盘时刻
]

# 高频采集时间段配置（连续竞价时段）
_HIGH_FREQ_PERIODS = [
    (time(9, 30), time(11, 30)),  # 上午9:30-11:30
    (time(13, 0), time(14, 27)),  # 下午1:00-2:27
]


def _is_in_high_freq_period(current_time: time) -> bool:
    """
    判断当前时间是否在高频采集时间段内

    参数:
        current_time (time): 当前时间（时:分:秒）

    返回:
        bool: True 表示在高频采集时间段内

    判断逻辑:
        - 遍历所有高频时间段
        - 检查当前时间是否在任一时间段的开始和结束之间（包含边界）
    """
    for start, end in _HIGH_FREQ_PERIODS:
        if start <= current_time <= end:
            return True
    return False


def _is_exact_capture_time(current_time: time) -> bool:
    """
    判断当前时间是否为精确采集时间点（允许1秒误差）

    参数:
        current_time (time): 当前时间（时:分:秒）

    返回:
        bool: True 表示匹配某个精确采集时间点

    容错机制:
        - 允许1秒的时间误差（网络延迟、系统调度等）
        - 通过计算秒数差值来判断是否在误差范围内
    """
    for exact_time in _EXACT_CAPTURE_TIMES:
        # 将时间转换为总秒数进行比较
        time_diff = abs(
            (current_time.hour * 3600 + current_time.minute * 60 + current_time.second)
            - (exact_time.hour * 3600 + exact_time.minute * 60 + exact_time.second)
        )
        if time_diff <= 1:  # 允许1秒误差
            return True
    return False


def _should_execute_snapshot(current_time: time) -> tuple[bool, str]:
    """
    判断是否应该执行快照采集

    参数:
        current_time (time): 当前时间（时:分:秒）

    返回:
        tuple[bool, str]: (是否执行, 执行原因)

    决策优先级:
        1. 精确时间点采集（最高优先级）
        2. 高频期采集（次优先级）
        3. 其他时间不采集

    高频期采集规则:
        - 只在每分钟的 0 秒和 30 秒执行
        - 避免过于频繁的采集影响系统性能
    """
    # 检查精确时间点（最高优先级）
    if _is_exact_capture_time(current_time):
        return True, "精确时间点采集"

    # 检查高频采集期（每分钟的0秒和30秒）
    if _is_in_high_freq_period(current_time):
        if current_time.second in [0, 30]:
            return True, f"高频期采集 ({current_time.second}秒)"

    return False, ""


async def auto_snapshot_scheduler_loop():
    """
    改进的自动快照调度器主循环

    核心功能：
        - 持续监控系统时间和自动快照状态
        - 在交易日按预设策略执行快照采集
        - 支持运行时动态开关控制
        - 处理各种异常情况保证稳定性

    执行流程：
        1. 检查全局开关状态，关闭时快速休眠
        2. 获取数据库会话，检查今日是否为交易日
        3. 非交易日：每分钟检查一次
        4. 交易日：按精确策略判断是否执行采集
        5. 执行采集并记录详细日志
        6. 动态调整休眠时间提高时间精度

    并发安全：
        - 使用独立的数据库会话（SessionLocal）
        - 精确时间点防重复执行机制
        - 异常捕获防止调度器崩溃

    性能优化：
        - 高频期0.1秒轮询，保证时间精度
        - 普通期1秒轮询，节省CPU资源
        - 非交易日60秒轮询，减少数据库查询
    """
    logger.info("🔄 自动快照调度器启动（精确交易日模式）")

    # 创建数据库会话工厂
    SessionLocal = sessionmaker(bind=engine)

    # 用于避免重复执行精确时间点（同一天内）
    executed_exact_times = set()

    while True:
        try:
            # 检查全局开关状态
            enabled = await auto_snapshot_state.is_enabled()
            if not enabled:
                await asyncio.sleep(0.5)  # 关闭状态快速轮询
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
                    # 避免精确时间点重复执行（同一秒内）
                    time_key = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                    if "精确时间点" in reason:
                        if time_key in executed_exact_times:
                            await asyncio.sleep(0.1)
                            continue
                        executed_exact_times.add(time_key)

                        # 每天最多重置3次精确时间点记录（防止内存泄漏）
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