"""
文件名：session.py
作用说明：
    SQLAlchemy Engine 与 Session 工厂
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings

engine = create_engine(settings.database_url, echo=settings.DB_ECHO, pool_size=settings.DB_POOL_SIZE,max_overflow=settings.DB_MAX_OVERFLOW, future=True, )

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, )


