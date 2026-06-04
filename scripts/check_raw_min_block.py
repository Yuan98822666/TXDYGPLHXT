# -*- coding: utf-8 -*-
"""检查 raw_min_block 表结构"""
from app.db.session import SessionLocal
from app.models.raw.raw_min_block import RawMinBlock
from datetime import date
from sqlalchemy import desc

db = SessionLocal()
try:
    # 检查4月2日 raw_min_block 中是否有 stock_code 字段
    latest = db.query(RawMinBlock).filter(
        RawMinBlock.trade_date == date(2026, 4, 2)
    ).order_by(desc(RawMinBlock.raw_no)).first()
    
    if latest:
        print(f'Latest raw_no: {latest.raw_no}')
        # 检查是否有股票相关字段
        cols = [c.name for c in latest.__table__.columns]
        print(f'RawMinBlock columns: {cols}')
        
        # 检查是否有股票相关字段
        stock_fields = ['stock_price', 'stock_change_percent', 'stock_zl_inflow', 'stock_code']
        for f in stock_fields:
            has_field = hasattr(latest, f)
            print(f'Has {f}: {has_field}')
    else:
        print('No data found')
finally:
    db.close()
