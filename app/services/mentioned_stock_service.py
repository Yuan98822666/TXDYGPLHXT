# app/services/mentioned_stock_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from app.models.raw.raw_stock_huoyue import RawStockHuoyue


class MentionedStockService:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_kz_no(self) -> Optional[int]:
        """获取最新的快照批次号"""
        result = self.db.query(RawBlockHuoyue.kz_no).order_by(RawBlockHuoyue.kz_no.desc()).first()
        return result[0] if result else None

    def get_mentioned_codes_from_blocks(self, kz_no: int) -> List[str]:
        """
        从板块表中提取所有被点名的股票代码（领涨股 + 资金流入最多股）
        UNION ALL 逻辑通过 Python 实现（避免复杂子查询）
        """
        blocks = self.db.query(RawBlockHuoyue).filter(RawBlockHuoyue.kz_no == kz_no).all()

        codes = []
        for block in blocks:
            if block.lider_stock_code:
                codes.append(block.lider_stock_code)
            if block.money_stock_code:
                codes.append(block.money_stock_code)
        return codes

    def get_stock_snapshots_by_codes(self, kz_no: int, stock_codes: List[str]) -> List[RawStockHuoyue]:
        """批量获取个股快照"""
        return self.db.query(RawStockHuoyue).filter(RawStockHuoyue.kz_no == kz_no,RawStockHuoyue.stock_code.in_(stock_codes)).all()