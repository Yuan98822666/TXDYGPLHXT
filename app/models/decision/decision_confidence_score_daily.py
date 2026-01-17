"""
决策信心分日表
定位：系统唯一输出，用于 T+1 交易准备
原则：只基于 is_final = TRUE 的事件生成
"""

from sqlalchemy import Column, String, Date, DateTime, Integer, Text, JSON
from app.db.base import Base


class DecisionConfidenceScoreDaily(Base):
    __tablename__ = "decision_confidence_score_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, comment="交易日（T日，决定T+1）")

    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(64), nullable=False, comment="股票名称")

    decision_state = Column(
        String(20),
        nullable=False,
        comment="决策状态：FORBIDDEN / OBSERVE / PREPARE / ALLOW_NEXT_DAY"
    )
    confidence_score = Column(Integer, nullable=False, comment="信心分（0～100，仅用于排序）")

    # 子项评分（用于复盘）
    block_strength_score = Column(Integer, nullable=True, comment="板块背景分")
    capital_score = Column(Integer, nullable=True, comment="资金持续性分")
    dominance_score = Column(Integer, nullable=True, comment="控盘强度分")
    consensus_score = Column(Integer, nullable=True, comment="市场共识分")

    used_event_ids = Column(JSON, nullable=True, comment="引用的事件ID列表（用于追踪）")
    generated_at = Column(DateTime, nullable=False, comment="决策生成时间")

    __table_args__ = (
        {"comment": "决策信心分日表（T日生成，用于T+1）"},
    )