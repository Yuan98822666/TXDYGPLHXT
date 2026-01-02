"""
文件名：raw_block_named_stock_event.py
作用说明：
    板块点名股票原始事件表。
    用于记录在某一市场时间点，
    某一个板块在接口层面
    明确“点名”的股票关系事实。

    本表不表示股票强弱、不表示龙头，
    只表示【被板块点名】这一客观事实。

所属层级：
    数据采集层（Raw Data Layer）

设计原则：
    1. 一条记录 = 一次点名事实
    2. 不合并、不去重
    3. 不判断业务含义
    4. 强绑定 kz_no 与 market_time
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class RawBlockNamedStockEvent(Base):
    """
    表名：raw_block_named_stock_event
    中文名：板块点名股票原始事件表
    """

    __tablename__ = "raw_block_named_stock_event"

    # =========================
    # 1. 事件与批次
    # =========================
    event_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="事件ID，全局唯一")
    kz_no = Column(BigInteger, nullable=False, index=True, comment="快照批次号：与板块/个股快照对齐")
    # =========================
    # 2. 板块身份
    # =========================
    block_code = Column(String(20), nullable=False, index=True, comment="板块代码（东方财富板块ID）")
    block_name = Column(String(64), nullable=False, comment="板块名称")
    block_type = Column(String(20), nullable=False, comment="板块类型：industry / concept")
    # =========================
    # 3. 股票身份
    # =========================
    stock_code = Column(String(16), nullable=False, index=True, comment="股票代码")
    stock_name = Column(String(64), nullable=False, comment="股票名称")
    # =========================
    # 4. 点名角色
    # =========================
    role_type = Column(String(16), nullable=False, comment="点名角色：leader / laggard / other")
    # =========================
    # 5. 时间三元组
    # =========================
    market_time = Column(DateTime, nullable=False, index=True, comment="市场时间：该点名事实在市场中的时间点")
    store_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, comment="入库时间")
    def __repr__(self):
        """
        调试用简要表示
        """
        return (
            f"<RawBlockNamedStockEvent "
            f"block={self.block_name} "
            f"stock={self.stock_code} "
            f"role={self.role_type} "
            f"time={self.market_time}>"
        )
