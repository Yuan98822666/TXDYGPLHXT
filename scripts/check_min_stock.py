# -*- coding: utf-8 -*-
"""检查 raw_min_stock 表数据"""
from app.db.session import SessionLocal
from app.models.raw.raw_min_stock import RawMinStock
from datetime import date
from sqlalchemy import desc, func

db = SessionLocal()
try:
    # 检查4月2日 raw_min_stock 数据
    count = db.query(RawMinStock).filter(
        RawMinStock.trade_date == date(2026, 4, 2)
    ).count()
    print(f'raw_min_stock 4月2日总记录数: {count}')
    
    # 查看最新批次
    latest = db.query(RawMinStock).filter(
        RawMinStock.trade_date == date(2026, 4, 2)
    ).order_by(desc(RawMinStock.raw_no)).first()
    
    if latest:
        print(f'最新批次号: {latest.raw_no}')
        latest_count = db.query(RawMinStock).filter(
            RawMinStock.trade_date == date(2026, 4, 2), 
            RawMinStock.raw_no == latest.raw_no
        ).count()
        print(f'最新批次记录数: {latest_count}')
        print(f'样本数据: code={latest.stock_code}, price={latest.stock_spj}, zdf={latest.stock_zdf}, zl_inflow={latest.stock_zl_inflow}')
    else:
        print('无数据')
finally:
    db.close()
