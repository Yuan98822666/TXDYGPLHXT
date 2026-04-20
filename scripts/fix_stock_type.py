"""修复 stock_type 字段：中文 -> 英文代码"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import get_db_context
from app.models.base.base_stock import BaseStock

# 映射关系
TYPE_MAP = {
    '上证主板': 'SH_ZB',
    '深圳主板': 'SH_ZB',  # 原代码写反了，沪市主板被标记为"深圳主板"
    '科创板': 'KCB',
    '创业板': 'CYB',
    '北交所': 'BJS',
}

with get_db_context() as db:
    updated = 0
    for old_type, new_type in TYPE_MAP.items():
        result = db.query(BaseStock).filter(BaseStock.stock_type == old_type).update(
            {BaseStock.stock_type: new_type},
            synchronize_session=False
        )
        updated += result
        print(f'{old_type} -> {new_type}: {result} 条')

    db.commit()
    print(f'\n总计更新: {updated} 条')

    # 验证
    from sqlalchemy import func
    result = db.query(
        BaseStock.stock_type,
        func.count(BaseStock.stock_code).label('count')
    ).group_by(BaseStock.stock_type).all()

    print('\n修复后分布:')
    for row in result:
        print(f'  {row.stock_type!r}: {row.count}')
