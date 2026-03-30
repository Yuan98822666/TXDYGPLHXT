# -*- coding: utf-8 -*-
"""
日K数据采集器

功能：从 raw_min_* 快照表获取收盘时刻数据，复制到 raw_day_* 表
入库规则：每日收盘后（15:00后）执行，复制当天最后一笔快照数据
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from datetime import datetime, date
from typing import Dict

from sqlalchemy import func
from app.utils.trade_calendar import get_latest_trade_day
from app.models.raw import RawMinStock, RawMinBlock, RawDayStock, RawDayBlock
from app.db.session import get_db_context

logger = logging.getLogger(__name__)


class DayCollector:
    """日K数据采集器"""

    @classmethod
    def collect_stock_day(cls) -> Dict:
        """
        采集股票日K数据

        从 raw_min_stock 复制当天最后一笔快照数据到 raw_day_stock
        """
        start_time = time.time()
        trade_date = get_latest_trade_day()

        # 检查是否已收盘（15:00后）
        now = datetime.now().time()
        is_after_close = now.hour >= 15 or (now.hour == 14 and now.minute >= 55)

        if not is_after_close:
            return {
                "status": "skipped",
                "message": "未到收盘时间，跳过采集",
                "count": 0,
                "elapsed_seconds": 0,
            }

        with get_db_context() as db:
            # 查询当天最后一笔快照数据（按 snapshot_time 降序）
            subquery = (
                db.query(
                    RawMinStock.stock_code,
                    func.max(RawMinStock.snapshot_time).label("max_time")
                )
                .filter(RawMinStock.trade_date == trade_date)
                .group_by(RawMinStock.stock_code)
                .subquery()
            )

            # 获取每只股票的最新快照数据
            last_snapshots = (
                db.query(RawMinStock)
                .join(
                    subquery,
                    (RawMinStock.stock_code == subquery.c.stock_code)
                    & (RawMinStock.snapshot_time == subquery.c.max_time)
                )
                .filter(RawMinStock.trade_date == trade_date)
                .all()
            )

            if not last_snapshots:
                return {
                    "status": "success",
                    "message": "无快照数据",
                    "count": 0,
                    "elapsed_seconds": time.time() - start_time,
                }

            # 删除旧数据
            db.query(RawDayStock).filter(RawDayStock.trade_date == trade_date).delete()
            db.commit()

            # 复制到日K表
            day_records = []
            for snapshot in last_snapshots:
                record = RawDayStock(
                    stock_code=snapshot.stock_code,
                    raw_no=snapshot.raw_no,
                    trade_date=trade_date,
                    stock_zsj=snapshot.stock_zsj,
                    stock_kpj=snapshot.stock_kpj,
                    stock_zgj=snapshot.stock_zgj,
                    stock_zdj=snapshot.stock_zdj,
                    stock_spj=snapshot.stock_spj,
                    stock_ztj=snapshot.stock_ztj,
                    stock_dtj=snapshot.stock_dtj,
                    stock_cjl=snapshot.stock_cjl,
                    stock_cje=snapshot.stock_cje,
                    stock_zdf=snapshot.stock_zdf,
                    stock_zf=snapshot.stock_zf,
                    stock_zde=snapshot.stock_zde,
                    stock_hsl=snapshot.stock_hsl,
                    stock_sjhsl=snapshot.stock_sjhsl,
                    stock_syl=snapshot.stock_syl,
                    stock_sjl=snapshot.stock_sjl,
                    stock_zsz=snapshot.stock_zsz,
                    stock_ltsz=snapshot.stock_ltsz,
                    stock_ltg=snapshot.stock_ltg,
                    stock_ztzt=snapshot.stock_ztzt,
                    stock_zl_inflow=snapshot.stock_zl_inflow,
                    stock_cd_inflow=snapshot.stock_cd_inflow,
                    stock_dd_inflow=snapshot.stock_dd_inflow,
                    stock_zd_inflow=snapshot.stock_zd_inflow,
                    stock_xd_inflow=snapshot.stock_xd_inflow,
                    stock_zl_zb=snapshot.stock_zl_zb,
                    stock_cd_zb=snapshot.stock_cd_zb,
                    stock_dd_zb=snapshot.stock_dd_zb,
                    stock_zd_zb=snapshot.stock_zd_zb,
                    stock_xd_zb=snapshot.stock_xd_zb,
                )
                day_records.append(record)

            db.bulk_save_objects(day_records)
            db.commit()

        elapsed = time.time() - start_time
        logger.info(f"股票日K采集完成: {len(day_records)} 条, 耗时 {elapsed:.2f}s")

        return {
            "status": "success",
            "message": "股票日K采集完成",
            "count": len(day_records),
            "trade_date": str(trade_date),
            "elapsed_seconds": round(elapsed, 2),
        }

    @classmethod
    def collect_block_day(cls) -> Dict:
        """
        采集板块日K数据

        从 raw_min_block 复制当天最后一笔快照数据到 raw_day_block
        """
        start_time = time.time()
        trade_date = get_latest_trade_day()

        # 检查是否已收盘
        now = datetime.now().time()
        is_after_close = now.hour >= 15 or (now.hour == 14 and now.minute >= 55)

        if not is_after_close:
            return {
                "status": "skipped",
                "message": "未到收盘时间，跳过采集",
                "count": 0,
                "elapsed_seconds": 0,
            }

        with get_db_context() as db:
            # 查询当天最后一笔快照数据
            subquery = (
                db.query(
                    RawMinBlock.block_code,
                    func.max(RawMinBlock.snapshot_time).label("max_time")
                )
                .filter(RawMinBlock.trade_date == trade_date)
                .group_by(RawMinBlock.block_code)
                .subquery()
            )

            # 获取每个板块的最新快照数据
            last_snapshots = (
                db.query(RawMinBlock)
                .join(
                    subquery,
                    (RawMinBlock.block_code == subquery.c.block_code)
                    & (RawMinBlock.snapshot_time == subquery.c.max_time)
                )
                .filter(RawMinBlock.trade_date == trade_date)
                .all()
            )

            if not last_snapshots:
                return {
                    "status": "success",
                    "message": "无快照数据",
                    "count": 0,
                    "elapsed_seconds": time.time() - start_time,
                }

            # 删除旧数据
            db.query(RawDayBlock).filter(RawDayBlock.trade_date == trade_date).delete()
            db.commit()

            # 复制到日K表
            day_records = []
            for snapshot in last_snapshots:
                record = RawDayBlock(
                    block_code=snapshot.block_code,
                    block_name=snapshot.block_name,
                    raw_no=snapshot.raw_no,
                    trade_date=trade_date,
                    block_zs=snapshot.block_zs,
                    block_ltg=snapshot.block_ltg,
                    block_stock_count=snapshot.block_stock_count,
                    block_zdf=snapshot.block_zdf,
                    block_lb=snapshot.block_lb,
                    block_hsl=snapshot.block_hsl,
                    stock_cjls=snapshot.stock_cjls,
                    block_up_stock=snapshot.block_up_stock,
                    block_pi_stock=snapshot.block_pi_stock,
                    block_dw_stock=snapshot.block_dw_stock,
                    block_zl_inflow=snapshot.block_zl_inflow,
                    block_cd_inflow=snapshot.block_cd_inflow,
                    block_dd_inflow=snapshot.block_dd_inflow,
                    block_zd_inflow=snapshot.block_zd_inflow,
                    block_xd_inflow=snapshot.block_xd_inflow,
                    block_zl_zb=snapshot.block_zl_zb,
                    block_cd_zb=snapshot.block_cd_zb,
                    block_dd_zb=snapshot.block_dd_zb,
                    block_zd_zb=snapshot.block_zd_zb,
                    block_xd_zb=snapshot.block_xd_zb,
                    leader_stock_code=snapshot.leader_stock_code,
                    leader_stock_name=snapshot.leader_stock_name,
                    leader_stock_zdf=snapshot.leader_stock_zdf,
                    money_stock_code=snapshot.money_stock_code,
                    money_stock_name=snapshot.money_stock_name,
                )
                day_records.append(record)

            db.bulk_save_objects(day_records)
            db.commit()

        elapsed = time.time() - start_time
        logger.info(f"板块日K采集完成: {len(day_records)} 条, 耗时 {elapsed:.2f}s")

        return {
            "status": "success",
            "message": "板块日K采集完成",
            "count": len(day_records),
            "trade_date": str(trade_date),
            "elapsed_seconds": round(elapsed, 2),
        }

    @classmethod
    def collect_all(cls) -> Dict:
        """采集所有日K数据"""
        stock_result = cls.collect_stock_day()
        block_result = cls.collect_block_day()

        return {
            "stock": stock_result,
            "block": block_result,
            "total_stock": stock_result.get("count", 0),
            "total_block": block_result.get("count", 0),
        }


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=== 日K数据采集测试 ===\n")
    result = DayCollector.collect_all()
    print(json.dumps(result, ensure_ascii=False, indent=2))
