"""
文件路径：app/models/base/base_block_stock_lnk.py
作用说明：板块成分股关联表 ORM 模型

表设计说明：
  - 记录每个板块与其成分股的多对多关系
  - 约 30 万条数据，主键使用 BigInteger
  - block_name 为冗余字段，查询时无需 JOIN base_block 表
  - (block_code, stock_code) 联合唯一，防止重复写入

索引设计：
  - idx_lnk_block_code : 按板块查成分股（高频）
  - idx_lnk_stock_code : 按股票查所属板块（高频）
"""
from sqlalchemy import Column, String, BigInteger, DateTime, UniqueConstraint, Index
from datetime import datetime, timezone
from app.db.base import Base


class BaseBlockStockLnk(Base):
    """
    表名：base_block_stock_lnk
    中文名：板块成分股关联表

    列说明：
    - id         : 主键ID，自增，无业务含义（BigInteger，数据量约30万条）
    - block_code : 板块代码，关联 base_block.block_code，如 BK0428
    - block_name : 板块名称（冗余字段），方便查询时无需 JOIN base_block 表
    - stock_code : 股票代码，关联 base_stock.stock_code，如 300317
    - update_time: 数据最后更新时间（UTC时区）
    """
    __tablename__ = "base_block_stock_lnk"

    # 主键（BigInteger，因关联数据量较大，约30万条）
    id = Column(BigInteger, primary_key=True, autoincrement=True,
                comment="主键ID，自增，无业务含义；使用 BigInteger 因关联数据量较大（约 30 万条）")

    # 板块信息
    block_code = Column(String(20), nullable=False, index=True,
                        comment="板块代码，关联 base_block.block_code，如 BK0428")
    block_name = Column(String(100), nullable=False,
                        comment="板块名称（冗余字段），方便查询时无需 JOIN base_block 表，如 电子元件")

    # 股票信息
    stock_code = Column(String(20), nullable=False, index=True,
                        comment="股票代码，关联 base_stock.stock_code，如 300317")

    # 更新时间
    update_time = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="数据最后更新时间（UTC时区）"
    )

    # 联合唯一约束：同一板块内同一股票只能有一条记录
    __table_args__ = (
        UniqueConstraint("block_code", "stock_code", name="uq_block_stock"),
    )

    def __repr__(self):
        return (
            f"<BaseBlockStockLnk "
            f"block={self.block_code}({self.block_name}) "
            f"stock={self.stock_code}>"
        )
