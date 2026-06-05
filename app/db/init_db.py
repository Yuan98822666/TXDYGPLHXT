# -*- coding: utf-8 -*-
"""
数据库初始化模块

功能：
- 自动创建所有 SQLAlchemy 模型对应的表
- 在应用启动时调用，确保表结构存在

使用方式：
    from app.db.init_db import init_db
    init_db()  # 在应用启动时调用

注意事项：
- 不会删除已有表，只会创建不存在的表
- 不会修改已有表的结构（需使用 Alembic 迁移）
- 生产环境建议使用 Alembic 管理表结构变更
"""
import logging

from app.db.base import Base
from app.db.session import engine

# 导入所有模型，确保它们注册到 Base.metadata
# 这行至关重要！没有它，Base 不知道有哪些表要创建
from app.models import *  # noqa: F401, F403

logger = logging.getLogger(__name__)


def init_db():
    """
    初始化数据库，创建所有不存在的表
    
    流程：
    1. 导入所有模型（确保注册到 Base.metadata）
    2. 调用 create_all() 创建缺失的表
    3. 记录创建的表名
    """
    try:
        # 获取当前已存在的表（避免重复创建）
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        # 获取 SQLAlchemy 知道的所有表
        all_tables = set(Base.metadata.tables.keys())
        
        # 计算需要创建的表
        tables_to_create = all_tables - existing_tables
        
        if tables_to_create:
            logger.info(f"检测到 {len(tables_to_create)} 个待创建表: {sorted(tables_to_create)}")
            # 创建所有表（只创建不存在的）
            Base.metadata.create_all(bind=engine)
            logger.info(f"数据库表创建完成，共 {len(all_tables)} 个表")
        else:
            logger.info(f"所有表已存在，无需创建（共 {len(all_tables)} 个表）")
            
        # 列出所有表
        logger.debug(f"数据库表清单: {sorted(all_tables)}")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def get_table_stats():
    """
    获取数据库表统计信息
    
    Returns:
        dict: 包含表数量和表名列表
    """
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    return {
        "total_tables": len(tables),
        "tables": sorted(tables),
        "sqlalchemy_registered": sorted(Base.metadata.tables.keys()),
    }
