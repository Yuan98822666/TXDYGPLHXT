"""
文件名：kz_generator.py
作用说明：
    快照批次号生成器（KZGenerator）
"""

import threading
from datetime import datetime

from app.utils.time_utils import current_market_second_str


class KZGenerator:
    """
    kz_no 结构：
        YYYYMMDDHHMMSS + 3 位序列号
    示例：
        20260103103015001
    """

    _lock = threading.Lock()
    _last_second: str | None = None
    _sequence: int = 0

    @classmethod
    def next_kz_no(cls, market_time: datetime) -> int:
        """
        生成新的 kz_no

        参数：
            market_time: timezone-aware 的中国市场时间
        """

        if market_time.tzinfo is None:
            raise ValueError("market_time 必须是 timezone-aware（Asia/Shanghai）")

        second_str = current_market_second_str(market_time)

        with cls._lock:
            if cls._last_second == second_str:
                cls._sequence += 1
            else:
                cls._last_second = second_str
                cls._sequence = 1

            kz_no_str = f"{second_str}{cls._sequence:03d}"

        return int(kz_no_str)

    # === 明确禁止使用的接口 ===
    @classmethod
    def next(cls):
        raise RuntimeError(
            "禁止调用 KZGenerator.next()，请使用 next_kz_no(market_time)，并由 Dispatcher 统一传入时间"
        )


# ------------------------
# 模块级别的封装函数，方便直接导入
def next_kz_no(market_time: datetime) -> int:
    return KZGenerator.next_kz_no(market_time)
