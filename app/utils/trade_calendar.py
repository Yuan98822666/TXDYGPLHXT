# -*- coding: utf-8 -*-
"""
交易日历工具 - 统一版本 v2.0

功能：
1. 判断某天是否是交易日（基于内置节假日表 + 数据库MarketStateDate表）
2. 获取距今最近的交易日
3. 获取上一个/下一个交易日

规则：
1. 周六、周日不是交易日
2. 法定节假日不是交易日（维护节假日列表 2024-2026）
3. 数据库中标记为休市的日期不是交易日
4. 其余都是交易日

设计考虑：
- 优先使用内置节假日表（无需数据库连接，性能更好）
- 支持数据库查询作为补充（更灵活，可动态维护）
- 最大回溯/前溯限制为365天，防止无限循环
- 静态方法设计，便于在任何地方调用
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import date, datetime, timedelta
from typing import Optional, Set

logger = logging.getLogger(__name__)


class TradeCalendar:
    """交易日历工具类 - 统一版本"""

    # 中国股市主要节假日（格式：YYYY-MM-DD）
    # 需要每年更新
    HOLIDAYS_2024 = {
        # 元旦
        "2024-01-01",
        # 春节
        "2024-02-09", "2024-02-10", "2024-02-11", "2024-02-12",
        "2024-02-13", "2024-02-14", "2024-02-15", "2024-02-16", "2024-02-17",
        # 清明
        "2024-04-04", "2024-04-05", "2024-04-06",
        # 劳动节
        "2024-05-01", "2024-05-02", "2024-05-03", "2024-05-04", "2024-05-05",
        # 端午
        "2024-06-08", "2024-06-09", "2024-06-10",
        # 中秋
        "2024-09-15", "2024-09-16", "2024-09-17",
        # 国庆
        "2024-10-01", "2024-10-02", "2024-10-03", "2024-10-04",
        "2024-10-05", "2024-10-06", "2024-10-07",
    }

    HOLIDAYS_2025 = {
        # 元旦
        "2025-01-01",
        # 春节
        "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
        "2025-02-01", "2025-02-02", "2025-02-03", "2025-02-04",
        # 清明
        "2025-04-04", "2025-04-05", "2025-04-06",
        # 劳动节
        "2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04", "2025-05-05",
        # 端午
        "2025-05-31", "2025-06-01", "2025-06-02",
        # 中秋
        "2025-10-06", "2025-10-07", "2025-10-08",
        # 国庆
        "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05",
    }

    HOLIDAYS_2026 = {
        # 元旦
        "2026-01-01", "2026-01-02", "2026-01-03",
        # 春节
        "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19",
        "2026-02-20", "2026-02-21", "2026-02-22", "2026-02-23",
        # 清明
        "2026-04-04", "2026-04-05", "2026-04-06",
        # 劳动节
        "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
        # 端午
        "2026-05-29", "2026-05-30", "2026-05-31",
        # 中秋+国庆
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
        "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
    }

    # 合并所有节假日
    ALL_HOLIDAYS: Set[str] = HOLIDAYS_2024 | HOLIDAYS_2025 | HOLIDAYS_2026

    @classmethod
    def is_weekend(cls, check_date: date) -> bool:
        """判断是否是周末"""
        return check_date.weekday() >= 5  # 5=周六, 6=周日

    @classmethod
    def is_holiday(cls, check_date: date) -> bool:
        """判断是否是法定节假日（基于内置表）"""
        date_str = check_date.strftime("%Y-%m-%d")
        return date_str in cls.ALL_HOLIDAYS

    @classmethod
    def is_trade_day(cls, check_date: date = None) -> bool:
        """
        判断某天是否是交易日（基于内置节假日表）

        参数:
            check_date: 日期，默认今天

        返回:
            True/False
        """
        if check_date is None:
            check_date = date.today()

        # 周末不是交易日
        if cls.is_weekend(check_date):
            return False

        # 节假日不是交易日
        if cls.is_holiday(check_date):
            return False

        return True

    @classmethod
    def is_trading_day_from_db(cls, check_date: date, db_session=None) -> bool:
        """
        判断某天是否是交易日（基于数据库MarketStateDate表）

        参数:
            check_date: 要检查的日期
            db_session: 数据库会话对象（可选）

        返回:
            bool: True 表示是交易日（开市），False 表示非交易日
        """
        if db_session is None:
            # 如果没有提供数据库连接，回退到内置表判断
            return cls.is_trade_day(check_date)

        try:
            from app.models.system.sys_market_state_date import MarketStateDate
            record = db_session.query(MarketStateDate).filter(
                MarketStateDate.market_date == check_date,
                MarketStateDate.market_state == 0  # 0 表示开市
            ).first()
            return record is not None
        except Exception as e:
            logger.warning(f"数据库查询失败，回退到内置表: {e}")
            return cls.is_trade_day(check_date)

    @classmethod
    def get_latest_trade_day(cls, check_date: date = None) -> date:
        """
        获取距今最近的交易日

        规则：
        - 如果 check_date 是交易日，返回 check_date
        - 如果 check_date 不是交易日，向前查找最近的交易日

        参数:
            check_date: 日期，默认今天

        返回:
            最近的交易日（date 对象）
        """
        if check_date is None:
            check_date = date.today()

        # 如果是交易日，直接返回
        if cls.is_trade_day(check_date):
            return check_date

        # 向前查找最近的交易日（最多查30天）
        for i in range(1, 31):
            prev_date = check_date - timedelta(days=i)
            if cls.is_trade_day(prev_date):
                logger.debug(f"非交易日 {check_date}，找到最近交易日: {prev_date}")
                return prev_date

        # 兜底：返回 check_date（不应该发生）
        logger.warning(f"未找到交易日，返回默认日期: {check_date}")
        return check_date

    @classmethod
    def get_prev_trade_day(cls, check_date: date = None) -> date:
        """
        获取上一个交易日（严格早于check_date）

        参数:
            check_date: 日期，默认今天

        返回:
            上一个交易日（date 对象）
        """
        if check_date is None:
            check_date = date.today()

        # 向前查找交易日（最多查30天）
        for i in range(1, 31):
            prev_date = check_date - timedelta(days=i)
            if cls.is_trade_day(prev_date):
                return prev_date

        # 兜底
        return check_date - timedelta(days=1)

    @classmethod
    def get_next_trade_day(cls, check_date: date = None) -> date:
        """
        获取下一个交易日

        参数:
            check_date: 日期，默认今天

        返回:
            下一个交易日（date 对象）
        """
        if check_date is None:
            check_date = date.today()

        # 向后查找交易日（最多查30天）
        for i in range(1, 31):
            next_date = check_date + timedelta(days=i)
            if cls.is_trade_day(next_date):
                return next_date

        # 兜底
        return check_date + timedelta(days=1)

    @classmethod
    def get_previous_trading_day(cls, check_date: date = None, db_session=None) -> Optional[date]:
        """
        获取指定日期的上一个交易日（支持数据库查询）

        参数:
            check_date: 目标日期，默认今天
            db_session: 数据库会话对象（可选）

        返回:
            Optional[date]: 上一个交易日，如果找不到返回 None
        """
        if check_date is None:
            check_date = date.today()

        # 如果提供了数据库连接，优先使用数据库
        if db_session is not None:
            try:
                current_date = check_date - timedelta(days=1)
                days_checked = 0
                max_days_back = 365

                while days_checked < max_days_back:
                    if cls.is_trading_day_from_db(current_date, db_session):
                        return current_date
                    current_date -= timedelta(days=1)
                    days_checked += 1
                return None
            except Exception as e:
                logger.warning(f"数据库查询失败，使用内置表: {e}")

        # 使用内置表
        return cls.get_prev_trade_day(check_date)

    @classmethod
    def get_next_trading_day(cls, check_date: date = None, db_session=None) -> Optional[date]:
        """
        获取指定日期的下一个交易日（支持数据库查询）

        参数:
            check_date: 目标日期，默认今天
            db_session: 数据库会话对象（可选）

        返回:
            Optional[date]: 下一个交易日，如果找不到返回 None
        """
        if check_date is None:
            check_date = date.today()

        # 如果提供了数据库连接，优先使用数据库
        if db_session is not None:
            try:
                current_date = check_date + timedelta(days=1)
                days_checked = 0
                max_days_forward = 365

                while days_checked < max_days_forward:
                    if cls.is_trading_day_from_db(current_date, db_session):
                        return current_date
                    current_date += timedelta(days=1)
                    days_checked += 1
                return None
            except Exception as e:
                logger.warning(f"数据库查询失败，使用内置表: {e}")

        # 使用内置表
        return cls.get_next_trade_day(check_date)

    @classmethod
    def get_trade_date_str(cls, check_date: date = None) -> str:
        """
        获取距今最近的交易日（字符串格式）

        参数:
            check_date: 日期，默认今天

        返回:
            最近的交易日字符串，格式：'YYYY-MM-DD'
        """
        latest = cls.get_latest_trade_day(check_date)
        return latest.strftime("%Y-%m-%d")

    @classmethod
    def is_today_trading_day(cls, db_session=None) -> bool:
        """
        判断今天是否为交易日

        参数:
            db_session: 数据库会话对象（可选）

        返回:
            bool: True 表示今天是交易日
        """
        if db_session is not None:
            return cls.is_trading_day_from_db(date.today(), db_session)
        return cls.is_trade_day(date.today())


# 便捷函数（保持向后兼容）
def is_trade_day(check_date: date = None) -> bool:
    """判断是否是交易日"""
    return TradeCalendar.is_trade_day(check_date)


def get_latest_trade_day(check_date: date = None) -> date:
    """获取最近的交易日"""
    return TradeCalendar.get_latest_trade_day(check_date)


def get_prev_trade_day(check_date: date = None) -> date:
    """获取上一个交易日"""
    return TradeCalendar.get_prev_trade_day(check_date)


def get_next_trade_day(check_date: date = None) -> date:
    """获取下一个交易日"""
    return TradeCalendar.get_next_trade_day(check_date)


def get_trade_date_str(check_date: date = None) -> str:
    """获取最近的交易日字符串"""
    return TradeCalendar.get_trade_date_str(check_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== 交易日历工具测试 ===\n")

    # 测试今天
    today = date.today()
    print(f"今天: {today} (星期{['一','二','三','四','五','六','日'][today.weekday()]})")
    print(f"是否交易日: {is_trade_day(today)}")
    print(f"最近交易日: {get_latest_trade_day(today)}")
    print(f"交易日字符串: {get_trade_date_str()}")

    # 测试周末
    print("\n--- 测试周末 ---")
    sunday = date(2026, 3, 29)
    saturday = date(2026, 3, 28)
    print(f"周六 {saturday}: {is_trade_day(saturday)}")
    print(f"周日 {sunday}: {is_trade_day(sunday)}")
    print(f"周日最近交易日: {get_latest_trade_day(sunday)}")

    # 测试节假日
    print("\n--- 测试节假日 ---")
    new_year = date(2026, 1, 1)
    print(f"元旦 {new_year}: {is_trade_day(new_year)}")
    print(f"元旦最近交易日: {get_latest_trade_day(new_year)}")

    # 测试下一个交易日
    print("\n--- 测试下一个交易日 ---")
    print(f"今天下一个交易日: {get_next_trade_day(today)}")
