"""
文件路径：app/models/raw/raw_block_huoyue.py

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
from app.db.base import Base
from datetime import datetime, timezone




class RawBlockHuoyue(Base):
    """
    表名：raw_block_huoyue
    中文名：板块活跃度 / 资金快照表
    """
    __tablename__ = "raw_block_huoyue"
    # =========================
    # 1. 事件与批次
    # =========================
    event_id = Column(BigInteger, primary_key=True, autoincrement=True, comment="事件ID，全局唯一")
    kz_no = Column(BigInteger, nullable=False, index=True, comment="快照批次号")
    # =========================
    # 2. 板块身份
    # =========================
    block_code = Column(String(20), nullable=False, index=True, comment="板块代码（东方财富板块ID）")
    block_name = Column(String(50), nullable=False, comment="板块名称")
    block_type = Column(String(20), nullable=False, comment="HY / GN")
    # =========================
    # 3. 行情事实
    # =========================
    # block_zs = Column(Float, nullable=True, comment="板块指数")
    block_zdf = Column(Float, nullable=True, comment="板块涨跌幅（%）")
    block_zde = Column(Float, nullable=True, comment="板块涨跌额")
    block_hsl = Column(Float, nullable=True, comment="板块换手率（%）")
    # =========================
    # 4. 板块结构
    # =========================
    up_count = Column(Integer, nullable=True, comment="上涨家数")
    pi_count = Column(Integer, nullable=True, comment="平盘家数")
    dw_count = Column(Integer, nullable=True, comment="下跌家数")


    # =========================
    # 5. 板块资金
    # =========================
    block_zl_inflow = Column(Float, nullable=True, comment="板块主力资金净流入")
    block_cd_inflow = Column(Float, nullable=True, comment="板块超大单资金净流入")
    block_dd_inflow = Column(Float, nullable=True, comment="板块大单资金净流入")
    block_zd_inflow = Column(Float, nullable=True, comment="板块中单资金净流入")
    block_xd_inflow = Column(Float, nullable=True, comment="板块小单资金净流入")

    block_zl_zb = Column(Float, nullable=True, comment="板块主力资金净流入占比")
    block_cd_zb = Column(Float, nullable=True, comment="板块超大单资金净流入占比")
    block_dd_zb = Column(Float, nullable=True, comment="板块大单资金净流入占比")
    block_zd_zb = Column(Float, nullable=True, comment="板块中单资金净流入占比")
    block_xd_zb = Column(Float, nullable=True, comment="板块小单资金净流入占比")

    # =========================
    # 6. 点名股票  板块领涨股 和 板块资金流入最多股 都是板块点名股
    # =========================
    money_stock_code  = Column(String(20), nullable=True, comment="板块资金流入最多个股代码")
    money_stock__name = Column(String(50), nullable=True, comment="板块资金流入最多个股名称")
    money_stock__type = Column(String(20), nullable=True, comment="板块资金流入最多个股所属市场1 沪 0 深")

    lider_stock_code  = Column(String(20), nullable=True, comment="板块领涨个股代码")
    lider_stock__name = Column(String(50), nullable=True, comment="板块领涨个股名称")
    lider_stock__pct  = Column(String(20), nullable=True, comment="板块领涨个股涨幅")
    lider_stock__type = Column(String(20), nullable=True, comment="板块领涨个股所属市场1 沪 0 深")








    # =========================
    # 6. 时间字段
    # =========================
    market_time = Column(DateTime, nullable=False, comment="市场时间：该板块状态对应的市场时间")
    add_time = Column(DateTime(timezone=True),nullable=False,default=lambda: datetime.now(timezone.utc),comment="入库时间")
    def __repr__(self):
        return f"<RawBlockSnapshotEvent "f"{self.block_name} "f"time={self.market_time}>"
