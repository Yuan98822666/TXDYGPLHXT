"""
文件路径：app/models/base/base_stock.py
作用说明：基础股票信息表 ORM 模型

设计结构：
- id            : 唯一编号（自增）
- stock_code    : 股票代码（唯一）
- stock_name    : 股票名称
- exchange      : 交易所标识（0=深市, 1=沪市）
- secid         : 东方财富格式标识（exchange.code，如 0.000001）
- stock_type    : 股票上市板块类型
- stock_risk    : 风险警示状态（0=有风险, 1=正常）
- stock_imp     : 自选股标记（0=未添加, 1=已添加）
- pdate_time    : 数据更新时间
"""
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime, timezone
from app.db.base import Base


class BaseStock(Base):
    """
    表名：base_stock
    中文名：基础股票信息表

    列说明：
    - id            : 唯一编号（自增）
    - stock_code    : 股票代码（6位数字，唯一）
    - stock_name    : 股票名称
    - exchange      : 交易所标识（0=深市, 1=沪市）
    - secid         : 东方财富格式标识（f13.code，如 0.000001、1.600519）
                      用于拼接东方财富个股接口 URL
    - stock_type    : 股票上市板块类型（SH_ZB/SZ_ZB/KCB/CYB/BJS）
    - stock_risk    : 风险警示状态（0=有风险ST/*ST/退市, 1=正常）
    - stock_imp     : 自选股标记（0=未添加, 1=已添加，用户手动维护）
    - pdate_time    : 数据更新时间（UTC时区）
    """
    __tablename__ = "base_stock"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID，自增，无业务含义")

    # 股票身份
    stock_code = Column(String(20), unique=True, nullable=False, index=True, comment="股票代码，6位数字")
    stock_name = Column(String(100), nullable=False, comment="股票名称")
    exchange = Column(String(10), nullable=False, index=True, comment="交易所标识：0=深京市，1=沪市")
    secid = Column(String(30), unique=True, nullable=False, index=True, comment="东方财富格式标识，格式：exchange.stock_code，如 0.000001")

    # 板块类型、风险、自选
    stock_type = Column(String(20), nullable=False, index=True, comment="股票上市板块类型")
    stock_risk = Column(Integer, nullable=False, default=1, index=True, comment="风险状态：0=有风险, 1=正常")
    stock_imp = Column(Integer, nullable=False, default=0, index=True, comment="自选标记：0=未添加, 1=已添加")

    # 更新时间
    pdate_time = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="数据更新时间（UTC时区）"
    )

    def __repr__(self):
        return f"<BaseStock code={self.stock_code} name={self.stock_name} secid={self.secid} risk={self.stock_risk}>"
