# -*- coding: utf-8 -*-
"""
股票日K表 ORM 模型

表名：raw_day_stock
用途：每日收盘后入库，与 raw_min_stock 字段保持一致
"""
from sqlalchemy import Column, BigInteger, String, Numeric, SmallInteger, Date, DateTime, Index
from datetime import datetime, timezone
from app.db.base import Base


class RawDayStock(Base):
    """
    股票日K表

    采集频率：每日收盘后（15:00-15:30）
    采集范围：stock_imp=1 的股票
    采集来源：从 raw_min_stock 快照表获取收盘时数据
    """
    __tablename__ = "raw_day_stock"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增ID")

    # 身份标识
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码，关联 base_stock")
    raw_no = Column(String(30), nullable=False, index=True, comment="快照批次号")

    # 时间维度
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")

    # 价格相关（与 raw_min_stock 保持一致）
    stock_zsj = Column(Numeric(12, 4), comment="昨收价（元）")
    stock_kpj = Column(Numeric(12, 4), comment="开盘价（元）")
    stock_zgj = Column(Numeric(12, 4), comment="最高价（元）")
    stock_zdj = Column(Numeric(12, 4), comment="最低价（元）")
    stock_spj = Column(Numeric(12, 4), comment="收盘价（元）")
    stock_ztj = Column(Numeric(12, 4), comment="涨停价（元）")
    stock_dtj = Column(Numeric(12, 4), comment="跌停价（元）")

    # 成交相关
    stock_cjl = Column(BigInteger, comment="成交量（手）")
    stock_cje = Column(Numeric(18, 2), comment="成交额（元）")
    stock_zdf = Column(Numeric(8, 4), comment="涨跌幅（%）")
    stock_zf = Column(Numeric(8, 4), comment="震幅（%）")
    stock_zde = Column(Numeric(12, 4), comment="涨跌额（元）")
    stock_hsl = Column(Numeric(8, 4), comment="换手率（%）")
    stock_sjhsl = Column(Numeric(8, 4), comment="实际换手率（%）")

    # 估值相关
    stock_syl = Column(Numeric(10, 4), comment="市盈率TTM")
    stock_sjl = Column(Numeric(10, 4), comment="市净率")
    stock_zsz = Column(Numeric(20, 2), comment="总市值（元）")
    stock_ltsz = Column(Numeric(20, 2), comment="流通市值（元）")
    stock_ltg = Column(BigInteger, comment="流通股（股）")

    # 涨停状态：0=正常，1=涨停，2=炸板，3=跌停
    stock_ztzt = Column(SmallInteger, default=0, comment="涨停状态：0=正常，1=涨停，2=炸板，3=跌停")

    # 资金流向（五档）
    stock_zl_inflow = Column(Numeric(18, 2), comment="主力净流入（元）")
    stock_cd_inflow = Column(Numeric(18, 2), comment="超大单净流入（元）")
    stock_dd_inflow = Column(Numeric(18, 2), comment="大单净流入（元）")
    stock_zd_inflow = Column(Numeric(18, 2), comment="中单净流入（元）")
    stock_xd_inflow = Column(Numeric(18, 2), comment="小单净流入（元）")

    # 资金流向占比
    stock_zl_zb = Column(Numeric(8, 4), comment="主力净流入占比（%）")
    stock_cd_zb = Column(Numeric(8, 4), comment="超大单净流入占比（%）")
    stock_dd_zb = Column(Numeric(8, 4), comment="大单净流入占比（%）")
    stock_zd_zb = Column(Numeric(8, 4), comment="中单净流入占比（%）")
    stock_xd_zb = Column(Numeric(8, 4), comment="小单净流入占比（%）")

    # 入库时间
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="入库时间"
    )

    # 联合唯一索引：同一股票同一日期只能有一条记录
    __table_args__ = (
        Index("ix_raw_day_stock_code_date", "stock_code", "trade_date", unique=True),
        {"comment": "股票日K表"},
    )

    def __repr__(self):
        return f"<RawDayStock code={self.stock_code} date={self.trade_date} zdf={self.stock_zdf}>"
