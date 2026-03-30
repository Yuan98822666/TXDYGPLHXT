# -*- coding: utf-8 -*-
"""
板块快照表 ORM 模型

表名：raw_min_block
用途：每分钟采集所有板块（GN + HY + FG）的快照数据

字段来源：东方财富板块接口
"""
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Date, DateTime, Index
from datetime import datetime, timezone
from app.db.base import Base


class RawMinBlock(Base):
    """
    板块快照表

    采集频率：每分钟
    采集范围：所有板块（base_block 全部，包括 GN/HY/FG）
    """
    __tablename__ = "raw_min_block"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增ID")

    # 身份标识
    block_code = Column(String(20), nullable=False, index=True, comment="板块代码，关联 base_block")
    block_name = Column(String(100), comment="板块名称（冗余）")
    raw_no = Column(String(30), nullable=False, index=True, comment="批次号，格式：YYYYMMDDHHMMSS")

    # 时间维度
    snapshot_time = Column(DateTime, nullable=False, comment="采集时间戳（精确到秒）")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")

    # 行情数据
    block_zs = Column(Numeric(12, 4), comment="板块最新指数")
    block_ltg = Column(BigInteger, comment="板块流通股")
    block_zdf = Column(Numeric(8, 4), comment="涨跌幅（%）")
    block_lb = Column(Numeric(8, 4), comment="量比")
    block_hsl = Column(Numeric(8, 4), comment="换手率（%）")
    stock_cjls = Column(BigInteger, comment="成交量（手）")

    # 涨跌家数
    block_up_stock = Column(Integer, comment="上涨家数")
    block_pi_stock = Column(Integer, comment="平盘家数")
    block_dw_stock = Column(Integer, comment="下跌家数")

    # 资金流向（五档）- 金额
    block_zl_inflow = Column(Numeric(18, 2), comment="主力净流入（元）")
    block_cd_inflow = Column(Numeric(18, 2), comment="超大单净流入（元）")
    block_dd_inflow = Column(Numeric(18, 2), comment="大单净流入（元）")
    block_zd_inflow = Column(Numeric(18, 2), comment="中单净流入（元）")
    block_xd_inflow = Column(Numeric(18, 2), comment="小单净流入（元）")

    # 资金流向占比
    block_zl_zb = Column(Numeric(8, 4), comment="主力净流入占比（%）")
    block_cd_zb = Column(Numeric(8, 4), comment="超大单净流入占比（%）")
    block_dd_zb = Column(Numeric(8, 4), comment="大单净流入占比（%）")
    block_zd_zb = Column(Numeric(8, 4), comment="中单净流入占比（%）")
    block_xd_zb = Column(Numeric(8, 4), comment="小单净流入占比（%）")

    # 领涨股
    leader_stock_code = Column(String(20), comment="领涨个股代码")
    leader_stock_name = Column(String(100), comment="领涨个股名称")
    leader_stock_zdf = Column(Numeric(8, 4), comment="领涨个股涨幅（%）")

    # 资金流入最多股
    money_stock_code = Column(String(20), comment="资金流入最多个股代码")
    money_stock_name = Column(String(100), comment="资金流入最多个股名称")

    # 入库时间
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="入库时间"
    )

    # 联合唯一索引：同一板块同一时间只能有一条记录
    __table_args__ = (
        Index("ix_raw_min_block_code_time", "block_code", "snapshot_time", unique=True),
        {"comment": "板块快照表"},
    )

    def __repr__(self):
        return f"<RawMinBlock code={self.block_code} name={self.block_name} zdf={self.block_zdf}>"
