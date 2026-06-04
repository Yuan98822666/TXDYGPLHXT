# -*- coding: utf-8 -*-
"""检查 raw_min_block 表的时间分布"""
from app.db.session import SessionLocal
from app.models.raw.raw_min_block import RawMinBlock
from datetime import date
from sqlalchemy import func

db = SessionLocal()
try:
    # 获取4月2日所有不同的时间点
    times = db.query(
        func.date_trunc('minute', RawMinBlock.snapshot_time).label('time'),
        func.count(RawMinBlock.id).label('count')
    ).filter(
        RawMinBlock.trade_date == date(2026, 4, 2)
    ).group_by(
        func.date_trunc('minute', RawMinBlock.snapshot_time)
    ).order_by('time').all()
    
    print(f"Total unique times: {len(times)}")
    print("\nTime distribution:")
    for t, count in times:
        time_str = t.strftime("%H:%M")
        print(f"  {time_str}: {count} records")
finally:
    db.close()
