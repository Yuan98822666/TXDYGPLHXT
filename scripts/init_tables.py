# -*- coding: utf-8 -*-
"""
数据库表初始化脚本

功能：创建所有表（包括 v0.2.0 新增的四张快照表）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.db.base import Base
from app.models.base import BaseBlock, BaseStock, BaseBlockStockLnk
from app.models.raw import RawMinStock, RawDayStock, RawMinBlock, RawDayBlock
from app.models.system import sys_market_state_date


def init_tables():
    """创建所有表"""
    print("开始创建数据库表...")

    # 导入所有模型，确保 Base.metadata 包含所有表定义
    models = [
        BaseBlock,
        BaseStock,
        BaseBlockStockLnk,
        RawMinStock,
        RawDayStock,
        RawMinBlock,
        RawDayBlock,
    ]

    print(f"将创建 {len(models)} 张表：")
    for model in models:
        print(f"  - {model.__tablename__}")

    # 创建表
    Base.metadata.create_all(bind=engine)

    print("\n[OK] 数据库表创建完成！")


if __name__ == "__main__":
    init_tables()
