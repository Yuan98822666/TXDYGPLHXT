# -*- coding: utf-8 -*-
"""验证交易时间过滤逻辑"""

def is_trading_time(time_str: str) -> bool:
    """检查是否是交易时间"""
    hour_min = time_str.split(':')
    hour = int(hour_min[0])
    minute = int(hour_min[1])
    total_minutes = hour * 60 + minute
    
    # 上午 9:30-11:30 (570-690分钟)，下午 13:00-15:00 (780-900分钟)
    is_morning = 570 <= total_minutes <= 690  # 9:30-11:30
    is_afternoon = 780 <= total_minutes <= 900  # 13:00-15:00
    
    return is_morning or is_afternoon

# 测试所有时间点
test_times = [
    "00:48", "09:30", "09:31", "09:32", "09:33", "09:34", "09:35",
    "09:36", "09:37", "09:38", "09:39", "09:40", "09:41", "09:42",
    "10:56", "10:57", "10:58", "10:59", "11:00", "11:01", "11:02",
    "11:03", "11:04", "11:05", "11:30", "11:31", "12:00", "12:59",
    "13:00", "13:01", "14:00", "15:00", "15:01", "19:06", "19:08"
]

print("Time filter verification:")
for t in test_times:
    result = is_trading_time(t)
    status = "KEEP" if result else "FILTER"
    print(f"  {t}: {status}")
