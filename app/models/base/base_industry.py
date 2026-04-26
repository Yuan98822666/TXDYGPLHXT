# -*- coding: utf-8 -*-
"""
文件路径：app/models/base/base_industry.py
作用说明：申万三级行业分类表 ORM 模型

表设计说明：
  - 存储申万行业三级行业分类体系
  - 一级31种、二级128种、三级337种
  - 每级行业均有东财BK码，可关联 base_block 表
  - parent_code 形成层级关系

数据来源：
  - 用户桌面板块.txt文件
  - bk1/bk2/bk3 字段提供 行业名称 + BK码
  - baseinfo 字段提供 股票→三级行业映射

索引设计：
  - uq_industry_level_code : (level, industry_code) 联合唯一
  - idx_industry_parent    : 按父级查子级
  - idx_industry_bk        : 按东财BK码关联 base_block
"""
from sqlalchemy import Column, String, Integer, SmallInteger, DateTime, UniqueConstraint, Index
from datetime import datetime, timezone
from app.db.base import Base


class BaseIndustry(Base):
    """
    表名：base_industry
    中文名：申万三级行业分类表

    列说明：
    - id            : 主键ID，自增
    - level         : 行业层级（1=一级行业, 2=二级行业, 3=三级行业）
    - industry_code : 行业编码（如 L1_0, L2_12, L3_39），与 base_stock 中 sw_industry_l1/l2/l3 对应
    - industry_name : 行业名称（如 "银行", "银行Ⅱ", "股份制银行Ⅲ"）
    - em_bk_code    : 东方财富BK代码（如 BK1283），可关联 base_block.block_code
    - parent_code   : 父级行业编码（一级为NULL，二级指向一级，三级指向二级）
    - sort_order    : 排序序号（对应原数据中的ID顺序）
    - update_time   : 数据更新时间（UTC时区）
    """
    __tablename__ = "base_industry"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID，自增，无业务含义")

    # 行业层级与编码
    level = Column(SmallInteger, nullable=False, comment="行业层级：1=一级行业, 2=二级行业, 3=三级行业")
    industry_code = Column(String(20), nullable=False, comment="行业编码，如 L1_0, L2_12, L3_39")
    industry_name = Column(String(100), nullable=True, comment="行业名称，如 银行, 银行Ⅱ, 股份制银行Ⅲ")

    # 东方财富关联
    em_bk_code = Column(String(20), nullable=True, index=True, comment="东方财富BK代码，如 BK1283，可关联 base_block.block_code")

    # 层级关系
    parent_code = Column(String(20), nullable=True, index=True, comment="父级行业编码，一级为NULL")

    # 排序
    sort_order = Column(Integer, nullable=False, default=0, comment="排序序号，对应原数据中的ID顺序")

    # 更新时间
    update_time = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="数据更新时间（UTC时区）"
    )

    # 联合唯一约束：同一层级下行业编码唯一
    __table_args__ = (
        UniqueConstraint("level", "industry_code", name="uq_industry_level_code"),
    )

    def __repr__(self):
        return f"<BaseIndustry level={self.level} code={self.industry_code} name={self.industry_name}>"
