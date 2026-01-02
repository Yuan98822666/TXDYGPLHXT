"""
快照批次号生成器（KZGenerator）
"""

import threading
import datetime

class KZGenerator:
    _lock = threading.Lock()
    _last_second = None
    _sequence = 0

    @classmethod
    def next_kz_no(cls, market_time: datetime.datetime | None = None) -> int:
        """
        生成一个新的 kz_no

        kz_no = YYYYMMDDHHMMSS + 3 位序列号
        """
        if market_time is None:
            market_time = datetime.datetime.now()

        second_str = market_time.strftime("%Y%m%d%H%M%S")

        with cls._lock:
            if cls._last_second == second_str:
                cls._sequence += 1
            else:
                cls._last_second = second_str
                cls._sequence = 1

            seq_str = f"{cls._sequence:03d}"
            kz_no_str = f"{second_str}{seq_str}"

        return int(kz_no_str)
