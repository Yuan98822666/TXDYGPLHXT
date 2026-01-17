"""
群体共识事件模型一句话定义：
EventStockConsensus = 同一只股票，在同一交易日内，
被多个不同板块“反复点名”，形成市场共识。
我们只问一件事：“市场是不是在反复用不同角度说：就是它。”
"""

from sqlalchemy import Column, String, Date, DateTime, Integer, Numeric, Text,Boolean
from app.db.base import Base


class EventStockConsensus(Base):
    __tablename__ = "event_stock_consensus"  # 数据库表名（业务语义，无 event_ 前缀）

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基础信息
    trade_date = Column(Date, nullable=False, comment="交易日")
    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(64), nullable=True, comment="股票名称")

    # 共识强度指标
    mentioned_block_count = Column(Integer, nullable=False, comment="被点名的板块数量（去重）")
    mentioned_times = Column(Integer, nullable=False, comment="被点名总次数（不去重）")
    money_block_count = Column(Integer, nullable=False, comment="作为资金代表被点名的板块数")
    lider_block_count = Column(Integer, nullable=False, comment="作为领涨代表被点名的板块数")

    # 时间维度
    first_mentioned_time = Column(DateTime, nullable=False, comment="首次被点名时间")
    last_mentioned_time = Column(DateTime, nullable=False, comment="最后一次被点名时间")
    duration_minutes = Column(Integer, nullable=False, comment="被点名持续时长（分钟）")

    # 内部评分 & 人类可读说明
    consensus_strength = Column(Numeric(10, 2), nullable=False, comment="共识强度评分（内部使用）")
    reason = Column(Text, nullable=True, comment="共识形成原因说明（给人看的）")
    # 👇 新增字段：标识是否为收盘冻结事件
    is_final = Column(Boolean, nullable=False, default=False, index=True, comment="是否为收盘冻结事件")
    # ✅ 新增字段：事件生成时间（用于追踪何时被系统产出）
    generated_at = Column(DateTime, nullable=False, comment="事件生成时间")


    __table_args__ = ({"comment": "群体共识事件表"},)