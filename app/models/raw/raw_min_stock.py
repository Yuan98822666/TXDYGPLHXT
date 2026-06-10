# -*- coding: utf-8 -*-
"""
股票快照表 ORM 模型

表名：raw_min_stock
用途：每分钟采集 stock_imp=1 的股票快照数据
"""
from sqlalchemy import Column, BigInteger, String, Numeric, SmallInteger, Date, DateTime, Index
from datetime import datetime, timezone
from app.db.base import Base


class RawMinStock(Base):
    """
    股票快照表

    采集频率：每分钟
    采集范围：base_stock.stock_imp = 1 的股票
    """
    __tablename__ = "raw_min_stock"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增ID")

    # 身份标识
    stock_code = Column(String(20), nullable=False, index=True, comment="股票代码，关联 base_stock")
    raw_no = Column(String(30), nullable=False, index=True, comment="批次号，格式：YYYYMMDDHHMMSS")

    # 时间维度
    snapshot_time = Column(DateTime, nullable=False, comment="采集时间戳（精确到秒）")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期")

    # 价格相关（单位：分，需除以100）
    stock_zsj = Column(Numeric(12, 4), comment="昨收价（元）")
    stock_kpj = Column(Numeric(12, 4), comment="开盘价（元）")
    stock_zgj = Column(Numeric(12, 4), comment="最高价（元）")
    stock_zdj = Column(Numeric(12, 4), comment="最低价（元）")
    stock_spj = Column(Numeric(12, 4), comment="最新价（元）")
    stock_ztj = Column(Numeric(12, 4), comment="涨停价（元）")
    stock_dtj = Column(Numeric(12, 4), comment="跌停价（元）")

    # 成交相关
    stock_cjl = Column(BigInteger, comment="成交量（手）")
    stock_cje = Column(Numeric(18, 2), comment="成交额（元）")
    stock_zdf = Column(Numeric(8, 4), comment="涨跌幅（%）")
    stock_zf = Column(Numeric(8, 4), comment="震幅（%）")
    stock_zde = Column(Numeric(12, 4), comment="涨跌额（元）")
    stock_hsl = Column(Numeric(8, 4), comment="换手率（%）")
    stock_sjhsl = Column(Numeric(8, 4), comment="实际换手率（%），计算：成交量/自由流通股*100")

    # 估值相关
    stock_syl = Column(Numeric(12, 4), comment="市盈率TTM")
    stock_sjl = Column(Numeric(12, 4), comment="市净率")
    stock_zsz = Column(Numeric(20, 2), comment="总市值（元）")
    stock_ltsz = Column(Numeric(20, 2), comment="流通市值（元）")
    stock_ltg = Column(BigInteger, comment="流通股（股）")

    # 涨停状态：0=正常，1=涨停，2=炸板，3=跌停
    # 判断规则：现价=涨停价→涨停；最高价=涨停价但现价≠涨停价→炸板；现价=跌停价→跌停
    stock_ztzt = Column(SmallInteger, default=0, comment="涨停状态：0=正常，1=涨停，2=炸板，3=跌停")

    # 资金流向（五档，单位：元）
    stock_zl_inflow = Column(Numeric(18, 2), comment="主力净流入（元）")
    stock_cd_inflow = Column(Numeric(18, 2), comment="超大单净流入（元）")
    stock_dd_inflow = Column(Numeric(18, 2), comment="大单净流入（元）")
    stock_zd_inflow = Column(Numeric(18, 2), comment="中单净流入（元）")
    stock_xd_inflow = Column(Numeric(18, 2), comment="小单净流入（元）")

    # 资金流向占比（单位：%）
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

    # 联合唯一索引：同一股票同一时间只能有一条记录
    __table_args__ = (
        Index("ix_raw_min_stock_code_time", "stock_code", "snapshot_time", unique=True),
        {"comment": "股票快照表"},
    )

    def __repr__(self):
        return f"<RawMinStock code={self.stock_code} time={self.snapshot_time} zdf={self.stock_zdf}>"
