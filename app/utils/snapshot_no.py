"""
时间与快照批次号（kz_no）生成工具。
整合了原 time_utils 和 kz_generator 的功能，方法名保持不变，无需修改调用代码。
"""

import threading
from datetime import datetime
import pytz
from typing import Optional

# 上海时区常量
_SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")


def current_market_second_str(dt: Optional[datetime] = None) -> str:
    """
    获取当前市场时间字符串（上海时区），格式：YYYYMMDDHHMMSS

    - 若 dt 为 None：使用当前时间
    - 若 dt 无时区：视为 UTC 并转为上海时间
    - 若 dt 有时区：直接转为上海时间
    """
    if dt is None:
        sh_time = datetime.now(_SHANGHAI_TZ)
    else:
        if dt.tzinfo is None:
            # 无时区 → 视为 UTC
            dt = pytz.utc.localize(dt)
        sh_time = dt.astimezone(_SHANGHAI_TZ)

    return sh_time.strftime("%Y%m%d%H%M%S")


# ===== 以下为原 kz_generator.py 的逻辑，内嵌实现 =====

class _KZGenerator:
    """内部快照号生成器，线程安全"""
    _lock = threading.Lock()
    _last_second: Optional[str] = None
    _sequence: int = 0

    @classmethod
    def next_kz_no(cls, market_time: datetime) -> int:
        if market_time.tzinfo is None:
            raise ValueError("market_time 必须是带时区的 datetime（建议使用 Asia/Shanghai）")

        second_str = current_market_second_str(market_time)

        with cls._lock:
            if cls._last_second == second_str:
                cls._sequence += 1
            else:
                cls._last_second = second_str
                cls._sequence = 1

            return int(f"{second_str}{cls._sequence:03d}")


def next_kz_no(market_time: datetime) -> int:
    """
    生成下一个快照批次号（kz_no），格式：YYYYMMDDHHMMSS + 001～999

    示例：20260116195741001

    参数:
        market_time: 带时区信息的 datetime（必须！）
    """
    return _KZGenerator.next_kz_no(market_time)
