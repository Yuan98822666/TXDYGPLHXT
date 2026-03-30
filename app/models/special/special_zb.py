# -*- coding: utf-8 -*-
"""
炸板池表 ORM 模型

表名：special_zb
"""
from sqlalchemy import Column, BigInteger, String, Integer, Numeric, Date, DateTime, Index
from datetime import datetime, timezone
from app.db.base import Base


class SpecialZb(Base):
    __tablename__ = "special_zb"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增ID")
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(100), comment="股票名称")
    mkt = Column(Integer, comment="市场(0=深,1=沪)")
    price = Column(Numeric(12, 4), comment="最新价（元）")
    ztp = Column(Numeric(12, 4), comment="涨停价（元）")
    zdp = Column(Numeric(8, 4), comment="涨跌幅（%）")
    amount = Column(Numeric(18, 2), comment="成交额（元）")
    ltsz = Column(Numeric(18, 2), comment="流通市值（元）")
    tshare = Column(Numeric(18, 2), comment="流通股本")
    hs = Column(Numeric(8, 4), comment="换手率（%）")
    zf = Column(Numeric(8, 4), comment="振幅（%）")
    zs = Column(Numeric(8, 4), comment="涨停统计")
    fbt = Column(Integer, comment="首次炸板时间（HHMMSS）")
    zbc = Column(Integer, comment="炸板次数")
    hybk = Column(String(50), comment="行业板块")
    zt_days = Column(Integer, comment="涨停天数")
    zt_count = Column(Integer, comment="涨停次数")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), comment="入库时间")

    __table_args__ = (
        Index("ix_special_zb_code_date", "stock_code", "trade_date", unique=True),
        {"comment": "炸板池表"},
    )

    def __repr__(self):
        return f"<SpecialZb code={self.stock_code} name={self.stock_name}>"
