"""
快照数据批量写入器

功能说明：
- 提供统一的快照数据持久化接口
- 支持板块快照和个股快照的批量插入
- 使用 SQLAlchemy 的 bulk_save_objects 提升写入性能
- 包含完整的事务管理和异常回滚机制

数据模型依赖：
- RawBlockHuoyue: 板块活跃度原始数据模型
- RawStockHuoyue: 个股活跃度原始数据模型

设计特点：
- 批量操作：减少数据库交互次数，提升性能
- 事务安全：写入失败时自动回滚，保证数据一致性
- 资源管理：确保数据库连接正确关闭
"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from typing import List


def write_block_and_stock_snapshots(
        block_list: List[RawBlockHuoyue],
        stock_list: List[RawStockHuoyue]
):
    """
    批量写入板块和个股快照数据到数据库

    参数:
        block_list (List[RawBlockHuoyue]): 板块快照对象列表
        stock_list (List[RawStockHuoyue]): 个股快照对象列表

    功能流程:
        1. 获取数据库会话
        2. 开启事务
        3. 批量插入板块数据（如果列表非空）
        4. 批量插入个股数据（如果列表非空）
        5. 提交事务
        6. 异常时回滚事务并重新抛出异常
        7. 确保数据库连接最终关闭

    性能优化:
        - 使用 bulk_save_objects 进行批量插入
        - 避免逐条插入的性能开销
        - 单次事务包含所有相关数据，保证原子性

    异常处理:
        - 任何数据库操作异常都会触发事务回滚
        - 重新抛出原始异常，便于上层处理
    """
    db: Session = SessionLocal()
    try:
        # 批量插入（SQLAlchemy 支持 bulk_save_objects）
        if block_list:
            db.bulk_save_objects(block_list)
        if stock_list:
            db.bulk_save_objects(stock_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()