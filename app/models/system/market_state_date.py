"""
文件名：market_state_date.py
作用说明：
    股市开市休市时间表
"""
from sqlalchemy import (
    String,
    Integer,
    Date,
    Column,
)
from app.db.base import Base



class MarketStateDate(Base):
    """
    表名：market_state_date
    中文名：股市开市休市时间表
    """
    __tablename__ = "market_state_date"

    id = Column(Integer, primary_key=True, index=True, comment="自增主键")
    market_date   = Column(Date, nullable=True, comment="日期列表")
    market_week   = Column(String(20), nullable=True, comment="星期列表")
    market_state  = Column(Integer, nullable=True, comment="市场状态 0开市 1 休市")
    market_remark = Column(String(20), nullable=True, comment="节假日备注")
