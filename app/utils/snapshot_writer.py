# app/writers/snapshot_writer.py
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from typing import List

def write_block_and_stock_snapshots(block_list: List[RawBlockHuoyue], stock_list: List[RawStockHuoyue]):
    db: Session = SessionLocal()
    try:
        # 批量插入（SQLAlchemy 支持 bulk_save_objects）
        if block_list:
            db.bulk_save_objects(block_list)
        if stock_list:
            db.bulk_save_objects(stock_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()