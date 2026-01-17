# app/models/decision/decision_stock_daily.py
"""
盘尾决策结果表（每日生成一次）
作用：记录每只股票在当日盘尾是否“允许隔夜持仓”
这是系统从“观察”走向“实盘辅助”的核心输出表
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Text, DateTime
from sqlalchemy.sql import func  # 用于自动填充创建时间
from app.db.base import Base  # 声明式基类


class DecisionStockDaily(Base):
    __tablename__ = "decision_stock_daily"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 交易日期（如 2026-01-17）
    trade_date = Column(Date, nullable=False)

    # 股票代码（如 '600519'）
    stock_code = Column(String(16), nullable=False)

    # 股票名称（如 '贵州茅台'）
    stock_name = Column(String(64))

    # 决策状态（三选一）：
    # - ALLOW: 允许隔夜下注（候选池）
    # - OBSERVE: 观察，不操作
    # - FORBIDDEN: 禁止关注（次日直接跳过）
    decision_status = Column(String(16), nullable=False)

    # 信心分（0～100），用于排序，非决策依据
    confidence_score = Column(Numeric(5, 2))

    # === 辅助解释字段（用于人工复盘或前端展示）===
    block_hit_count = Column(Integer)  # 被多少个活跃板块点名
    capital_minutes = Column(Integer)  # 主力资金持续流入分钟数
    dominance_minutes = Column(Integer)  # 主力控盘持续分钟数
    consensus_strength = Column(Integer)  # 群体共识强度（点名总次数）

    # 决策原因（人类可读，如“尾盘资金撤退”）
    decision_reason = Column(Text)

    # 记录创建时间（UTC）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # SQLite 兼容性设置（确保自增主键）
    __table_args__ = ({"sqlite_autoincrement": True},)