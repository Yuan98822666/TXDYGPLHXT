"""
文件路径：app/models/raw/raw_block_snapshot_event.py
作用说明：
    定义【板块资金快照事件】ORM。
    本表用于记录：
        在某一市场时间点，
        某一个板块自身的行情状态、资金状态与结构规模等
        原始市场事实。
设计原则：
    1. 不包含任何股票级别信息
    2. 不记录领涨股 / 资金股
    3. 不做强弱、主线判断
    4. 只描述“板块此刻是什么样子”
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class RawBlockSnapshotEvent(Base):
    """
    表名：raw_block_snapshot_event
    中文名：板块原始行情快照事件表
    """
    __tablename__ = "raw_block_snapshot_event"
    # =========================
    # 1. 事件与批次
    # =========================
    event_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="事件ID，全局唯一")
    kz_no = Column(String(64), nullable=False, index=True, comment="快照批次号：与个股快照共享，用于板块-个股联动")
    # =========================
    # 2. 板块身份
    # =========================
    block_code = Column(String(20), nullable=False, index=True, comment="板块代码（东方财富板块ID）")
    block_name = Column(String(50), nullable=False, comment="板块名称")
    block_type = Column(String(20), nullable=True, comment="板块类型：行业 / 概念")
    # =========================
    # 3. 行情事实
    # =========================
    block_index = Column(Float, nullable=True, comment="板块指数")
    block_change_pct = Column(Float, nullable=True, comment="板块涨跌幅（%）")
    block_change_amt = Column(Float, nullable=True, comment="板块涨跌额")
    block_turnover_rate = Column(Float, nullable=True, comment="板块换手率（%）")
    # =========================
    # 4. 板块结构
    # =========================
    up_count = Column(Integer, nullable=True, comment="上涨家数")
    down_count = Column(Integer, nullable=True, comment="下跌家数")
    # limit_up_count = Column(Integer, nullable=True, comment="涨停家数（如接口可得）")
    # limit_down_count = Column(Integer, nullable=True, comment="跌停家数（如接口可得）")
    # =========================
    # 5. 板块资金
    # =========================
    main_inflow = Column(Float, nullable=True, comment="板块主力资金净流入")
    super_inflow = Column(Float, nullable=True, comment="板块超大单资金净流入")
    large_inflow = Column(Float, nullable=True, comment="板块大单资金净流入")
    medium_inflow = Column(Float, nullable=True, comment="板块中单资金净流入")
    small_inflow = Column(Float, nullable=True, comment="板块小单资金净流入")
    # =========================
    # 6. 时间字段
    # =========================
    market_time = Column(DateTime, nullable=False, comment="市场时间：该板块状态对应的市场时间")
    fetch_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, comment="抓取时间：程序请求接口时间")

    def __repr__(self):
        return f"<RawBlockSnapshotEvent "f"{self.block_name} "f"time={self.market_time}>"
