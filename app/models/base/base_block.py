"""
文件路径：app/models/base/base_block.py
作用说明：板块基础信息表

设计结构（按用户要求）：
- id: 唯一编号（自增）
- block_code: 板块代码
- block_name: 板块名称
- block_type: 板块类型（HY=行业, GN=概念）
- block_stock_count: 板块内股票总数
- update_time: 更新时间
"""
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime, timezone
from app.db.base import Base


class BaseBlock(Base):
    """
    表名：base_block
    中文名：板块基础信息表
    
    列说明：
    - id: 唯一编号
    - block_code: 板块代码（东方财富板块ID，唯一）
    - block_name: 板块名称
    - block_type: 板块类型（HY=行业板块，GN=概念板块）
    - block_stock_count: 板块内股票总数
    - update_time: 更新时间
    """
    __tablename__ = "base_block"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="唯一编号")

    # 板块身份
    block_code = Column(String(20), unique=True, nullable=False, index=True, comment="板块代码")
    block_name = Column(String(100), nullable=False, comment="板块名称")
    block_type = Column(String(10), nullable=False, index=True, comment="HY=行业板块，GN=概念板块")

    # 板块统计
    block_stock_count = Column(Integer, nullable=True, default=0, comment="板块内股票总数")

    # 更新时间
    update_time = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间"
    )

    def __repr__(self):
        return f"<BaseBlock code={self.block_code} name={self.block_name} type={self.block_type}>"
