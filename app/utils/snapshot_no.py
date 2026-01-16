"""
时间与快照批次号（kz_no）生成工具。
整合了原 time_utils 和 kz_generator 的功能，方法名保持不变，无需修改调用代码。

核心功能：
1. 获取上海时区的当前市场时间字符串（精确到秒）
2. 生成全局唯一、线程安全的快照批次号（kz_no），格式为：YYYYMMDDHHMMSS + 001～999

设计要点：
- 所有时间处理均基于上海时区（Asia/Shanghai）
- 快照号在同1秒内自动递增序列号，跨秒重置
- 使用类级别的锁保证多线程环境下序列号不重复
"""

import threading
from datetime import datetime
import pytz
from typing import Optional

# 上海时区常量，避免重复创建时区对象
_SHANGHAI_TZ = pytz.timezone("Asia/Shanghai")


def current_market_second_str(dt: Optional[datetime] = None) -> str:
    """
    获取当前市场时间字符串（上海时区），格式：YYYYMMDDHHMMSS

    参数:
        dt (Optional[datetime]):
            - 若为 None：使用当前系统时间
            - 若无时区信息：视为 UTC 时间并转换为上海时间
            - 若有时区信息：直接转换为上海时间

    返回:
        str: 格式化的14位时间字符串，例如 "20260116195741"

    逻辑说明:
        1. 无输入时间 → 获取当前上海时间
        2. 输入时间无时区 → 假定为UTC，本地化后再转上海时区
        3. 输入时间有时区 → 直接转换为目标时区
    """
    if dt is None:
        # 使用当前上海时间
        sh_time = datetime.now(_SHANGHAI_TZ)
    else:
        if dt.tzinfo is None:
            # 无时区信息的 datetime 被视为 UTC
            dt = pytz.utc.localize(dt)
        # 转换为上海时区
        sh_time = dt.astimezone(_SHANGHAI_TZ)
    return sh_time.strftime("%Y%m%d%H%M%S")


# ===== 以下为原 kz_generator.py 的逻辑，内嵌实现 =====

class _KZGenerator:
    """
    内部快照号生成器，线程安全

    设计原理：
    - 使用类变量存储上一次生成的时间戳和序列号
    - 通过 threading.Lock() 保证并发安全
    - 同一秒内调用 next_kz_no() 会递增序列号（001→002...999）
    - 跨秒调用会重置序列号为001

    注意：这是一个内部类，外部应通过 next_kz_no() 函数调用
    """
    _lock = threading.Lock()           # 线程锁，保护共享状态
    _last_second: Optional[str] = None # 记录上一次生成快照的时间戳（秒级）
    _sequence: int = 0                 # 当前秒内的序列号（1-999）

    @classmethod
    def next_kz_no(cls, market_time: datetime) -> int:
        """
        生成下一个快照批次号（内部实现）

        参数:
            market_time (datetime): 带时区信息的市场时间（必须！）

        返回:
            int: 17位快照号，格式 YYYYMMDDHHMMSSxxx（xxx为001-999）

        异常:
            ValueError: 当 market_time 无时区信息时抛出

        逻辑流程:
            1. 验证输入时间必须带时区
            2. 获取当前秒级时间字符串（上海时区）
            3. 加锁保护临界区
            4. 比较当前秒与上次记录的秒：
               - 相同 → 序列号+1
               - 不同 → 重置序列号为1，更新时间戳
            5. 拼接时间字符串和3位序列号，转为整数返回
        """
        if market_time.tzinfo is None:
            raise ValueError("market_time 必须是带时区的 datetime（建议使用 Asia/Shanghai）")

        second_str = current_market_second_str(market_time)

        with cls._lock:
            if cls._last_second == second_str:
                # 同一秒内，序列号递增
                cls._sequence += 1
            else:
                # 新的一秒，重置序列号
                cls._last_second = second_str
                cls._sequence = 1

        # 格式：时间字符串(14位) + 序列号(3位，左补零)
        return int(f"{second_str}{cls._sequence:03d}")


def next_kz_no(market_time: datetime) -> int:
    """
    生成下一个快照批次号（kz_no），格式：YYYYMMDDHHMMSS + 001～999

    示例：20260116195741001

    参数:
        market_time: 带时区信息的 datetime（必须！建议使用 Asia/Shanghai 时区）

    返回:
        int: 17位唯一快照批次号

    使用说明:
        此函数是 _KZGenerator.next_kz_no() 的公共接口，
        保持原有调用方式不变，便于代码迁移
    """
    return _KZGenerator.next_kz_no(market_time)