"""
文件名：raw_limit_up_pool.py
作用说明：
    涨停池原始快照事件表。
    用于记录在某一市场时间点，
    市场中“当前处于涨停状态”的股票的
    封板行为、资金、连板结构等原始事实。
    本表是一个【涨停池快照表】，而非日终结果表。
所属层级：
    数据采集层（Raw Data Layer）
设计原则：
    1. 允许同一股票在同一交易日出现多次
    2. 每一条记录代表“某一时刻的市场认定状态”
    3. 不判断最终是否涨停
    4. 不推断情绪或梯队
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    BigInteger,
    Date
)
from app.db.base import Base
from datetime import datetime, timezone



class RawLimitUpPool(Base):
    """
    表名：raw_limit_up_snapshot_event
    中文名：涨停池原始快照事件表
    """
    __tablename__ = "raw_limit_up_pool"
    # =========================
    # 1. 事件与批次
    # =========================
    event_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="事件ID")
    kz_no = Column(BigInteger, nullable=False, index=True, comment="快照批次号：与板块、个股快照对齐")
    # =========================
    # 2. 股票身份
    # =========================
    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(64), nullable=False, comment="股票名称")
    exchange = Column(String(8), nullable=True, comment="交易所：SH / SZ")
    # =========================
    # 3. 涨停行情状态
    # =========================
    last_price = Column(Float, nullable=True, comment="最新成交价")
    limit_up_price = Column(Float, nullable=True, comment="涨停价")
    change_pct = Column(Float, nullable=True, comment="涨跌幅（%）")
    turnover_rate = Column(Float, nullable=True, comment="换手率（%）")
    amount = Column(Float, nullable=True, comment="成交额（元）")
    # =========================
    # 4. 封板行为（快照态）
    # =========================
    first_seal_time = Column(Integer, nullable=True, comment="首次封板时间（HHMM 或 HHMMSS）")
    last_seal_time = Column(Integer, nullable=True, comment="最近一次封板时间")
    seal_fund = Column(Float, nullable=True, comment="封板资金（元）")
    break_count = Column(Integer, nullable=True, comment="当日炸板次数（接口给定）")
    # =========================
    # 5. 连板结构
    # =========================
    continuous_limit_count = Column(Integer, nullable=True, comment="连板数")
    limit_stat_days = Column(Integer, nullable=True, comment="统计周期天数（几天几板）")
    limit_stat_count = Column(Integer, nullable=True, comment="统计周期内涨停次数")
    # =========================
    # 6. 原始板块归属
    # =========================
    industry_block = Column(String(64), nullable=True, comment="所属行业板块（接口原始）")
    # =========================
    # 7. 时间三元组
    # =========================
    trade_date = Column(Date, nullable=False, index=True, comment="交易日")
    market_time = Column(DateTime, nullable=False, comment="市场时间：该状态在市场中的时间点")
    add_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),comment="入库时间")
    def __repr__(self):
        return (
            f"<RawLimitUpSnapshotEvent "f"{self.stock_code} "f"time={self.market_time}>")
