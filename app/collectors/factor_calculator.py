# -*- coding: utf-8 -*-
"""
文件路径：app/collectors/factor_calculator.py
作用说明：因子计算任务

功能清单：
- 计算板块受重视程度因子
- 计算个股-板块共振因子（涨停潜力因子、受重视程度因子）
- 标记领涨股、资金流入最多股、共振状态
- 日级汇总个股强度因子

执行方式:
    每次 raw_min_stock 和 raw_min_block 采集完成后自动触发
    或手动执行: python scripts/calculate_factors.py --raw-no 20250602103000
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, date
from typing import List, Dict, Optional
from decimal import Decimal
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models.raw.raw_min_stock import RawMinStock
from app.models.raw.raw_min_block import RawMinBlock
from app.models.base.base_block_stock_lnk import BaseBlockStockLnk
from app.models.analysis.analysis_block_stock_resonance import AnalysisBlockStockResonance
from app.models.analysis.analysis_stock_strength import AnalysisStockStrength

logger = logging.getLogger(__name__)


class FactorCalculator:
    """因子计算器"""

    @classmethod
    def calculate_for_raw_no(cls, stock_raw_no: str = None, block_raw_no: str = None, db: Session = None) -> Dict:
        """
        计算指定批次的所有因子

        Args:
            stock_raw_no: 股票批次号，如 "20250602103000"
            block_raw_no: 板块批次号，如 "20250602103000"（可与股票批次不同）
            db: 数据库会话（可选，用于事务控制）

        Returns:
            计算结果统计
        """
        close_db = False
        if db is None:
            db = get_db_context().__enter__()
            close_db = True

        try:
            # 如果没有指定批次号，查找最新的匹配批次
            if stock_raw_no is None or block_raw_no is None:
                stock_raw_no, block_raw_no = cls._find_matching_raw_nos(db, stock_raw_no)
            
            logger.info(f"开始计算因子，股票批次: {stock_raw_no}, 板块批次: {block_raw_no}")

            # 1. 计算板块受重视程度因子
            block_importance_map = cls._calculate_block_importance(block_raw_no, db)
            logger.info(f"板块受重视程度因子计算完成，共 {len(block_importance_map)} 个板块")

            # 2. 计算个股-板块共振因子
            resonance_count = cls._calculate_resonance_factors(stock_raw_no, block_raw_no, block_importance_map, db)
            logger.info(f"个股-板块共振因子计算完成，共 {resonance_count} 条记录")

            # 3. 日级汇总个股强度因子
            trade_date = datetime.strptime(stock_raw_no[:8], "%Y%m%d").date()
            strength_count = cls._calculate_stock_strength(trade_date, db)
            logger.info(f"个股强度因子计算完成，共 {strength_count} 只股票")

            result = {
                "stock_raw_no": stock_raw_no,
                "block_raw_no": block_raw_no,
                "trade_date": trade_date.isoformat(),
                "block_count": len(block_importance_map),
                "resonance_count": resonance_count,
                "strength_count": strength_count,
                "success": True
            }

            logger.info(f"因子计算完成: {result}")
            return result

        except Exception as e:
            logger.error(f"因子计算失败: {e}", exc_info=True)
            raise
        finally:
            if close_db:
                db.close()

    @classmethod
    def _calculate_block_importance(cls, raw_no: str, db: Session) -> Dict[str, Decimal]:
        """
        计算板块受重视程度因子

        公式: 板块受重视程度因子 = 板块主力资金净流入 / 所有板块主力资金净流入总和

        Returns:
            {block_code: block_importance_factor}
        """
        # 查询同批次所有板块数据
        blocks = db.query(RawMinBlock).filter(RawMinBlock.raw_no == raw_no).all()

        if not blocks:
            logger.warning(f"批次 {raw_no} 无板块数据")
            return {}

        # 计算总流入（只计算净流入为正的板块）
        total_inflow = sum(b.block_zl_inflow for b in blocks if b.block_zl_inflow and b.block_zl_inflow > 0)

        if total_inflow == 0:
            logger.warning(f"批次 {raw_no} 板块总流入为0")
            return {}

        # 计算每个板块的受重视程度因子
        block_importance_map = {}
        for block in blocks:
            if block.block_zl_inflow and block.block_zl_inflow > 0:
                factor = Decimal(block.block_zl_inflow) / Decimal(total_inflow)
                block_importance_map[block.block_code] = factor
            else:
                block_importance_map[block.block_code] = Decimal(0)

        return block_importance_map

    @classmethod
    def _find_matching_raw_nos(cls, db: Session, prefer_stock_raw_no: str = None) -> tuple:
        """
        查找匹配的股票和板块批次号
        
        由于股票和板块采集时间可能有几秒差异，需要找到最接近的匹配批次
        """
        if prefer_stock_raw_no:
            # 使用指定的股票批次，找最接近的板块批次
            stock_raw_no = prefer_stock_raw_no
            stock_time = datetime.strptime(stock_raw_no, "%Y%m%d%H%M%S")
            
            # 查找同一日期内的板块批次
            date_prefix = stock_raw_no[:8]
            block_raws = db.query(RawMinBlock.raw_no).filter(
                RawMinBlock.raw_no.like(f"{date_prefix}%")
            ).distinct().order_by(RawMinBlock.raw_no).all()
            
            if not block_raws:
                raise ValueError(f"日期 {date_prefix} 无板块数据")
            
            # 找时间最接近的
            closest_block_raw = None
            min_diff = float('inf')
            for (block_raw,) in block_raws:
                block_time = datetime.strptime(block_raw, "%Y%m%d%H%M%S")
                diff = abs((block_time - stock_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_block_raw = block_raw
            
            return stock_raw_no, closest_block_raw
        else:
            # 找最新的匹配批次
            latest_stock = db.query(RawMinStock).order_by(RawMinStock.raw_no.desc()).first()
            if not latest_stock:
                raise ValueError("数据库中无股票数据")
            
            return cls._find_matching_raw_nos(db, latest_stock.raw_no)

    @classmethod
    def _calculate_resonance_factors(
        cls,
        stock_raw_no: str,
        block_raw_no: str,
        block_importance_map: Dict[str, Decimal],
        db: Session
    ) -> int:
        """
        计算个股-板块共振因子

        公式:
        - 涨停潜力因子 = 个股主力资金净流入 / 个股流通市值
        - 受重视程度因子 = 个股主力资金净流入 / 板块主力资金净流入
        """
        # 查询同批次所有个股数据
        stocks = db.query(RawMinStock).filter(RawMinStock.raw_no == stock_raw_no).all()

        if not stocks:
            logger.warning(f"批次 {stock_raw_no} 无个股数据")
            return 0

        # 构建股票代码到数据的映射
        stock_map = {s.stock_code: s for s in stocks}

        # 查询板块-股票关联关系
        stock_codes = list(stock_map.keys())
        links = db.query(BaseBlockStockLnk).filter(
            BaseBlockStockLnk.stock_code.in_(stock_codes)
        ).all()

        # 查询板块数据（用于判断领涨股和资金流入最多股）
        blocks = db.query(RawMinBlock).filter(RawMinBlock.raw_no == block_raw_no).all()
        block_map = {b.block_code: b for b in blocks}

        # 准备批量插入数据
        resonance_records = []
        trade_date = datetime.strptime(stock_raw_no[:8], "%Y%m%d").date()
        snapshot_time = datetime.strptime(stock_raw_no, "%Y%m%d%H%M%S")

        for link in links:
            stock_code = link.stock_code
            block_code = link.block_code

            stock = stock_map.get(stock_code)
            block = block_map.get(block_code)

            if not stock or not block:
                continue

            # 计算涨停潜力因子
            zt_potential_factor = Decimal(0)
            if stock.stock_ltsz and stock.stock_ltsz > 0:
                zt_potential_factor = Decimal(stock.stock_zl_inflow or 0) / Decimal(stock.stock_ltsz)

            # 计算受重视程度因子
            attention_factor = Decimal(0)
            if block.block_zl_inflow and block.block_zl_inflow != 0:
                attention_factor = Decimal(stock.stock_zl_inflow or 0) / Decimal(block.block_zl_inflow)

            # 获取板块受重视程度因子
            block_importance_factor = block_importance_map.get(block_code, Decimal(0))

            # 判断是否为领涨股
            is_leader = (block.leader_stock_code == stock_code)

            # 判断是否为资金流入最多股
            is_money_leader = (block.money_stock_code == stock_code)

            # 判断是否共振（同向流入）
            stock_inflow = stock.stock_zl_inflow or 0
            block_inflow = block.block_zl_inflow or 0
            is_resonance = (stock_inflow > 0 and block_inflow > 0) or (stock_inflow < 0 and block_inflow < 0)

            # 创建记录
            record = AnalysisBlockStockResonance(
                stock_code=stock_code,
                block_code=block_code,
                raw_no=stock_raw_no,
                trade_date=trade_date,
                snapshot_time=snapshot_time,
                stock_zl_inflow=stock.stock_zl_inflow,
                block_zl_inflow=block.block_zl_inflow,
                stock_ltsz=stock.stock_ltsz,
                zt_potential_factor=zt_potential_factor,
                attention_factor=attention_factor,
                block_importance_factor=block_importance_factor,
                is_leader=is_leader,
                is_money_leader=is_money_leader,
                is_resonance=is_resonance
            )
            resonance_records.append(record)

        # 批量插入（使用 upsert 避免重复）
        if resonance_records:
            from sqlalchemy.dialects.postgresql import insert

            for record in resonance_records:
                stmt = insert(AnalysisBlockStockResonance).values(
                    stock_code=record.stock_code,
                    block_code=record.block_code,
                    raw_no=record.raw_no,
                    trade_date=record.trade_date,
                    snapshot_time=record.snapshot_time,
                    stock_zl_inflow=record.stock_zl_inflow,
                    block_zl_inflow=record.block_zl_inflow,
                    stock_ltsz=record.stock_ltsz,
                    zt_potential_factor=record.zt_potential_factor,
                    attention_factor=record.attention_factor,
                    block_importance_factor=record.block_importance_factor,
                    is_leader=record.is_leader,
                    is_money_leader=record.is_money_leader,
                    is_resonance=record.is_resonance
                )
                # 冲突时更新
                stmt = stmt.on_conflict_do_update(
                    index_elements=['raw_no', 'stock_code', 'block_code'],
                    set_=dict(
                        trade_date=record.trade_date,
                        snapshot_time=record.snapshot_time,
                        stock_zl_inflow=record.stock_zl_inflow,
                        block_zl_inflow=record.block_zl_inflow,
                        stock_ltsz=record.stock_ltsz,
                        zt_potential_factor=record.zt_potential_factor,
                        attention_factor=record.attention_factor,
                        block_importance_factor=record.block_importance_factor,
                        is_leader=record.is_leader,
                        is_money_leader=record.is_money_leader,
                        is_resonance=record.is_resonance
                    )
                )
                db.execute(stmt)

            db.commit()

        return len(resonance_records)

    @classmethod
    def _calculate_stock_strength(cls, trade_date: date, db: Session) -> int:
        """
        计算个股强度因子（日级汇总）

        公式: 个股强度因子 = 领涨股出现次数 + 资金流入最多股出现次数
        """
        # 查询当日所有共振记录
        records = db.query(AnalysisBlockStockResonance).filter(
            AnalysisBlockStockResonance.trade_date == trade_date
        ).all()

        if not records:
            logger.warning(f"日期 {trade_date} 无共振数据")
            return 0

        # 按股票汇总
        stock_stats: Dict[str, Dict] = {}

        for record in records:
            code = record.stock_code

            if code not in stock_stats:
                stock_stats[code] = {
                    "leader_count": 0,
                    "money_leader_count": 0,
                    "total_blocks": 0,
                    "leader_blocks": [],
                    "money_leader_blocks": []
                }

            stats = stock_stats[code]
            stats["total_blocks"] += 1

            if record.is_leader:
                stats["leader_count"] += 1
                stats["leader_blocks"].append({
                    "block_code": record.block_code,
                    "block_name": None,  # 可从base_block查询
                    "count": 1
                })

            if record.is_money_leader:
                stats["money_leader_count"] += 1
                stats["money_leader_blocks"].append({
                    "block_code": record.block_code,
                    "block_name": None,
                    "count": 1
                })

        # 批量插入/更新
        from sqlalchemy.dialects.postgresql import insert

        count = 0
        for stock_code, stats in stock_stats.items():
            strength_factor = stats["leader_count"] + stats["money_leader_count"]

            stmt = insert(AnalysisStockStrength).values(
                stock_code=stock_code,
                trade_date=trade_date,
                leader_count=stats["leader_count"],
                money_leader_count=stats["money_leader_count"],
                total_blocks=stats["total_blocks"],
                strength_factor=strength_factor,
                leader_blocks=stats["leader_blocks"],
                money_leader_blocks=stats["money_leader_blocks"]
            )
            # 冲突时更新
            stmt = stmt.on_conflict_do_update(
                index_elements=['stock_code', 'trade_date'],
                set_=dict(
                    leader_count=stats["leader_count"],
                    money_leader_count=stats["money_leader_count"],
                    total_blocks=stats["total_blocks"],
                    strength_factor=strength_factor,
                    leader_blocks=stats["leader_blocks"],
                    money_leader_blocks=stats["money_leader_blocks"]
                )
            )
            db.execute(stmt)
            count += 1

        db.commit()
        return count


if __name__ == "__main__":
    # 测试
    import argparse

    parser = argparse.ArgumentParser(description="计算因子")
    parser.add_argument("--raw-no", required=True, help="批次号，如 20250602103000")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    result = FactorCalculator.calculate_for_raw_no(args.raw_no)
    print(f"计算结果: {result}")
