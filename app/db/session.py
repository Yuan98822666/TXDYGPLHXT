"""
文件名：session.py
作用说明：SQLAlchemy Engine 与 Session 工厂

核心功能：
- 创建数据库引擎（Engine）
- 配置连接池参数
- 提供线程安全的会话工厂（SessionLocal）

设计要点：
- 引擎配置来自全局 settings
- 连接池优化数据库连接复用
- 会话工厂配置为非自动提交/非自动刷新模式

组件说明：

1. engine:
   - 数据库连接的核心对象
   - 管理底层 DBAPI 连接池
   - 处理 SQL 语句的编译和执行

2. SessionLocal:
   - 会话工厂，用于创建数据库会话实例
   - autocommit=False: 禁用自动提交，需要显式调用 commit()
   - autoflush=False: 禁用自动刷新，需要显式调用 flush()
   - 这种配置提供更好的事务控制粒度

配置参数来源：
- database_url: 来自 settings.database_url
- DB_ECHO: 来自 settings.DB_ECHO（是否输出 SQL 日志）
- DB_POOL_SIZE: 来自 settings.DB_POOL_SIZE（连接池大小）
- DB_MAX_OVERFLOW: 来自 settings.DB_MAX_OVERFLOW（溢出连接数）

使用模式：
在业务代码中：
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # 数据库操作...
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings
from contextlib import contextmanager

# 创建数据库引擎
# 配置说明：
# - echo: 是否输出 SQL 语句到日志（调试用）
# - pool_size: 连接池中保持的连接数
# - max_overflow: 超出 pool_size 后允许创建的额外连接数
# - future=True: 使用 SQLAlchemy 2.0 风格 API
engine = create_engine(settings.database_url, echo=settings.DB_ECHO, pool_size=settings.DB_POOL_SIZE,max_overflow=settings.DB_MAX_OVERFLOW, future=True, )

# 创建会话工厂
# 配置说明：
# - autocommit=False: 禁用自动提交，需要显式 commit()
# - autoflush=False: 禁用自动刷新，需要显式 flush()
# 这种配置提供更精细的事务控制
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, )


def get_db():
    """
    FastAPI 依赖项函数：用于路由中注入数据库会话。

    使用方式:
        @app.get("/xxx")
        def read_data(db: Session = Depends(get_db)):
            ...

    注意: 此函数返回一个生成器，FastAPI 自动处理 yield 前后逻辑。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    上下文管理器：用于非 FastAPI 环境（如调度器、脚本）中安全获取数据库会话。

    使用方式:
        with get_db_context() as db:
            db.query(...)

    特点:
        - 自动 commit/rollback 由调用方控制（此处仅提供会话）
        - 自动关闭连接，防止连接泄漏
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()