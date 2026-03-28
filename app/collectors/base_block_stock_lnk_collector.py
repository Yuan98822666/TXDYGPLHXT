# -*- coding: utf-8 -*-
"""
板块成分股采集器

功能：采集板块成分股关联数据，写入 base_block_stock_lnk 表

使用方式：
    from app.collectors.base_block_stock_lnk_collector import BaseBlockStockLnkCollector
    
    # 采集单个板块
    codes = BaseBlockStockLnkCollector.collect_block_stocks("BK0968", "固态电池")
    
    # 批量采集
    results = BaseBlockStockLnkCollector.collect_blocks([
        {"code": "BK0968", "name": "固态电池"},
        {"code": "BK0988", "name": "钠离子电池"},
    ])
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from typing import List, Dict

from app.utils.request_util import EastMoneyRequest

logger = logging.getLogger(__name__)


class BaseBlockStockLnkCollector:
    """板块成分股采集器"""

    @classmethod
    def collect_block_stocks(cls, block_code: str, block_name: str = "") -> List[str]:
        """
        采集单个板块全部成分股

        参数:
            block_code: 板块代码（如 BK0968）
            block_name: 板块名称（用于日志）

        返回:
            股票代码列表
        """
        all_codes = []
        page = 1

        while True:
            result = EastMoneyRequest.get_block_stocks(block_code, page, 100)
            if not result:
                if page == 1:
                    logger.warning(f"[{block_code}] {block_name} FAIL")
                break

            codes = result["codes"]
            if not codes:
                break

            all_codes.extend(codes)
            logger.debug(f"[{block_code}] page {page}: +{len(codes)}")

            if len(codes) < 100:
                break

            page += 1
            time.sleep(0.3)

        if all_codes:
            logger.info(f"[{block_code}] {block_name} -> {len(all_codes)}")
        return all_codes

    @classmethod
    def collect_blocks(cls, blocks: List[Dict]) -> Dict[str, List[str]]:
        """
        批量采集多个板块的成分股

        参数:
            blocks: [{"code": "BK0968", "name": "固态电池"}, ...]

        返回:
            {"BK0968": ["300750", ...], ...}
        """
        results = {}
        for b in blocks:
            codes = cls.collect_block_stocks(b["code"], b.get("name", ""))
            results[b["code"]] = codes
            time.sleep(0.3)
        return results


def collect_base_block_stock_lnk() -> Dict[str, int]:
    """
    采集所有板块的成分股关联数据（入口函数）
    
    流程：
        1. 从 base_block 表读取所有板块
        2. 逐个采集成分股
        3. 写入 base_block_stock_lnk 表
    
    返回:
        {"total_blocks": 板块数, "total_stocks": 成分股总数, "elapsed_seconds": 耗时}
    """
    import time
    from app.db.session import get_db_context
    from app.models.base.base_block import BaseBlock
    from app.models.base.base_block_stock_lnk import BaseBlockStockLnk
    from sqlalchemy.dialects.postgresql import insert
    
    start_time = time.time()
    logger.info("开始采集板块成分股关联数据...")
    
    # 读取所有板块
    with get_db_context() as db:
        blocks = db.query(BaseBlock).all()
    
    if not blocks:
        logger.warning("base_block 表为空，请先采集板块数据")
        return {"total_blocks": 0, "total_stocks": 0, "elapsed_seconds": 0}
    
    logger.info(f"共 {len(blocks)} 个板块待采集")
    
    total_stocks = 0
    success_count = 0
    
    for i, block in enumerate(blocks):
        codes = BaseBlockStockLnkCollector.collect_block_stocks(
            block.block_code, 
            block.block_name
        )
        
        if codes:
            success_count += 1
            total_stocks += len(codes)
            
            # 写入数据库
            with get_db_context() as db:
                # 先删除该板块的旧数据
                db.query(BaseBlockStockLnk).filter(
                    BaseBlockStockLnk.block_code == block.block_code
                ).delete()
                
                # 批量插入新数据
                values = [
                    {
                        "block_code": block.block_code,
                        "block_name": block.block_name,
                        "stock_code": code,
                    }
                    for code in codes
                ]
                if values:
                    db.execute(insert(BaseBlockStockLnk).values(values))
                    db.commit()
        
        # 进度日志
        if (i + 1) % 50 == 0:
            logger.info(f"进度: {i + 1}/{len(blocks)}, 成功: {success_count}")
        
        time.sleep(0.3)
    
    elapsed = time.time() - start_time
    logger.info(f"完成! 成功: {success_count}/{len(blocks)}, 成分股总数: {total_stocks}, 耗时: {elapsed:.1f}s")
    
    return {
        "total_blocks": len(blocks),
        "success_blocks": success_count,
        "total_stocks": total_stocks,
        "elapsed_seconds": round(elapsed, 2),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # 测试
    test = [("BK0968", "固态电池"), ("BK0988", "钠离子电池")]
    for code, name in test:
        codes = BaseBlockStockLnkCollector.collect_block_stocks(code, name)
        print(f"[{code}] {len(codes)} 只: {codes[:5]}")


def update_feng_ge_blocks(block_codes: List[str] = None) -> Dict[str, int]:
    """
    手动更新风格板块（block_type='FG'）的成分股
    
    参数:
        block_codes: 指定要更新的板块代码列表，如 ["BK0001", "BK0002"]
                    如果为空，则更新所有 block_type='FG' 的板块
    
    返回:
        {"updated_blocks": 更新板块数, "total_stocks": 成分股总数, "elapsed_seconds": 耗时}
    """
    import time
    from app.db.session import get_db_context
    from app.models.base.base_block import BaseBlock
    from app.models.base.base_block_stock_lnk import BaseBlockStockLnk
    from sqlalchemy.dialects.postgresql import insert
    
    start_time = time.time()
    logger.info("开始更新风格板块（block_type='FG'）成分股...")
    
    # 确定要更新的板块
    with get_db_context() as db:
        if block_codes:
            # 指定板块
            blocks = db.query(BaseBlock).filter(
                BaseBlock.block_code.in_(block_codes)
            ).all()
            logger.info(f"指定更新 {len(block_codes)} 个板块")
        else:
            # 所有风格板块（block_type='FG'）
            blocks = db.query(BaseBlock).filter(
                BaseBlock.block_type == 'FG'
            ).all()
            logger.info(f"更新所有风格板块（block_type='FG'），共 {len(blocks)} 个")
    
    if not blocks:
        logger.warning("没有找到要更新的板块")
        return {"updated_blocks": 0, "total_stocks": 0, "elapsed_seconds": 0}
    
    total_stocks = 0
    updated_count = 0
    
    for i, block in enumerate(blocks):
        codes = BaseBlockStockLnkCollector.collect_block_stocks(
            block.block_code,
            block.block_name
        )
        
        if codes:
            updated_count += 1
            total_stocks += len(codes)
            
            # 删除旧数据并插入新数据
            with get_db_context() as db:
                db.query(BaseBlockStockLnk).filter(
                    BaseBlockStockLnk.block_code == block.block_code
                ).delete()
                
                values = [
                    {
                        "block_code": block.block_code,
                        "block_name": block.block_name,
                        "stock_code": code,
                    }
                    for code in codes
                ]
                if values:
                    db.execute(insert(BaseBlockStockLnk).values(values))
                    db.commit()
        
        # 进度日志
        if (i + 1) % 10 == 0:
            logger.info(f"进度: {i + 1}/{len(blocks)}, 已更新: {updated_count}")
        
        time.sleep(0.3)
    
    elapsed = time.time() - start_time
    logger.info(f"风格板块更新完成! 更新: {updated_count}/{len(blocks)}, 成分股总数: {total_stocks}, 耗时: {elapsed:.1f}s")
    
    return {
        "updated_blocks": updated_count,
        "total_stocks": total_stocks,
        "elapsed_seconds": round(elapsed, 2),
    }

