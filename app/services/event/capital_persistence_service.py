"""
资本持续性事件服务

📌 文件说明：
本服务识别“真金白银持续流入”的股票。
- 输入：raw_stock_huoyue 分钟级个股资金流
- 输出：event_capital_persistence 事件表记录
- 核心逻辑：连续60分钟以上主力净流入，且满足强度与稳定性阈值

🎯 使用场景：
- 盘中（is_final=False）：观察资金动向
- 收盘（is_final=True）：作为决策生死门槛

✅ 修复说明（2026-01-17）：
- 修正 seg 字段访问错误：原代码误用 'stock_code_list'，实际应为 'stock_code'
- 从原始 df 获取 stock_name（因非数值列未被聚合）
- 添加防御性检查，避免 KeyError
"""

from datetime import date, datetime
from typing import List
import pandas as pd
from sqlalchemy.orm import Session

from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from app.models.event.event_capital_persistence import EventCapitalPersistence
from app.utils.continuous_segment import extract_continuous_segments


class CapitalPersistenceService:
    @staticmethod
    def run_for_date(db: Session, trade_date: date, is_final: bool = False) -> List[EventCapitalPersistence]:
        """
        为指定交易日生成资本持续性事件。

        ▶ 触发标准（第一版写死）：
        - 持续时间 ≥ 60 分钟
        - 正流入分钟占比 ≥ 70%
        - 主力净流入累计 ≥ 300 万
        - 区间价格回撤 ≤ 1%（即涨幅 ≥ -1%）

        ▶ 参数说明：
        db (Session): SQLAlchemy 数据库会话
        trade_date (date): 目标交易日
        is_final (bool): 是否为收盘冻结事件（默认 False）

        ▶ 返回：
        List[EventCapitalPersistence]: 符合条件的持续性事件列表（已持久化）
        """
        # Step 1: 获取当日原始分钟数据
        raw_data = db.query(
            RawStockHuoyue.stock_code,
            RawStockHuoyue.stock_name,
            RawStockHuoyue.market_time,
            RawStockHuoyue.stock_zl_inflow,
            RawStockHuoyue.stock_zl_zb,
            RawStockHuoyue.stock_zxj
        ).filter(
            RawStockHuoyue.market_time >= trade_date,
            RawStockHuoyue.market_time < trade_date.replace(day=trade_date.day + 1)
        ).all()

        if not raw_data:
            return []

        # 转为 DataFrame，并处理空值
        df = pd.DataFrame([
            {
                'stock_code': r.stock_code,
                'stock_name': r.stock_name,
                'market_time': r.market_time,
                'stock_zl_inflow': r.stock_zl_inflow or 0,
                'stock_zl_zb': r.stock_zl_zb or 0.0,
                'stock_zxj': r.stock_zxj or 0.0,
            }
            for r in raw_data
        ])

        if df.empty:
            return []

        # Step 2: 标记正流入分钟（主力未流出）
        df['is_positive'] = df['stock_zl_inflow'] > 0

        # Step 3: 提取连续“主力未流出”时间段（核心！）
        # 注意：group_by='stock_code'，所以每个 segment 只属于一只股票
        segments = extract_continuous_segments(
            df=df,
            group_by='stock_code',
            time_col='market_time',
            condition_col='is_positive',
            min_duration=60  # ≥60分钟
        )

        # Step 4: 遍历每个连续段，计算指标并过滤
        events = []
        generated_at = datetime.now()

        for seg in segments:
            try:
                # ✅ 修复点 1: 直接使用 'stock_code'（不再是 'stock_code_list'）
                stock_code = seg['stock_code']

                # ✅ 修复点 2: 从原始 df 获取 stock_name（因非数值列未被聚合）
                # 取该股票任意一行即可（名称不变）
                stock_sample = df[df['stock_code'] == stock_code].iloc[0]
                stock_name = stock_sample['stock_name']

                duration = seg['duration']
                zl_sum = seg.get('stock_zl_inflow_sum', 0)

                # 重新计算正流入占比（更准确）
                mask = (
                    (df['stock_code'] == stock_code) &
                    (df['market_time'] >= seg['start_time']) &
                    (df['market_time'] <= seg['end_time'])
                )
                pos_ratio = df.loc[mask, 'is_positive'].mean() if not df.loc[mask].empty else 0.0

                min_price = seg.get('stock_zxj_min', 0)
                max_price = seg.get('stock_zxj_max', 0)
                price_change = (max_price / min_price - 1) if min_price > 0 else 0
                avg_zl_zb = seg.get('stock_zl_zb_mean', 0)

                # 应用阈值过滤
                if pos_ratio >= 0.7 and zl_sum >= 3_000_000 and price_change >= -0.01:
                    reason = (
                        f"连续{duration}分钟主力净流入，累计 "
                        f"{round(zl_sum / 10000, 1)} 万元，"
                        f"正流入占比 {round(pos_ratio * 100, 1)}%"
                    )
                    event = EventCapitalPersistence(
                        trade_date=trade_date,
                        stock_code=stock_code,
                        stock_name=stock_name,
                        start_time=seg['start_time'],
                        end_time=seg['end_time'],
                        duration_minutes=duration,
                        zl_inflow_sum=zl_sum,
                        positive_minute_ratio=pos_ratio,
                        price_change_pct=price_change,
                        avg_zl_zb=avg_zl_zb,
                        reason=reason,
                        is_final=is_final,
                        generated_at=generated_at
                    )
                    events.append(event)

            except (KeyError, IndexError) as e:
                # 防御性处理：跳过异常 segment
                print(f"警告：处理 segment 时出错，跳过。错误: {e}, seg 内容: {seg}")
                continue

        # Step 5: 幂等写入
        db.query(EventCapitalPersistence).filter(
            EventCapitalPersistence.trade_date == trade_date
        ).delete()
        db.add_all(events)
        db.commit()
        return events