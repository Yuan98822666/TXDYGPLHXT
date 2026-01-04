"""
数据库初始化脚本
"""

from app.db.session import engine
from app.db.base import Base

# 显式导入所有 Model（非常重要）


def init_db():
    """
    创建所有表
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("✅ 数据库表初始化完成")
