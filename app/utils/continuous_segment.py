from typing import List, Dict, Any
import pandas as pd


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