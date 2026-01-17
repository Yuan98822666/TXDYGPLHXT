"""
群体共识事件服务

📌 文件说明：
本服务识别“被多个板块反复点名”的核心个股。
- 输入：raw_block_huoyue 中 MONEY / LIDER 字段
- 输出：event_stock_consensus 事件表记录
- 核心逻辑：UNION ALL 资金代表 + 领涨代表，聚合统计

🎯 使用场景：
- 盘中（is_final=False）：观察市场焦点
- 收盘（is_final=True）：判断次日是否有接力共识
"""

from datetime import date, datetime
from typing import List
from sqlalchemy.orm import Session

from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from app.models.event.event_stock_consensus import EventStockConsensus


class StockConsensusService:

    @staticmethod
    def run_for_date(
        db: Session,
        trade_date: date,
        is_final: bool = False
    ) -> List[EventStockConsensus]:
        """
        为指定交易日生成群体共识事件。

        ▶ 触发标准（第一版写死）：
            - 被点名板块数（去重） ≥ 3
            - 点名总次数 ≥ 5
            - 持续时间 ≥ 30 分钟

        ▶ 参数说明：
            db (Session): SQLAlchemy 数据库会话
            trade_date (date): 目标交易日（如 2026-01-15）
            is_final (bool): 是否为收盘冻结事件（默认 False）

        ▶ 返回：
            List[EventStockConsensus]: 符合条件的共识事件列表（已持久化）
        """
        # Step 1: 摊平点名行为（MONEY + LIDER）
        mentions = []

        # 提取所有作为“资金代表”被点名的记录
        money_mentions = db.query(
            RawBlockHuoyue.market_time,
            RawBlockHuoyue.money_stock_code.label('stock_code'),
            RawBlockHuoyue.money_stock_name.label('stock_name'),
            RawBlockHuoyue.block_code,
            RawBlockHuoyue.block_name
        ).filter(
            RawBlockHuoyue.market_time >= trade_date,
            RawBlockHuoyue.market_time < trade_date.replace(day=trade_date.day + 1),
            RawBlockHuoyue.money_stock_code.isnot(None)
        ).all()

        for m in money_mentions:
            mentions.append({
                'market_time': m.market_time,
                'stock_code': m.stock_code,
                'stock_name': m.stock_name,
                'block_code': m.block_code,
                'mention_type': 'MONEY'
            })

        # 提取所有作为“领涨代表”被点名的记录
        lider_mentions = db.query(
            RawBlockHuoyue.market_time,
            RawBlockHuoyue.lider_stock_code.label('stock_code'),
            RawBlockHuoyue.lider_stock_name.label('stock_name'),
            RawBlockHuoyue.block_code,
            RawBlockHuoyue.block_name
        ).filter(
            RawBlockHuoyue.market_time >= trade_date,
            RawBlockHuoyue.market_time < trade_date.replace(day=trade_date.day + 1),
            RawBlockHuoyue.lider_stock_code.isnot(None)
        ).all()

        for l in lider_mentions:
            mentions.append({
                'market_time': l.market_time,
                'stock_code': l.stock_code,
                'stock_name': l.stock_name,
                'block_code': l.block_code,
                'mention_type': 'LIDER'
            })

        if not mentions:
            return []

        # Step 2: 转为 DataFrame 聚合
        import pandas as pd
        df = pd.DataFrame(mentions)

        agg = df.groupby(['stock_code']).agg(
            stock_name=('stock_name', 'first'),
            mentioned_times=('stock_code', 'size'),
            mentioned_block_count=('block_code', 'nunique'),
            money_block_count=('mention_type', lambda x: (x == 'MONEY').sum()),
            lider_block_count=('mention_type', lambda x: (x == 'LIDER').sum()),
            first_mentioned_time=('market_time', 'min'),
            last_mentioned_time=('market_time', 'max')
        ).reset_index()

        # 计算持续时间（分钟）
        agg['duration_minutes'] = (
            (agg['last_mentioned_time'] - agg['first_mentioned_time']).dt.total_seconds() / 60
        ).astype(int)

        # Step 3: 应用触发阈值过滤
        filtered = agg[
            (agg['mentioned_block_count'] >= 3) &
            (agg['mentioned_times'] >= 5) &
            (agg['duration_minutes'] >= 30)
        ]

        # Step 4: 构造事件对象
        events = []
        generated_at = datetime.now()
        for _, row in filtered.iterrows():
            # 共识强度评分（内部使用，非决策分）
            strength = (
                row['mentioned_block_count'] * 10 +
                row['mentioned_times'] * 2 +
                row['money_block_count'] * 5 +
                row['lider_block_count'] * 5
            )

            reason = (
                f"被 {row['mentioned_block_count']} 个板块点名，共 "
                f"{row['mentioned_times']} 次（资金 "
                f"{row['money_block_count']}，领涨 "
                f"{row['lider_block_count']}），持续 "
                f"{row['duration_minutes']} 分钟"
            )

            event = EventStockConsensus(
                trade_date=trade_date,
                stock_code=row['stock_code'],
                stock_name=row['stock_name'],
                mentioned_block_count=row['mentioned_block_count'],
                mentioned_times=row['mentioned_times'],
                money_block_count=row['money_block_count'],
                lider_block_count=row['lider_block_count'],
                first_mentioned_time=row['first_mentioned_time'],
                last_mentioned_time=row['last_mentioned_time'],
                duration_minutes=row['duration_minutes'],
                consensus_strength=strength,
                reason=reason,
                # --- 新增字段 ---
                is_final=is_final,
                generated_at=generated_at
            )
            events.append(event)

        # Step 5: 幂等写入（先删后插）
        db.query(EventStockConsensus).filter(
            EventStockConsensus.trade_date == trade_date
        ).delete()
        db.add_all(events)
        db.commit()

        return events