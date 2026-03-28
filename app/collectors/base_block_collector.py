# -*- coding: utf-8 -*-
"""
基础板块数据采集器

功能：从东方财富 API 采集板块基础信息，写入 base_block 表
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from typing import Dict, List

from app.utils.request_util import EastMoneyRequest
from app.models.base.base_block import BaseBlock
from app.db.session import get_db_context
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)


def _fetch_boards_by_type(board_type: str) -> List[Dict]:
    """
    按板块类型采集数据

    参数:
        board_type: "concept" 或 "industry"

    返回:
        [{"code": "BK0968", "name": "固态电池", "type": "GN"}, ...]
    """
    return EastMoneyRequest.get_blocks(board_type)


def collect_base_blocks() -> Dict[str, int]:
    """
    采集所有板块（概念 + 行业）并写入数据库

    返回:
        {"updated": 更新数, "inserted": 新增数, "total": 总数, "elapsed_seconds": 耗时}
    """
    start_time = time.time()
    logger.info("开始采集基础板块数据...")

    # 采集概念板块
    logger.info("采集 GN 概念板块...")
    boards_gn = _fetch_boards_by_type("concept")
    logger.info(f"GN 概念板块: {len(boards_gn)} 条")

    # 采集行业板块
    logger.info("采集 HY 行业板块...")
    boards_hy = _fetch_boards_by_type("industry")
    logger.info(f"HY 行业板块: {len(boards_hy)} 条")

    all_boards = boards_gn + boards_hy
    logger.info(f"接口返回共 {len(all_boards)} 条板块数据")

    if not all_boards:
        logger.warning("没有板块数据，跳过写入")
        return {"updated": 0, "inserted": 0, "total": 0, "elapsed_seconds": 0}

    # 查询现有记录
    with get_db_context() as db:
        existing_codes = {
            row.block_code
            for row in db.query(BaseBlock.block_code).all()
        }

    # 统计
    updated_count = sum(1 for b in all_boards if b["code"] in existing_codes)
    inserted_count = len(all_boards) - updated_count

    # Upsert 写入
    values = [
        {
            "block_code": board["code"],
            "block_name": board["name"],
            "block_type": board["type"],
            "block_stock_count": 0,
        }
        for board in all_boards
    ]

    with get_db_context() as db:
        try:
            stmt = insert(BaseBlock).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["block_code"],
                set_={
                    "block_name": stmt.excluded.block_name,
                    "block_type": stmt.excluded.block_type,
                }
            )
            db.execute(stmt)
            db.commit()
            logger.info("数据库写入成功")
        except Exception as e:
            db.rollback()
            logger.error(f"数据库写入失败: {e}")
            raise

    elapsed = time.time() - start_time
    logger.info(f"板块采集完成: 更新 {updated_count}, 新增 {inserted_count}, 耗时 {elapsed:.2f}s")

    return {
        "updated": updated_count,
        "inserted": inserted_count,
        "total": len(all_boards),
        "elapsed_seconds": round(elapsed, 2),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    collect_base_blocks()
