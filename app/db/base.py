"""
所有 ORM Model 的 Declarative Base

功能说明：
- 提供 SQLAlchemy 声明式映射的基类
- 所有数据模型都应继承此类
- 实现自动表名推断和基础元数据管理

设计原理：
- declarative_base() 创建一个基类，包含：
  * 元数据容器（MetaData）
  * 映射注册表
  * 自动表名生成规则
- 统一基类便于后续扩展（如添加通用方法、混入类等）

使用方式：
在模型文件中：
    from app.db.base import Base
    class MyModel(Base):
        __tablename__ = "my_table"
        # 字段定义...

最佳实践：
- 所有模型必须继承此 Base 类
- 避免直接使用 sqlalchemy.ext.declarative.declarative_base()
- 便于统一管理和迁移操作
"""

from sqlalchemy.ext.declarative import declarative_base

# 创建声明式基类实例
# 此基类将被所有 ORM 模型继承
Base = declarative_base()