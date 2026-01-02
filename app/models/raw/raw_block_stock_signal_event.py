"""
文件名：raw_block_stock_signal_event.py
作用说明：
    定义【板块点名股票原始事件】ORM 模型。
    本表用于记录：
        在某一市场时间点，
        某一个板块，通过某一种榜单或规则，
        明确“点名”了某一只股票这一事实。
设计原则：
    1. 不做强弱判断
    2. 不做龙头认定
    3. 不做因果推断
    4. 只记录市场已经发生的“指认关系”
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


class RawBlockStockSignalEvent(Base):
    """
    表名：raw_block_stock_signal_event
    中文名：板块点名股票原始事件表
    表作用：
        记录板块与股票之间，在某一时刻发生的
        “点名 / 关联 / 指认”这一原始事实事件。
    """
    __tablename__ = "raw_block_stock_signal_event"
    # =========================
    # 1. 主键与批次
    # =========================
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键，自增ID")
    kz_no = Column(String(64), nullable=False, index=True,comment="快照批次号：与板块/个股快照共享，用于同一市场时刻数据对齐")
    # =========================
    # 2. 板块身份
    # =========================
    block_code = Column(String(20), nullable=False, index=True, comment="板块代码（东方财富板块ID）")
    block_name = Column(String(50), nullable=False, comment="板块名称")
    block_type = Column(String(20), nullable=True, comment="板块类型：行业 / 概念")
    # =========================
    # 3. 股票身份
    # =========================
    stock_code = Column(String(16), nullable=False, index=True, comment="被点名股票代码")
    stock_name = Column(String(64), nullable=False, comment="被点名股票名称")
    exchange = Column(String(8), nullable=True, comment="交易所标识：SH / SZ")
    # =========================
    # 4. 点名事实字段（核心）
    # =========================
    signal_type = Column(String(32), nullable=False, comment="点名类型：""leader（领涨股） / ""capital（资金股） / ""limit_up（涨停池）")
    signal_rank = Column(Integer, nullable=True, comment="在该点名榜单中的排名（如资金流入排名第N）")
    signal_value = Column(Float, nullable=True, comment="点名原始数值，如资金净流入金额 / 涨幅值等")
    signal_value_desc = Column(String(64), nullable=True, comment="signal_value 含义说明，如：主力净流入 / 涨幅")
    # =========================
    # 5. 时间与溯源
    # =========================
    market_time = Column(DateTime, nullable=False, comment="市场时间：该点名行为发生时对应的市场时间")
    fetch_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow,comment="数据抓取时间：程序请求接口并返回成功的时间")
    store_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, comment="数据入库时间")
    source = Column(String(32), nullable=False, comment="数据来源，如 eastmoney")
    raw_symbol = Column(String(64), nullable=True, comment="接口原始字段标识，用于字段语义变更后的回溯")
    # =========================
    # 索引设计
    # =========================
    __table_args__ = (Index("idx_block_stock_time", "block_code", "stock_code", "market_time"),
                      Index("idx_stock_signal_type", "stock_code", "signal_type", "market_time"),)

    def __repr__(self):
        """
        调试用字符串表示
        """
        return f"<RawBlockStockSignalEvent "f"block={self.block_name} "f"stock={self.stock_name} "f"signal={self.signal_type} "f"time={self.market_time}>"
