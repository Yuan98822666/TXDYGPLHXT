# -*- coding: utf-8 -*-
"""检查数据库数据"""
from app.db.session import SessionLocal
from app.models.raw.raw_min_block import RawMinBlock
from app.models.base.base_block import BaseBlock
from datetime import date

db = SessionLocal()
try:
    # 检查4月2日 raw_min_block 数据
    blocks = db.query(RawMinBlock).filter(
        RawMinBlock.trade_date == date(2026, 4, 2)
    ).count()
    print(f'raw_min_block 4月2日总记录数: {blocks}')
    
    # 查看最新批次
    latest = db.query(RawMinBlock).filter(
        RawMinBlock.trade_date == date(2026, 4, 2)
    ).order_by(RawMinBlock.raw_no.desc()).first()
    
    if latest:
        print(f'最新批次号: {latest.raw_no}')
        latest_count = db.query(RawMinBlock).filter(
            RawMinBlock.trade_date == date(2026, 4, 2), 
            RawMinBlock.raw_no == latest.raw_no
        ).count()
        print(f'最新批次记录数: {latest_count}')
        print(f'样本数据: code={latest.block_code}, name={latest.block_name}, zl_inflow={latest.block_zl_inflow}')
        
        # 检查板块类型分布（通过关联 base_block）
        from sqlalchemy import func
        from app.models.base.base_block import BaseBlock
        
        # 获取该批次所有板块代码
        block_codes = db.query(RawMinBlock.block_code).filter(
            RawMinBlock.trade_date == date(2026, 4, 2),
            RawMinBlock.raw_no == latest.raw_no
        ).distinct().all()
        block_codes = [b[0] for b in block_codes]
        print(f'该批次板块数量: {len(block_codes)}')
        
        # 关联 base_block 查看类型分布
        type_dist = db.query(
            BaseBlock.block_type, 
            func.count(BaseBlock.id)
        ).filter(
            BaseBlock.block_code.in_(block_codes)
        ).group_by(BaseBlock.block_type).all()
        print(f'板块类型分布: {type_dist}')
    else:
        print('无数据')
        
    # 检查 base_block 表
    base_count = db.query(BaseBlock).count()
    print(f'base_block 总记录数: {base_count}')
    
finally:
    db.close()
