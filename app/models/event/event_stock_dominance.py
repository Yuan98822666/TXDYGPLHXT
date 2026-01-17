"""
控盘程度事件模型一句话定义：
EventStockDominance = 主力对某只股票形成有效控制，
表现为筹码集中、波动收窄、反向单被压制。
它回答的问题是：“这票是不是‘主力说了算’？”
"""

from sqlalchemy import Column, String, Date, DateTime, Integer, Numeric, Text,Boolean
from app.db.base import Base


class EventStockDominance(Base):
    __tablename__ = "event_stock_dominance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, comment="交易日")

    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(64), nullable=False, comment="股票名称")

    start_time = Column(DateTime, nullable=False, comment="控盘开始时间")
    end_time = Column(DateTime, nullable=False, comment="控盘结束时间")
    duration_minutes = Column(Integer, nullable=False, comment="控盘持续分钟数")

    zl_control_ratio = Column(Numeric(5, 2), nullable=False, comment="主力控盘度（主力净买占比）")
    retail_resistance_ratio = Column(Numeric(5, 2), nullable=False, comment="散户抵抗强度（小单卖出占比）")
    price_volatility = Column(Numeric(6, 2), nullable=False, comment="价格波动率（标准差/均值）")
    bid_ask_imbalance = Column(Numeric(6, 2), nullable=False, comment="买卖不平衡度（大单净买 - 小单净卖）")

    reason = Column(Text, nullable=True, comment="控盘原因说明（给人看的）")
    # 👇 新增字段：标识是否为收盘冻结事件
    is_final = Column(Boolean, nullable=False, default=False, index=True, comment="是否为收盘冻结事件")
    # ✅ 新增字段：事件生成时间（用于追踪何时被系统产出）
    generated_at = Column(DateTime, nullable=False, comment="事件生成时间")

    __table_args__ = ({"comment": "控盘程度事件表"},)