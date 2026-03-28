# -*- coding: utf-8 -*-
"""
基础股票数据采集器

功能：从东方财富 API 采集股票基础信息，写入 base_stock 表
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from typing import Dict

from app.utils.request_util import EastMoneyRequest
from app.utils.stock_type import get_stock_type
from app.models.base.base_stock import BaseStock
from app.db.session import get_db_context
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _fetch_stocks_data() -> Dict[str, Dict]:
    """
    分页采集所有股票数据

    返回:
        {"000001": {"name": "平安银行", "exchange": "0", ...}, ...}
    """
    code_map: Dict[str, Dict] = {}
    page = 1

    while True:
        result = EastMoneyRequest.get_stocks(page, 100)
        if not result:
            break

        stocks = result.get("stocks", [])
        if not stocks:
            break

        for item in stocks:
            stock_code = item.get("f12")
            stock_name = item.get("f14")
            stock_short = item.get("f152", "")
            exchange = str(item.get("f13", ""))

            if stock_code and stock_name:
                # 判断风险状态
                short_str = str(stock_short) if stock_short else ""
                is_st = short_str.startswith("*ST") or short_str.startswith("ST")
                risk = 0 if is_st else 1

                # 判断板块类型
                stock_type = get_stock_type(stock_code, exchange)

                # secid
                secid = f"{exchange}.{stock_code}"

                code_map[stock_code] = {
                    "name": stock_name,
                    "exchange": exchange,
                    "secid": secid,
                    "type": stock_type,
                    "risk": risk,
                }

        if len(stocks) < 100:
            break
        page += 1

    return code_map


def collect_base_stocks() -> Dict[str, int]:
    """
    采集所有股票并写入数据库

    返回:
        {"updated": 更新数, "inserted": 新增数, "total": 总数, "elapsed_seconds": 耗时}
    """
    start_time = time.time()
    logger.info("开始采集基础股票数据...")

    code_map = _fetch_stocks_data()
    logger.info(f"接口返回 {len(code_map)} 条股票数据")

    if not code_map:
        logger.warning("没有股票数据，跳过写入")
        return {"updated": 0, "inserted": 0, "total": 0, "elapsed_seconds": 0}

    # 查询现有记录
    with get_db_context() as db:
        existing_codes = {
            row.stock_code
            for row in db.query(BaseStock.stock_code).all()
        }

    updated_count = sum(1 for code in code_map if code in existing_codes)
    inserted_count = len(code_map) - updated_count

    # Upsert 写入
    values = [
        {
            "stock_code": code,
            "stock_name": info["name"],
            "exchange": info["exchange"],
            "secid": info["secid"],
            "stock_type": info["type"],
            "stock_risk": info["risk"],
            "stock_imp": 0,
            "pdate_time": datetime.now(timezone.utc),
        }
        for code, info in code_map.items()
    ]

    with get_db_context() as db:
        try:
            stmt = insert(BaseStock).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_code"],
                set_={
                    "stock_name": stmt.excluded.stock_name,
                    "exchange": stmt.excluded.exchange,
                    "secid": stmt.excluded.secid,
                    "stock_type": stmt.excluded.stock_type,
                    "stock_risk": stmt.excluded.stock_risk,
                    "pdate_time": stmt.excluded.pdate_time,
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
    logger.info(f"股票采集完成: 更新 {updated_count}, 新增 {inserted_count}, 耗时 {elapsed:.2f}s")

    return {
        "updated": updated_count,
        "inserted": inserted_count,
        "total": len(code_map),
        "elapsed_seconds": round(elapsed, 2),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    collect_base_stocks()
