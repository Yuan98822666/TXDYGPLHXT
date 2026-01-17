# app/models/decision/decision_open_validation.py
"""
次日集合竞价验证结果表
作用：对昨日标记为 ALLOW 的股票，在 T+1 日 9:25 进行“生死验证”
注意：此表只处理 ALLOW 股票，其他股票不参与验证
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Text, BigInteger, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class DecisionOpenValidation(Base):
    __tablename__ = "decision_open_validation"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False)  # 验证发生的日期（T+1 日）
    stock_code = Column(String(16), nullable=False)  # 股票代码

    # 验证结果（三选一）：
    # - CONFIRMED: 昨日判断未被否定，可持有/加仓
    # - NEUTRAL: 中性，需盘中进一步观察
    # - REJECTED: 昨日判断被市场推翻，永久放弃
    open_status = Column(String(16), nullable=False)

    # 开盘涨跌幅（%），用于判断强弱
    open_gap_pct = Column(Numeric(6, 2))

    # 开盘成交量（手），辅助判断流动性
    open_volume = Column(BigInteger)

    # 验证原因（如“大幅低开”）
    reason = Column(Text)

    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = ({"sqlite_autoincrement": True},)