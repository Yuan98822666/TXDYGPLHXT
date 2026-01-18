from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import datetime


def extract_continuous_segments(
        df: pd.DataFrame,
        group_by: str,
        time_col: str,
        condition_col: str,
        min_duration: int = 1
) -> List[Dict[str, Any]]:
    """
    从时间序列数据中提取连续满足条件的时间段。

    核心逻辑：当 condition_col 为 False 时，断开连续段。

    Args:
        df: 输入 DataFrame，必须包含 group_by, time_col, condition_col 列
        group_by: 分组字段（如 'stock_code'）
        time_col: 时间字段（需已排序）
        condition_col: 布尔条件列（True 表示满足条件）
        min_duration: 最小持续长度（行数）

    Returns:
        List of segments, each with:
        - {group_by}_list: 所有分组值（应相同）
        - start_time, end_time
        - duration (行数)
        - 其他数值列的聚合（sum/avg/min/max）
    """
    if df.empty:
        return []

    # 确保按分组和时间排序
    df = df.sort_values([group_by, time_col]).reset_index(drop=True)

    # 标记断点：condition 为 False 的位置 +1
    df['break_flag'] = (~df[condition_col]).astype(int)  # ← 修复：使用 ～ 而不是 ～
    df['segment_id'] = df.groupby(group_by)['break_flag'].cumsum()

    # 过滤掉不满足 condition 的段（即 break_flag=1 的起始点）
    valid_segments = df[df[condition_col]]

    if valid_segments.empty:
        return []

    # 按 segment_id 聚合
    agg_dict = {
        time_col: ['min', 'max'],
        condition_col: 'size'
    }
    # 自动聚合其他数值列
    for col in df.columns:
        if col not in [group_by, time_col, condition_col, 'break_flag', 'segment_id']:
            if pd.api.types.is_numeric_dtype(df[col]):
                agg_dict[col] = ['sum', 'mean', 'min', 'max']

    grouped = valid_segments.groupby([group_by, 'segment_id']).agg(agg_dict).reset_index()

    # 展平列名
    grouped.columns = ['_'.join(col).strip('_') for col in grouped.columns]

    # 重命名关键列
    rename_map = {
        f'{time_col}_min': 'start_time',
        f'{time_col}_max': 'end_time',
        f'{condition_col}_size': 'duration'
    }
    grouped = grouped.rename(columns=rename_map)

    # 过滤最小持续时间
    result = grouped[grouped['duration'] >= min_duration].to_dict('records')

    return result


def find_longest_continuous_positive_segment(
        time_value_pairs: List[Tuple[str, float]]
) -> Optional[Dict[str, any]]:
    """
    【轻量型】从 (时间, 数值) 序列中找出“数值 > 0”的最长连续时间段。

    专为「资金持续性」「控盘持续性」等事件设计，特点：
    - 不依赖 pandas，纯 Python 实现，启动快、内存低
    - 输入为简单元组列表，易于从 SQLAlchemy 查询结果直接构造
    - 自动计算持续分钟数（基于时间差）

    Args:
        time_value_pairs: 形如 [("09:35", 120.5), ("09:36", 80.0), ...]
                          时间格式必须为 "HH:MM"，数值为 float/int

    Returns:
        None（无连续正向段） 或 字典：
        {
            "start_time": "09:35",
            "end_time": "10:20",
            "duration_minutes": 45,
            "total_value": 5000.0  # 正向期间总和（可选）
        }

    示例：
        >>> data = [("09:30", 100), ("09:31", 200), ("09:32", -50), ("09:33", 150)]
        >>> find_longest_continuous_positive_segment(data)
        {'start_time': '09:30', 'end_time': '09:31', 'duration_minutes': 1, 'total_value': 300}
    """
    if not time_value_pairs:
        return None

    # 按时间排序（防御性编程）
    sorted_pairs = sorted(time_value_pairs, key=lambda x: x[0])

    longest_segment = None
    current_start = None
    current_sum = 0.0

    for i, (time_str, value) in enumerate(sorted_pairs):
        is_positive = value > 0

        if is_positive:
            # 开启或延续一个正向段
            if current_start is None:
                current_start = time_str
                current_sum = value
            else:
                current_sum += value
        else:
            # 遇到非正向值，结束当前段
            if current_start is not None:
                # 计算当前段的结束时间和持续分钟
                current_end = sorted_pairs[i - 1][0]  # 上一个时间点
                duration = _calculate_duration_minutes(current_start, current_end)

                candidate = {
                    "start_time": current_start,
                    "end_time": current_end,
                    "duration_minutes": duration,
                    "total_value": current_sum
                }

                # 更新最长段
                if longest_segment is None or duration > longest_segment["duration_minutes"]:
                    longest_segment = candidate

                # 重置
                current_start = None
                current_sum = 0.0

    # 处理最后一段（如果以正向结束）
    if current_start is not None:
        current_end = sorted_pairs[-1][0]
        duration = _calculate_duration_minutes(current_start, current_end)
        candidate = {
            "start_time": current_start,
            "end_time": current_end,
            "duration_minutes": duration,
            "total_value": current_sum
        }
        if longest_segment is None or duration > longest_segment["duration_minutes"]:
            longest_segment = candidate

    return longest_segment


def _calculate_duration_minutes(start_time: str, end_time: str) -> int:
    """
    计算两个 "HH:MM" 时间字符串之间的分钟差（取整）

    Args:
        start_time: 起始时间，如 "09:30"
        end_time: 结束时间，如 "10:15"

    Returns:
        分钟数（int），最小为 0
    """
    try:
        fmt = "%H:%M"
        start_dt = datetime.datetime.strptime(start_time, fmt)
        end_dt = datetime.datetime.strptime(end_time, fmt)
        diff_seconds = (end_dt - start_dt).total_seconds()
        return max(0, int(diff_seconds // 60))
    except Exception:
        # 防御性处理：解析失败则返回 0
        return 0
