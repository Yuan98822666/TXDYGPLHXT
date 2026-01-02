"""
Base 模块
作用：
    定义 SQLAlchemy Base、Engine 和 Session，供所有 ORM 和服务层使用
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# -----------------------------
# 数据库配置
# -----------------------------
# 这里以 SQLite 举例，你可根据实际换成 MySQL/Postgres
DATABASE_URL = "sqlite:///E:/Python Project/TXDYGPLHXT/db/txdygplhxt.db"

# -----------------------------
# 创建 Engine
# -----------------------------
engine = create_engine(
    DATABASE_URL,
    echo=False,         # 开启 SQL 输出调试可改 True
    connect_args={"check_same_thread": False}  # SQLite 特有
)

# -----------------------------
# 创建 Session 工厂
# -----------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# -----------------------------
# Base 声明基类
# -----------------------------
Base = declarative_base()
