# app/utils/trading_day.py
"""
交易日工具类
提供交易日相关的查询功能
"""

from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.system.market_state_date import MarketStateDate


class TradingDayUtils:
    """
    交易日工具类

    提供以下功能：
    - 判断某天是否为交易日
    - 获取上一个交易日
    - 获取下一个交易日
    """

    @staticmethod
    def is_trading_day(check_date: date, db: Session) -> bool:
        """
        判断指定日期是否为交易日

        Args:
            check_date: 要检查的日期
            db: 数据库会话

        Returns:
            bool: True 表示是交易日，False 表示非交易日
        """
        record = db.query(MarketStateDate).filter(
            MarketStateDate.market_date == check_date,
            MarketStateDate.market_state == 0  # 0 表示开市
        ).first()
        return record is not None

    @staticmethod
    def get_previous_trading_day(target_date: date, db: Session) -> Optional[date]:
        """
        获取指定日期的上一个交易日

        Args:
            target_date: 目标日期
            db: 数据库会话

        Returns:
            Optional[date]: 上一个交易日，如果找不到返回 None
        """
        current_date = target_date - timedelta(days=1)
        days_checked = 0
        max_days_back = 365  # 最多回溯一年

        while days_checked < max_days_back:
            if TradingDayUtils.is_trading_day(current_date, db):
                return current_date
            current_date -= timedelta(days=1)
            days_checked += 1

        return None

    @staticmethod
    def get_next_trading_day(target_date: date, db: Session) -> Optional[date]:
        """
        获取指定日期的下一个交易日

        Args:
            target_date: 目标日期
            db: 数据库会话

        Returns:
            Optional[date]: 下一个交易日，如果找不到返回 None
        """
        current_date = target_date + timedelta(days=1)
        days_checked = 0
        max_days_forward = 365  # 最多向前查找一年

        while days_checked < max_days_forward:
            if TradingDayUtils.is_trading_day(current_date, db):
                return current_date
            current_date += timedelta(days=1)
            days_checked += 1

        return None

    @staticmethod
    def is_today_trading_day(db: Session) -> bool:
        """
        判断今天是否为交易日

        Args:
            db: 数据库会话

        Returns:
            bool: True 表示今天是交易日
        """
        return TradingDayUtils.is_trading_day(date.today(), db)