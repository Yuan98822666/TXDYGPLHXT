"""
数据库会话模块
作用：
    提供 SQLAlchemy 会话工厂 SessionLocal 以及 Base
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite 示例，可换成 MySQL/Postgres
DATABASE_URL = "sqlite:///E:/Python Project/TXDYGPLHXT/db/txdygplhxt.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}  # SQLite 特有
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
