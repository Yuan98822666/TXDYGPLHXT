import sys; sys.path.insert(0, '.')
from app.db.session import get_db_context
from app.models.base.base_stock import BaseStock
with get_db_context() as db:
    rows = db.query(BaseStock).limit(10).all()
    for r in rows:
        t = r.stock_type
        print('type repr:', repr(t), 'len:', len(t), 'bytes:', [hex(b) for b in t.encode('utf-8')])
