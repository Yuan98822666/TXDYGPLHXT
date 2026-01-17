"""
资本持续性事件模型一句话定义：
EventCapitalPersistence = 一只股票在盘中被主力资金“持续盯住”，而不是瞬时冲动。
它回答的不是：会不会涨停 ❌
而是：值不值得第二天继续观察 / 准备接力 ✅
"""

from sqlalchemy import Column, String, Date, DateTime, Integer, Numeric, Text,Boolean
from app.db.base import Base


class EventCapitalPersistence(Base):
    __tablename__ = "event_capital_persistence"  # 数据库表名

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基础信息
    trade_date = Column(Date, nullable=False, comment="交易日")
    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(64), nullable=False, comment="股票名称")

    # 时间区间（事件是“一段行为”，非瞬时点）
    start_time = Column(DateTime, nullable=False, comment="持续流入开始时间")
    end_time = Column(DateTime, nullable=False, comment="持续流入结束时间")
    duration_minutes = Column(Integer, nullable=False, comment="持续分钟数")

    # 资金行为指标
    zl_inflow_sum = Column(Numeric(18, 2), nullable=False, comment="主力净流入累计金额（元）")
    positive_minute_ratio = Column(Numeric(5, 2), nullable=False, comment="主力净流入为正的分钟占比（0～1）")
    price_change_pct = Column(Numeric(6, 2), nullable=False, comment="区间价格涨跌幅（%）")
    avg_zl_zb = Column(Numeric(6, 2), nullable=False, comment="区间平均主力占比（%）")

    # 人类可读说明
    reason = Column(Text, nullable=True, comment="事件触发原因说明（给人看的）")
    # 👇 新增字段：标识是否为收盘冻结事件
    is_final = Column(Boolean, nullable=False, default=False, index=True, comment="是否为收盘冻结事件")
    # ✅ 新增字段：事件生成时间（用于追踪何时被系统产出）
    generated_at = Column(DateTime, nullable=False, comment="事件生成时间")


    __table_args__ = ({"comment": "资本持续性事件表"},)