"""
资本持续性事件服务（CapitalPersistenceService）

功能：
- 识别个股主力资金连续净流入的行为
- 支持两种模式：
    1. 盘中增量生成（is_final=False）→ 可多次调用，用于实时监控
    2. 盘尾冻结生成（is_final=True）→ 每日一次，用于最终决策

关键设计：
- 同一股票在同一交易日，可存在两个事件：
    • 一个 is_final=False（盘中最新状态）
    • 一个 is_final=True（盘尾最终状态）
- 删除旧事件时，只删除同类型（同 is_final 值）的记录，确保互不干扰
- 幂等性：同一时间段内，相同事件不会重复插入（由数据库唯一索引保证）

作者：基于系统 v1.0 设计规范重构
"""

from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.event.event_capital_persistence import EventCapitalPersistence
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from app.utils.continuous_segment import find_longest_continuous_positive_segment


class CapitalPersistenceService:
    """
    资金持续性事件生成器

    判定逻辑：
    - 主力净流入 > 0
    - 连续 N 分钟未中断（N >= 30 才生成事件）
    - 盘尾阶段会检查尾盘30分钟是否撤退（若撤退则不生成最终事件）
    """

    @staticmethod
    def generate_events_for_date(
        db: Session,
        trade_date: date,
        is_final: bool = False,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None
    ) -> List[EventCapitalPersistence]:
        """
        为指定交易日生成资本持续性事件

        参数：
        :param db: 数据库会话
        :param trade_date: 交易日期
        :param is_final: 是否为盘尾冻结事件（True=最终态，False=盘中临时）
        :param from_time: （仅盘中使用）开始时间，格式 "HH:MM"
        :param to_time:   （仅盘中使用）结束时间，格式 "HH:MM"

        返回：
        :return: 新生成的事件列表
        """
        # === 第一步：清理同类型旧事件 ===
        # 关键改动：只删除相同 is_final 值的记录
        # 例如：当 is_final=False 时，只删掉之前的临时事件，保留最终事件
        delete_condition = and_(
            EventCapitalPersistence.trade_date == trade_date,
            EventCapitalPersistence.is_final == is_final  # 👈 核心！按类型隔离
        )
        deleted_count = db.query(EventCapitalPersistence).filter(delete_condition).delete()
        print(f"🧹 清理 {trade_date} 的 {'最终' if is_final else '临时'}资本持续事件，共 {deleted_count} 条")

        # === 第二步：确定查询时间范围 ===
        if is_final:
            # 盘尾冻结：使用全天数据（9:30-15:00）
            start_time_str = "09:30"
            end_time_str = "15:00"
        else:
            # 盘中增量：使用传入的时间窗口
            if not from_time or not to_time:
                raise ValueError("盘中增量模式必须提供 from_time 和 to_time")
            start_time_str = from_time
            end_time_str = to_time

        # === 第三步：从原始数据中提取资金流序列 ===
        raw_records = db.query(RawStockHuoyue).filter(
            RawStockHuoyue.trade_date == trade_date,
            RawStockHuoyue.time >= start_time_str,
            RawStockHuoyue.time <= end_time_str,
            RawStockHuoyue.zl_net_inflow.isnot(None)
        ).order_by(RawStockHuoyue.time).all()

        if not raw_records:
            print(f"⚠️  {trade_date} {start_time_str}-{end_time_str} 无原始资金数据")
            return []

        # 按股票分组
        stock_groups = {}
        for record in raw_records:
            stock_groups.setdefault(record.stock_code, []).append(record)

        new_events = []

        # === 第四步：对每只股票计算最长连续正向资金流 ===
        for stock_code, records in stock_groups.items():
            # 提取 (time, zl_net_inflow) 序列
            time_series = [(r.time, r.zl_net_inflow) for r in records]

            # 使用工具函数找出最长连续 >0 的时间段
            segment = find_longest_continuous_positive_segment(time_series)

            if not segment:
                continue

            duration_minutes = segment["duration_minutes"]
            start_time = segment["start_time"]
            end_time = segment["end_time"]

            # === 第五步：应用业务规则 ===
            # 规则1：只有持续 >=30 分钟才生成事件（盘中）
            # 规则2：如果是盘尾最终事件，还需检查尾盘30分钟是否撤退
            should_generate = False
            reason = ""

            if is_final:
                # 盘尾模式：检查尾盘30分钟（14:30-15:00）是否有资金撤退
                tail_withdrawn = CapitalPersistenceService._is_tail_capital_withdrawn(
                    db, stock_code, trade_date
                )
                if duration_minutes >= 30 and not tail_withdrawn:
                    should_generate = True
                    reason = f"资金持续{duration_minutes}分钟，尾盘未撤退"
                else:
                    reason = f"持续{duration_minutes}分钟，但尾盘撤退={tail_withdrawn}"
            else:
                # 盘中模式：只要 >=30 分钟就生成
                if duration_minutes >= 30:
                    should_generate = True
                    reason = f"盘中资金持续{duration_minutes}分钟"

            if should_generate:
                event = EventCapitalPersistence(
                    trade_date=trade_date,
                    stock_code=stock_code,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration_minutes,
                    is_final=is_final,  # 👈 明确标记类型
                    generated_at=datetime.now(),
                    remarks=reason
                )
                db.add(event)
                new_events.append(event)
                print(f"✅ 生成{'最终' if is_final else '临时'}事件: {stock_code}, 持续{duration_minutes}分钟")

        db.commit()
        print(f"📈 共生成 {len(new_events)} 条资本持续事件（{'最终' if is_final else '临时'}）")
        return new_events

    @staticmethod
    def _is_tail_capital_withdrawn(db: Session, stock_code: str, trade_date: date) -> bool:
        """
        检查尾盘30分钟（14:30-15:00）是否出现主力净流入 <= 0

        返回 True 表示有撤退，应否决最终事件
        """
        tail_records = db.query(RawStockHuoyue).filter(
            RawStockHuoyue.trade_date == trade_date,
            RawStockHuoyue.stock_code == stock_code,
            RawStockHuoyue.time >= "14:30",
            RawStockHuoyue.time <= "15:00",
            RawStockHuoyue.zl_net_inflow <= 0
        ).first()

        return tail_records is not None