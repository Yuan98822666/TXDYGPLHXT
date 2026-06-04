#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件路径：scripts/calculate_factors.py
作用说明：因子计算执行脚本

使用方法:
    python scripts/calculate_factors.py --raw-no 20250602103000
    python scripts/calculate_factors.py --latest          # 计算最新批次
    python scripts/calculate_factors.py --date 2025-06-02 # 计算指定日期所有批次
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from datetime import datetime, date

from app.collectors.factor_calculator import FactorCalculator
from app.db.session import get_db_context

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_by_raw_no(raw_no: str):
    """计算指定批次的因子"""
    logger.info(f"开始计算批次 {raw_no} 的因子")
    result = FactorCalculator.calculate_for_raw_no(raw_no)
    logger.info(f"计算完成: {result}")
    return result


def calculate_latest():
    """计算最新批次的因子"""
    from app.models.raw.raw_min_stock import RawMinStock

    with get_db_context() as db:
        # 查询最新的批次号
        latest = db.query(RawMinStock).order_by(RawMinStock.raw_no.desc()).first()
        if not latest:
            logger.error("数据库中无股票数据")
            return None

        raw_no = latest.raw_no
        logger.info(f"最新批次号: {raw_no}")

    return calculate_by_raw_no(raw_no)


def calculate_by_date(trade_date: date):
    """计算指定日期的所有批次"""
    from app.models.raw.raw_min_stock import RawMinStock
    from sqlalchemy import func

    with get_db_context() as db:
        # 查询该日期所有批次
        raw_nos = db.query(RawMinStock.raw_no).filter(
            func.date(RawMinStock.trade_date) == trade_date
        ).distinct().order_by(RawMinStock.raw_no).all()

        raw_nos = [r[0] for r in raw_nos]

        if not raw_nos:
            logger.error(f"日期 {trade_date} 无数据")
            return []

        logger.info(f"日期 {trade_date} 共有 {len(raw_nos)} 个批次需要计算")

    results = []
    for raw_no in raw_nos:
        try:
            result = calculate_by_raw_no(raw_no)
            results.append(result)
        except Exception as e:
            logger.error(f"批次 {raw_no} 计算失败: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="因子计算工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--raw-no", help="指定批次号，如 20250602103000")
    group.add_argument("--latest", action="store_true", help="计算最新批次")
    group.add_argument("--date", help="指定日期，如 2025-06-02")

    args = parser.parse_args()

    if args.raw_no:
        result = calculate_by_raw_no(args.raw_no)
        print(f"\n计算结果:\n{result}")

    elif args.latest:
        result = calculate_latest()
        if result:
            print(f"\n计算结果:\n{result}")

    elif args.date:
        trade_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        results = calculate_by_date(trade_date)
        print(f"\n共计算 {len(results)} 个批次")
        for r in results:
            print(f"  - {r}")


if __name__ == "__main__":
    main()
