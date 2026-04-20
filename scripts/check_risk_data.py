"""检查 stock_risk 数据"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import get_db_context

with get_db_context() as db:
    # 查询有 ST 标记的股票
    st_stocks = db.execute(text("""
        SELECT stock_code, stock_name, stock_risk 
        FROM base_stock 
        WHERE stock_name LIKE '%ST%' OR stock_name LIKE '%%ST%%'
        LIMIT 10
    """)).fetchall()
    print('ST股票（名称含ST）:')
    for s in st_stocks:
        print(f'  {s[0]} {s[1]} -> stock_risk={s[2]}')
    
    print()
    # 查询 stock_risk=0 的股票
    risk0 = db.execute(text("""
        SELECT stock_code, stock_name, stock_risk 
        FROM base_stock 
        WHERE stock_risk = 0 
        LIMIT 10
    """)).fetchall()
    print('stock_risk=0 的股票:')
    for s in risk0:
        print(f'  {s[0]} {s[1]} -> stock_risk={s[2]}')
    
    print()
    # 查询 stock_risk=1 但名称含 ST 的股票
    mismatch = db.execute(text("""
        SELECT stock_code, stock_name, stock_risk 
        FROM base_stock 
        WHERE stock_risk = 1 AND (stock_name LIKE '%ST%' OR stock_name LIKE '%%ST%%')
        LIMIT 10
    """)).fetchall()
    print('stock_risk=1 但名称含ST的股票（数据问题）:')
    for s in mismatch:
        print(f'  {s[0]} {s[1]} -> stock_risk={s[2]}')
