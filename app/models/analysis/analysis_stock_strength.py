# -*- coding: utf-8 -*-
"""
文件路径：app/models/analysis/analysis_stock_strength.py
作用说明：个股强度统计表 ORM 模型

表设计说明：
  - 日级汇总表，记录每只股票当日在板块中的表现
  - 统计作为领涨股、资金流入最多股的出现次数
  - 计算个股强度因子

索引设计：
  - idx_strength_date_factor : 按日期和强度因子排序
  - idx_strength_stock_date : 按股票和日期查询
"""
from sqlalchemy import Column, String, BigInteger, DateTime, Date, Integer, Index, JSON
from datetime import datetime, timezone
from app.db.base import Base


class AnalysisStockStrength(Base):
    """
    表名：analysis_stock_strength
    中文名：个股强度统计表（日级汇总）

    列说明：
    - id : 主键ID，自增，BigInteger
    - stock_code : 股票代码
    - stock_name : 股票名称（冗余）
    - trade_date : 交易日期

    - leader_count : 作为领涨股出现次数
    - money_leader_count : 作为资金流入最多股出现次数
    - total_blocks : 当日涉及板块总数
    - strength_factor : 个股强度因子 = leader_count + money_leader_count

    - leader_blocks : 作为领涨股的板块列表（JSON）
    - money_leader_blocks : 作为资金流入最多股的板块列表（JSON）

    - created_at : 记录创建时间
    """
    __tablename__ = "analysis_stock_strength"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="主键ID")

    # 股票信息
    stock_code = Column(String(20), nullable=False, index=True,
                        comment="股票代码")
    stock_name = Column(String(100), nullable=True,
                        comment="股票名称")
    trade_date = Column(Date, nullable=False, index=True,
                        comment="交易日期")

    # 统计次数
    leader_count = Column(Integer, nullable=False, default=0,
                          comment="作为领涨股出现次数")
    money_leader_count = Column(Integer, nullable=False, default=0,
                                comment="作为资金流入最多股出现次数")
    total_blocks = Column(Integer, nullable=False, default=0,
                          comment="当日涉及板块总数")

    # 强度因子
    strength_factor = Column(Integer, nullable=False, default=0, index=True,
                             comment="个股强度因子")

    # 涉及板块详情（JSON格式）
    leader_blocks = Column(JSON, nullable=True,
                           comment="作为领涨股的板块列表")
    money_leader_blocks = Column(JSON, nullable=True,
                                 comment="作为资金流入最多股的板块列表")

    # 创建时间
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        comment="记录创建时间")

    # 联合唯一约束
    __table_args__ = (
        Index('idx_strength_stock_date', 'stock_code', 'trade_date', unique=True),
        Index('idx_strength_date_factor', 'trade_date', 'strength_factor'),
    )

    def __repr__(self):
        return (
            f"<AnalysisStockStrength "
            f"stock={self.stock_code} "
            f"date={self.trade_date} "
            f"strength={self.strength_factor}>"
        )
