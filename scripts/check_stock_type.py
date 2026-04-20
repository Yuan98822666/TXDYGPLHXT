"""检查 stock_type 字段分布"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import get_db_context
from app.models.base.base_stock import BaseStock
from sqlalchemy import func

with get_db_context() as db:
    result = db.query(
        BaseStock.stock_type,
        func.count(BaseStock.stock_code).label('count')
    ).group_by(BaseStock.stock_type).all()

    # 写入文件避免编码问题
    with open('stock_type_dist.txt', 'w', encoding='utf-8') as f:
        f.write('stock_type 分布:\n')
        for row in result:
            f.write(f'  {row.stock_type!r}: {row.count}\n')
    print('已写入 stock_type_dist.txt')
