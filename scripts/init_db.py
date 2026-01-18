"""
数据库初始化脚本
"""



# 显式导入所有 Model（非常重要）
from app.models.raw import raw_block_huoyue,raw_stock_huoyue
from app.models.event import event_stock_consensus,event_capital_persistence,event_stock_dominance,event_block_start
from app.models.system import sys_market_state_date
from app.models.decision import decision_stock_daily,decision_open_validation

from app.db.session import engine
from app.db.base import Base

def init_db():
    """
    创建所有表
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("✅ 数据库表初始化完成")
