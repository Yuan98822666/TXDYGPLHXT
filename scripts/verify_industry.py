# -*- coding: utf-8 -*-
"""验证行业数据导入结果"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    # 1. 行业数据
    for lv in [1, 2, 3]:
        cnt = db.execute(text('SELECT COUNT(*) FROM base_industry WHERE level = :lv'), {'lv': lv}).scalar()
        print(f'base_industry level={lv}: {cnt} 条')
    
    # 2. 股票覆盖率
    total = db.execute(text('SELECT COUNT(*) FROM base_stock')).scalar()
    with_l3 = db.execute(text('SELECT COUNT(*) FROM base_stock WHERE sw_industry_l3 IS NOT NULL')).scalar()
    no_l3 = total - with_l3
    print(f'\nbase_stock 总数: {total}')
    print(f'有三级行业: {with_l3} ({with_l3*100/total:.1f}%)')
    print(f'无三级行业: {no_l3}')
    
    # 3. 哪些股票没有行业
    if no_l3 > 0:
        print('\n无行业分类的股票:')
        rows = db.execute(text('SELECT stock_code, stock_name FROM base_stock WHERE sw_industry_l3 IS NULL')).fetchall()
        for r in rows:
            print(f'  {r[0]} {r[1]}')
    
    # 4. 银行业树示例
    print('\n行业树示例（银行）:')
    rows = db.execute(
        text("SELECT level, industry_code, industry_name, em_bk_code, parent_code "
             "FROM base_industry WHERE industry_name LIKE :name "
             "ORDER BY level, sort_order"),
        {'name': '%银行%'}
    ).fetchall()
    for r in rows:
        indent = '  ' * (r[0])
        print(f'{indent}{r[1]} -> {r[2]} ({r[3]}, parent={r[4]})')
    
    # 5. 层级完整性
    orphan2 = db.execute(text('SELECT COUNT(*) FROM base_industry WHERE level=2 AND parent_code IS NULL')).scalar()
    orphan3 = db.execute(text('SELECT COUNT(*) FROM base_industry WHERE level=3 AND parent_code IS NULL')).scalar()
    print(f'\n二级无parent: {orphan2}')
    print(f'三级无parent: {orphan3}')
    
    # 6. 板块.txt中不在base_stock的股票
    print('\n板块.txt中有但base_stock中无的（11条）:')
    import json
    with open(r'C:\Users\Yuan9\Desktop\板块.txt', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    existing_codes = set(
        r[0] for r in db.execute(text('SELECT stock_code FROM base_stock')).fetchall()
    )
    
    missing = []
    for line in data['baseinfo']:
        parts = line.strip(',').split('|')
        if len(parts) >= 6:
            code = parts[5]
            name = parts[3]
            l1, l2, l3 = parts[0], parts[1], parts[2]
            if code not in existing_codes:
                missing.append((code, name, f'L1_{l1}/L2_{l2}/L3_{l3}'))
    
    for code, name, industry in missing:
        print(f'  {code} {name} ({industry})')

finally:
    db.close()
