"""
交易日程判断工具。
"""

from datetime import datetime, time, date
from sqlalchemy.orm import Session
from app.models.system.market_state_date import MarketStateDate


_TRADING_PERIODS = [
    (time(9, 25), time(11, 31)),
    (time(13, 0), time(15, 1)),
]


def is_currently_in_trading_hours() -> bool:
    now_time = datetime.now().time()
    if datetime.now().weekday() >= 5:
        return False
    for start, end in _TRADING_PERIODS:
        if start <= now_time <= end:
            return True
    return False


def is_today_a_trading_day(db: Session) -> bool:
    today = date.today()
    record = db.query(MarketStateDate).filter(
        MarketStateDate.market_date == today,
        MarketStateDate.market_state == 0
    ).first()
    return record is not None