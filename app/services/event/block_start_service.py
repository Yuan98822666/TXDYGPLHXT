"""
板块启动事件服务

📌 文件说明：
本服务负责识别市场中“主线板块”的启动信号。
- 输入：raw_block_huoyue 分钟级板块行情
- 输出：event_block_start 事件表记录
- 核心逻辑：连续满足「上涨股比≥70% + 平均涨幅≥2% + 量比≥1.5」达15分钟以上

🎯 使用场景：
- 盘中（is_final=False）：每5/10分钟运行，用于观察
- 收盘（is_final=True）：15:10运行，用于决策

✅ 修复说明（2026-01-17）：
- 修正 seg 字段访问错误：原代码误用 'block_code_list'，实际应为 'block_code'
- 从原始 df 获取 block_name
- 添加异常处理
"""

from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
from sqlalchemy.orm import Session

from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from app.models.event.event_block_start import EventBlockStart
from app.utils.continuous_segment import extract_continuous_segments


class BlockStartService:
    @staticmethod
    def run_for_date(db: Session, trade_date: date, is_final: bool = False) -> List[EventBlockStart]:
        """
        为指定交易日生成板块启动事件。

        ▶ 触发标准（硬性规则）：
        - 上涨个股占比 ≥ 70%
        - 板块平均涨幅 ≥ 2%
        - 板块量比 ≥ 1.5
        - 连续持续时间 ≥ 15 分钟

        ▶ 参数说明：
        db (Session): SQLAlchemy 数据库会话
        trade_date (date): 目标交易日（如 2026-01-15）
        is_final (bool): 是否为收盘冻结事件（默认 False）

        ▶ 返回：
        List[EventBlockStart]: 符合条件的板块启动事件列表（已持久化）

        ▶ 幂等策略：
        每次运行前删除当日同类型事件，确保最新覆盖
        """
        # Step 1: 查询当日原始板块分钟数据
        raw_data = db.query(
            RawBlockHuoyue.block_code,
            RawBlockHuoyue.block_name,
            RawBlockHuoyue.market_time,
            RawBlockHuoyue.up_count,      # 上涨家数
            RawBlockHuoyue.stock_count,   # 总股票数
            RawBlockHuoyue.block_zdf,     # 板块涨跌幅（%）
            RawBlockHuoyue.block_lb       # 量比
        ).filter(
            RawBlockHuoyue.market_time >= datetime.combine(trade_date, datetime.min.time()),
            RawBlockHuoyue.market_time < datetime.combine(trade_date + timedelta(days=1), datetime.min.time())
        ).all()

        # 若无数据，直接返回空列表
        if not raw_data:
            return []

        # Step 2: 转换为 DataFrame 并处理空值
        df = pd.DataFrame([
            {
                'block_code': r.block_code,
                'block_name': r.block_name,
                'market_time': r.market_time,
                'block_up_count': r.up_count or 0,
                'block_total_count': r.stock_count or 1,  # 避免除零
                'block_avg_change': r.block_zdf or 0.0,   # block_zdf = average change %
                'block_volume_ratio': r.block_lb or 0.0,  # block_lb = volume ratio
            }
            for r in raw_data
        ])

        if df.empty:
            return []

        # Step 3: 计算上涨比例并标记启动分钟
        df['up_ratio'] = df['block_up_count'] / df['block_total_count'].clip(lower=1)
        df['is_start'] = (
            (df['up_ratio'] >= 0.7) &
            (df['block_avg_change'] >= 2.0) &
            (df['block_volume_ratio'] >= 1.5)
        )

        # Step 4: 提取连续启动时间段（至少15分钟）
        segments = extract_continuous_segments(
            df=df,
            group_by='block_code',
            time_col='market_time',
            condition_col='is_start',
            min_duration=15
        )

        # Step 5: 构造事件对象
        events = []
        generated_at = datetime.now()

        for seg in segments:
            try:
                # ✅ 修复点：直接使用 'block_code'
                block_code = seg['block_code']

                # 从原始 df 获取 block_name
                block_sample = df[df['block_code'] == block_code].iloc[0]
                block_name = block_sample['block_name']

                # 生成人类可读原因
                reason = (
                    f"板块 {block_name} 启动："
                    f"上涨 {seg['block_up_count_mean']:.0f}/{seg['block_total_count_mean']:.0f} 股，"
                    f"平均涨 {seg['block_avg_change_mean']:.1f}%，"
                    f"量比 {seg['block_volume_ratio_mean']:.1f}，"
                    f"持续 {seg['duration']} 分钟"
                )

                event = EventBlockStart(
                    trade_date=trade_date,
                    block_code=block_code,
                    block_name=block_name,
                    start_time=seg['start_time'],
                    end_time=seg['end_time'],
                    duration_minutes=seg['duration'],
                    block_up_count=int(seg['block_up_count_mean']),
                    block_total_count=int(seg['block_total_count_mean']),
                    up_ratio=seg['up_ratio_mean'],
                    avg_change_pct=seg['block_avg_change_mean'],
                    volume_ratio=seg['block_volume_ratio_mean'],
                    reason=reason,
                    is_final=is_final,
                    generated_at=generated_at
                )
                events.append(event)

            except (KeyError, IndexError) as e:
                print(f"警告：处理板块 segment 时出错，跳过。错误: {e}, seg: {seg}")
                continue

        # Step 6: 幂等写入（先删后插）
        db.query(EventBlockStart).filter(
            EventBlockStart.trade_date == trade_date,
            EventBlockStart.is_final == is_final
        ).delete()
        db.add_all(events)
        db.commit()
        return events