# -*- coding: utf-8 -*-
"""
文件路径：app/models/analysis/analysis_block_stock_resonance.py
作用说明：板块-股票共振分析表 ORM 模型

表设计说明：
  - 记录每个批次(raw_no)中个股与其所属板块的共振关系
  - 计算涨停潜力因子、受重视程度因子、板块受重视程度因子
  - 标记领涨股、资金流入最多股、共振状态
  - 数据量较大，使用 BigInteger 主键

索引设计：
  - idx_resonance_raw_no : 按批次查询
  - idx_resonance_stock : 按股票查询
  - idx_resonance_block : 按板块查询
  - idx_resonance_date : 按日期查询
  - idx_resonance_zt_factor : 按涨停潜力因子排序
"""
from sqlalchemy import Column, String, BigInteger, DateTime, Date, Boolean, Index, Numeric
from datetime import datetime, timezone
from app.db.base import Base


class AnalysisBlockStockResonance(Base):
    """
    表名：analysis_block_stock_resonance
    中文名：板块-股票共振分析表（分钟级）

    列说明：
    - id : 主键ID，自增，BigInteger
    - stock_code : 股票代码
    - block_code : 板块代码
    - raw_no : 批次号，关联 raw_min_stock/block 的 raw_no
    - trade_date : 交易日期
    - snapshot_time : 采集时间戳

    - stock_zl_inflow : 个股主力净流入（元）
    - block_zl_inflow : 板块主力净流入（元）
    - stock_ltsz : 个股流通市值（元）

    - zt_potential_factor : 涨停潜力因子 = 个股净流入/流通市值
    - attention_factor : 受重视程度因子 = 个股净流入/板块净流入
    - block_importance_factor : 板块受重视程度因子 = 板块净流入/所有板块总和

    - is_leader : 是否为板块领涨股
    - is_money_leader : 是否为板块资金流入最多股
    - is_resonance : 是否共振（个股和板块同向流入）

    - created_at : 记录创建时间
    """
    __tablename__ = "analysis_block_stock_resonance"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="主键ID，自增，BigInteger")

    # 关联字段
    stock_code = Column(String(20), nullable=False, index=True,
                        comment="股票代码，如 000001")
    block_code = Column(String(20), nullable=False, index=True,
                        comment="板块代码，如 BK0428")
    raw_no = Column(String(20), nullable=False, index=True,
                    comment="批次号，格式 YYYYMMDDHHMMSS，关联 raw_min_stock/block")
    trade_date = Column(Date, nullable=False, index=True,
                        comment="交易日期")
    snapshot_time = Column(DateTime(timezone=True), nullable=False,
                           comment="采集时间戳")

    # 原始数据
    stock_zl_inflow = Column(BigInteger, nullable=True,
                             comment="个股主力净流入（元）")
    block_zl_inflow = Column(BigInteger, nullable=True,
                             comment="板块主力净流入（元）")
    stock_ltsz = Column(BigInteger, nullable=True,
                        comment="个股流通市值（元）")

    # 计算因子（使用 Numeric 保证精度）
    zt_potential_factor = Column(Numeric(10, 6), nullable=True, index=True,
                                 comment="涨停潜力因子 = 个股净流入/流通市值，单位：小数形式（如 0.05 表示 5%）")
    attention_factor = Column(Numeric(10, 6), nullable=True, index=True,
                              comment="受重视程度因子 = 个股净流入/板块净流入，单位：小数形式")
    block_importance_factor = Column(Numeric(10, 6), nullable=True, index=True,
                                     comment="板块受重视程度因子 = 板块净流入/所有板块总和，单位：小数形式")

    # 共振标记
    is_leader = Column(Boolean, nullable=False, default=False,
                       comment="是否为板块领涨股，与 raw_min_block.leader_stock_code 匹配")
    is_money_leader = Column(Boolean, nullable=False, default=False,
                             comment="是否为板块资金流入最多股，与 raw_min_block.money_stock_code 匹配")
    is_resonance = Column(Boolean, nullable=False, default=False,
                          comment="是否共振，个股和板块同向流入（都正或都负）")

    # 创建时间
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc),
                        comment="记录创建时间")

    # 联合唯一约束：同一批次同一股票同一板块只能有一条记录
    __table_args__ = (
        Index('idx_resonance_raw_stock_block', 'raw_no', 'stock_code', 'block_code', unique=True),
        Index('idx_resonance_zt_factor', 'trade_date', 'zt_potential_factor'),
        Index('idx_resonance_attention', 'trade_date', 'attention_factor'),
        Index('idx_resonance_resonance', 'trade_date', 'is_resonance', 'zt_potential_factor'),
    )

    def __repr__(self):
        return (
            f"<AnalysisBlockStockResonance "
            f"stock={self.stock_code} "
            f"block={self.block_code} "
            f"raw_no={self.raw_no} "
            f"zt_factor={self.zt_potential_factor}>"
        )
