"""
板块启动事件模型一句话定义：
EventBlockStart = 市场出现明确的“钱往哪吹”信号，
表现为多个板块在短时间内集体放量上涨。
它回答的问题是：“今天有没有主线？”
"""

from sqlalchemy import Column, String, Date, DateTime, Integer, Numeric, Text,Boolean
from app.db.base import Base


class EventBlockStart(Base):
    __tablename__ = "event_block_start"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, comment="交易日")

    block_code = Column(String(32), nullable=False, index=True, comment="板块代码")
    block_name = Column(String(64), nullable=False, comment="板块名称")

    start_time = Column(DateTime, nullable=False, comment="启动开始时间")
    end_time = Column(DateTime, nullable=False, comment="启动确认时间")
    duration_minutes = Column(Integer, nullable=False, comment="从启动到确认的分钟数")

    block_up_count = Column(Integer, nullable=False, comment="板块内上涨个股数")
    block_total_count = Column(Integer, nullable=False, comment="板块总个股数")
    up_ratio = Column(Numeric(5, 2), nullable=False, comment="上涨个股占比（0～1）")
    avg_change_pct = Column(Numeric(6, 2), nullable=False, comment="板块平均涨幅（%）")
    volume_ratio = Column(Numeric(6, 2), nullable=False, comment="板块量比（vs 5日均量）")

    reason = Column(Text, nullable=True, comment="启动原因说明（给人看的）")
    # 👇 新增字段：标识是否为收盘冻结事件
    is_final = Column(Boolean, nullable=False, default=False, index=True, comment="是否为收盘冻结事件")

    __table_args__ = ({"comment": "板块启动事件表"},)