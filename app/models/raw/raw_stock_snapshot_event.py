"""
文件名：raw_stock_snapshot_event.py
作用说明：
    定义【个股资金信息快照表】ORM 模型。
    本模型用于存储从市场接口直接获取的个股行情与资金原始数据，
    不包含任何计算、判断或衍生逻辑，是系统中最底层的“事实记录层”。
设计原则：
    1. 字段一一对应接口返回值
    2. 不在 Raw 层做任何业务判断
    3. 必须支持高频、多次、可重算
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    BigInteger,
    Index
)
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class RawStockSnapshotEvent(Base):
    """
    表名：raw_stock_snapshot_event
    中文名：个股原始行情与资金快照事件表
    表作用：
        记录某一时间点，从市场接口获取到的“某只股票”的
        行情、成交、换手、市值、资金流向等最原始事实数据。
    注意：
        - 本表是【只写不改】表
        - 不允许在此表中做任何计算或业务判断
        - 所有字段均可用于事后重算与回测
    """
    __tablename__ = "raw_stock_snapshot_event"
    # =========================
    # 1. 主键与事件控制字段
    # =========================
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键，自增ID，仅用于数据库唯一性")
    kz_no = Column(String(64), nullable=False, index=True,comment="快照批次号：一次完整市场抓取动作的唯一标识，用于对齐板块/个股数据")
    # =========================
    # 2. 时间字段（极其重要）
    # =========================
    market_time = Column(DateTime, nullable=False, comment="市场时间：行情数据对应的市场时间（接口返回或推算）")
    fetch_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow,comment="数据获取时间：程序实际向接口请求并成功返回的时间")
    store_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow,comment="数据入库时间：该条记录写入数据库的时间")
    # =========================
    # 3. 股票身份字段
    # =========================
    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码，如 002196 / 600519")
    stock_name = Column(String(64), nullable=False, comment="股票名称，如 方正电机")
    exchange = Column(String(8), nullable=True, comment="交易所标识，如 SZ / SH（可由 f13 推导）")
    # =========================
    # 4. 行情与成交字段
    # =========================
    last_price = Column(Float, nullable=True, comment="最新价")
    change_amount = Column(Float, nullable=True, comment="涨跌额")
    change_rate = Column(Float, nullable=True, comment="涨跌幅（百分比）")
    volume = Column(BigInteger, nullable=True, comment="成交量（股）")
    amount = Column(BigInteger, nullable=True, comment="成交额（元）")
    # =========================
    # 5. 市值与换手率
    # =========================
    turnover_rate = Column(Float, nullable=True, comment="换手率（百分比）")
    total_market_value = Column(BigInteger, nullable=True, comment="总市值（元）")
    float_market_value = Column(BigInteger, nullable=True, comment="流通市值（元）")
    # =========================
    # 6. 资金流向字段（五档）
    # =========================
    main_net_inflow = Column(BigInteger, nullable=True, comment="主力资金净流入（元）")
    super_large_net_inflow = Column(BigInteger, nullable=True, comment="超大单净流入（元）")
    large_net_inflow = Column(BigInteger, nullable=True, comment="大单净流入（元）")
    medium_net_inflow = Column(BigInteger, nullable=True, comment="中单净流入（元）")
    small_net_inflow = Column(BigInteger, nullable=True, comment="小单净流入（元）")
    # =========================
    # 7. 接口溯源字段
    # =========================
    source = Column(String(32), nullable=False, comment="数据来源标识，如 eastmoney")
    raw_symbol = Column(String(64), nullable=True, comment="接口原始标识字段，用于字段含义变更后的回溯")
    # =========================
    # 索引定义
    # =========================
    __table_args__ = (Index("idx_stock_time", "stock_code", "market_time"),)
