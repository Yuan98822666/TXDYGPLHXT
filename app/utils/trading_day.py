"""
交易日工具类
提供交易日相关的查询功能，依赖数据库中的 MarketStateDate 表

核心功能：
- 判断某天是否为交易日（开市状态）
- 获取指定日期的上一个/下一个交易日
- 判断今天是否为交易日

数据库依赖：
- 表：MarketStateDate
- 字段：market_date (日期), market_state (0=开市, 1=休市)

设计考虑：
- 最大回溯/前溯限制为365天，防止无限循环
- 使用 SQLAlchemy ORM 查询，保证数据库会话正确管理
- 静态方法设计，便于在任何地方调用
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

        参数:
            check_date (date): 要检查的日期
            db (Session): 数据库会话对象

        返回:
            bool: True 表示是交易日（开市），False 表示非交易日（休市或周末）

        查询逻辑:
            在 MarketStateDate 表中查找：
            - market_date 等于指定日期
            - market_state 等于 0（表示开市）
            存在记录则返回 True，否则返回 False
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

        参数:
            target_date (date): 目标日期
            db (Session): 数据库会话对象

        返回:
            Optional[date]: 上一个交易日，如果找不到返回 None

        查找策略:
            1. 从目标日期前一天开始
            2. 逐日向前检查是否为交易日
            3. 最多回溯365天（防止无限循环）
            4. 找到第一个交易日立即返回
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

        参数:
            target_date (date): 目标日期
            db (Session): 数据库会话对象

        返回:
            Optional[date]: 下一个交易日，如果找不到返回 None

        查找策略:
            1. 从目标日期后一天开始
            2. 逐日向后检查是否为交易日
            3. 最多前溯365天（防止无限循环）
            4. 找到第一个交易日立即返回
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

        参数:
            db (Session): 数据库会话对象

        返回:
            bool: True 表示今天是交易日

        实现方式:
            调用 is_trading_day 方法，传入当前日期
        """
        return TradingDayUtils.is_trading_day(date.today(), db)