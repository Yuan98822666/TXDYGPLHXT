# app/utils/time_utils.py
from datetime import datetime
import pytz
from typing import Optional


def current_market_second_str(dt: Optional[datetime] = None) -> str:
    """
    获取中国股市时间（上海时区）的秒级字符串，格式 YYYYMMDDHHMMSS。

    - 如果传入 dt，则将其转换为上海时区后格式化；
    - 如果未传入，则使用当前上海时间。

    注意：若 dt 是 naive datetime（无时区），默认视为 UTC。
    """
    shanghai_tz = pytz.timezone("Asia/Shanghai")

    if dt is None:
        # 当前上海时间
        now_sh = datetime.now(shanghai_tz)
    else:
        # 确保 dt 是带时区的
        if dt.tzinfo is None:
            # 假设传入的是 UTC（常见于数据库存储的 UTC 时间）
            dt = pytz.utc.localize(dt)
        # 转换为上海时间
        now_sh = dt.astimezone(shanghai_tz)

    return now_sh.strftime("%Y%m%d%H%M%S")