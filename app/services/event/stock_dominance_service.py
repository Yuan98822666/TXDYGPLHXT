"""
控盘程度事件服务

📌 文件说明：
本服务判断主力是否对个股形成有效控制。
- 输入：raw_stock_huoyue 分钟级资金与价格数据
- 输出：event_stock_dominance 事件表记录
- 核心逻辑：主力控盘度高 + 散户抛压低 + 波动小 + 大单压制反向单

🎯 使用场景：
- 盘中（is_final=False）：观察控盘迹象
- 收盘（is_final=True）：判断次日是否具备溢价承接能力

✅ 修复说明（2026-01-17）：
1. 修正字段名：使用存在的字段（stock_zl_inflow, stock_xd_inflow, stock_cjey）
2. 重新定义控盘指标计算逻辑
3. 保留 generated_at（模型已添加）
"""

from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
from sqlalchemy.orm import Session

from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from app.models.event.event_stock_dominance import EventStockDominance
from app.utils.continuous_segment import extract_continuous_segments


class StockDominanceService:
    @staticmethod
    def run_for_date(db: Session, trade_date: date, is_final: bool = False) -> List[EventStockDominance]:
        """
        为指定交易日生成控盘程度事件。

        ▶ 触发标准（硬性规则）：
        - 主力控盘度 ≥ 60%（主力净流入 / 成交额）
        - 散户抛压 ≤ 20%（小单净流出占成交额比例）
        - 波动率 ≤ 0.5%（5分钟滚动波动率）
        - 主力净流入累计 ≥ 500 万（体现压制力）

        ▶ 参数说明：
        db (Session): SQLAlchemy 数据库会话
        trade_date (date): 目标交易日
        is_final (bool): 是否为收盘冻结事件（默认 False）

        ▶ 返回：
        List[EventStockDominance]: 符合条件的控盘事件列表（已持久化）
        """
        # Step 1: 获取当日股票分钟数据（使用存在的字段！）
        raw_data = db.query(
            RawStockHuoyue.stock_code,
            RawStockHuoyue.stock_name,
            RawStockHuoyue.market_time,
            RawStockHuoyue.stock_zl_inflow,   # ✅ 主力净流入（元）
            RawStockHuoyue.stock_xd_inflow,   # ✅ 小单净流入（元）→ 负值=卖出
            RawStockHuoyue.stock_cjey,        # ✅ 成交额（总买卖，元）
            RawStockHuoyue.stock_zxj          # ✅ 最新价
        ).filter(
            RawStockHuoyue.market_time >= datetime.combine(trade_date, datetime.min.time()),
            RawStockHuoyue.market_time < datetime.combine(trade_date + timedelta(days=1), datetime.min.time())
        ).all()

        if not raw_data:
            return []

        df = pd.DataFrame([
            {
                'stock_code': r.stock_code,
                'stock_name': r.stock_name,
                'market_time': r.market_time,
                'stock_zl_inflow': r.stock_zl_inflow or 0,
                'stock_xd_inflow': r.stock_xd_inflow or 0,
                'stock_cjey': r.stock_cjey or 1,  # 避免除零
                'stock_zxj': r.stock_zxj or 0.0,
            }
            for r in raw_data
        ])

        if df.empty:
            return []

        # Step 2: 计算核心指标（使用正确字段！）
        # 主力控盘度 = 主力净流入 / 成交额（反映主力主导程度）
        df['zl_control_ratio'] = (df['stock_zl_inflow'] / df['stock_cjey'].clip(lower=1)).clip(0, 1)

        # 散户抛压 = 小单净流出 / 成交额（小单 inflow 为负 → 卖出）
        df['retail_resistance_ratio'] = ((-df['stock_xd_inflow']).clip(lower=0) / df['stock_cjey'].clip(lower=1)).clip(0, 1)

        # 买卖不平衡 = 主力净流入 - 小单净流入（正值表示主力压制散户）
        df['bid_ask_imbalance'] = df['stock_zl_inflow'] - df['stock_xd_inflow']

        # 计算滚动波动率（5分钟窗口）
        df = df.sort_values(['stock_code', 'market_time'])
        df['price_volatility'] = df.groupby('stock_code')['stock_zxj'].rolling(
            window=5, min_periods=1
        ).apply(lambda x: x.std() / x.mean() if x.mean() > 0 else 0, raw=True).reset_index(level=0, drop=True)

        # Step 3: 标记满足控盘条件的分钟
        df['is_dominant'] = (
            (df['zl_control_ratio'] >= 0.6) &
            (df['retail_resistance_ratio'] <= 0.2) &
            (df['price_volatility'] <= 0.005) &
            (df['stock_zl_inflow'] >= 5_000_000)  # 主力单分钟流入 ≥ 500万
        )

        # Step 4: 提取连续控盘段（至少20分钟）
        segments = extract_continuous_segments(
            df=df,
            group_by='stock_code',
            time_col='market_time',
            condition_col='is_dominant',
            min_duration=20
        )

        # Step 5: 构造事件对象
        events = []
        generated_at = datetime.now()

        for seg in segments:
            try:
                stock_code = seg['stock_code']
                stock_sample = df[df['stock_code'] == stock_code].iloc[0]
                stock_name = stock_sample['stock_name']

                reason = (
                    f"{stock_name} 控盘："
                    f"主力控盘 {seg['zl_control_ratio_mean']:.0%}，"
                    f"散户抛压 {seg['retail_resistance_ratio_mean']:.0%}，"
                    f"波动率 {seg['price_volatility_mean']*100:.2f}%，"
                    f"主力压制 {round(seg['bid_ask_imbalance_sum']/1e6, 1)} 万元，"
                    f"持续 {seg['duration']} 分钟"
                )

                event = EventStockDominance(
                    trade_date=trade_date,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    start_time=seg['start_time'],
                    end_time=seg['end_time'],
                    duration_minutes=seg['duration'],
                    zl_control_ratio=seg['zl_control_ratio_mean'],
                    retail_resistance_ratio=seg['retail_resistance_ratio_mean'],
                    price_volatility=seg['price_volatility_mean'],
                    bid_ask_imbalance=seg['bid_ask_imbalance_sum'],
                    reason=reason,
                    is_final=is_final,
                    generated_at=generated_at  # ✅ 现在模型有此字段
                )
                events.append(event)

            except (KeyError, IndexError) as e:
                print(f"警告：处理控盘 segment 时出错，跳过。错误: {e}, seg: {seg}")
                continue

        # Step 6: 幂等写入
        db.query(EventStockDominance).filter(
            EventStockDominance.trade_date == trade_date
        ).delete()
        db.add_all(events)
        db.commit()
        return events