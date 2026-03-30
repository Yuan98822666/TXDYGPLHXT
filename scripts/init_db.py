"""
数据库初始化脚本
"""



# 显式导入所有 Model（非常重要）


from app.db.session import engine
from app.db.base import Base


from app.models.system import sys_market_state_date
from app.models.raw import  raw_min_stock,raw_day_stock,raw_day_block,raw_min_block
from app.models.base import  base_stock,base_block
from app.models.special import special_dt,special_qs,special_zb,special_zt,special_zrzt



def init_db():
    """
    创建所有表
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("✅ 数据库表初始化完成")
