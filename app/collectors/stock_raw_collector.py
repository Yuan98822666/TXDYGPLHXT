# -*- coding: utf-8 -*-
"""
股票快照采集器

功能：采集 stock_imp=1 的股票快照数据，写入 raw_min_stock 表
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from datetime import datetime
from typing import List, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.utils.request_util import EastMoneyRequest
from app.utils.batch_no import generate_batch_no
from app.utils.trade_calendar import get_latest_trade_day
from app.utils.stock_calculator import StockCalculator
from app.models.raw.raw_min_stock import RawMinStock
from app.models.base.base_stock import BaseStock
from app.db.session import get_db_context

logger = logging.getLogger(__name__)

MAX_WORKERS = 30  # 线程数


class StockRawCollector:
    """股票快照采集器"""

    @classmethod
    def _fetch_one_stock(cls, stock: Dict, ztzt_map: Dict[str, int]) -> Dict:
        """采集单只股票快照（线程任务）"""
        try:
            data = EastMoneyRequest.get_stock_raw(stock["secid"])
            if not data:
                return None

            # 获取价格数据
            spj = data.get("f43")
            zgj = data.get("f44")
            zdj = data.get("f45")
            zsj = data.get("f60")
            ztj = data.get("f51")
            dtj = data.get("f52")

            # 计算涨停状态
            stock_ztzt = ztzt_map.get(stock["stock_code"], 0)
            if stock_ztzt == 0:
                # 传入原始值（分），保证精度
                stock_ztzt = StockCalculator.calc_ztzt(
                    data.get("f43"), data.get("f44"), data.get("f51"), data.get("f52")
                )

            return {
                "stock_code": stock["stock_code"],
                "stock_zsj": zsj / 100 if zsj else None,
                "stock_kpj": data.get("f46") / 100 if data.get("f46") else None,
                "stock_zgj": zgj / 100 if zgj else None,
                "stock_zdj": zdj / 100 if zdj else None,
                "stock_spj": spj / 100 if spj else None,
                "stock_ztj": ztj / 100 if ztj else None,
                "stock_dtj": dtj / 100 if dtj else None,
                "stock_cjl": data.get("f47"),
                "stock_cje": data.get("f48"),
                "stock_zdf": data.get("f170") / 100 if data.get("f170") else None,
                "stock_zf": data.get("f171") / 100 if data.get("f171") else None,
                "stock_zde": data.get("f169") / 100 if data.get("f169") else None,
                "stock_hsl": data.get("f168") / 100 if data.get("f168") else None,
                "stock_sjhsl": StockCalculator.calc_sjhsl(data.get("f47"), data.get("f85")),
                "stock_syl": data.get("f162") / 100 if data.get("f162") else None,
                "stock_sjl": data.get("f167") / 100 if data.get("f167") else None,
                "stock_zsz": data.get("f116"),
                "stock_ltsz": data.get("f117"),
                "stock_ltg": data.get("f85"),
                "stock_ztzt": stock_ztzt,
                "stock_zl_inflow": data.get("f137"),
                "stock_cd_inflow": data.get("f140"),
                "stock_dd_inflow": data.get("f143"),
                "stock_zd_inflow": data.get("f146"),
                "stock_xd_inflow": data.get("f149"),
                "stock_zl_zb": data.get("f193") / 100 if data.get("f193") else None,
                "stock_cd_zb": data.get("f194") / 100 if data.get("f194") else None,
                "stock_dd_zb": data.get("f195") / 100 if data.get("f195") else None,
                "stock_zd_zb": data.get("f196") / 100 if data.get("f196") else None,
                "stock_xd_zb": data.get("f197") / 100 if data.get("f197") else None,
            }
        except Exception as e:
            logger.error(f"采集股票快照失败: {stock['stock_code']} - {e}")
            return None

    @classmethod
    def _get_pool_stocks(cls) -> List[Dict]:
        """获取涨停/炸板/跌停池中的股票"""
        trade_date = get_latest_trade_day()
        date_str = trade_date.strftime("%Y%m%d")

        zt_data = EastMoneyRequest.get_zt_pool(date_str)
        zb_data = EastMoneyRequest.get_zb_pool(date_str)
        dt_data = EastMoneyRequest.get_dt_pool(date_str)

        all_codes = set()
        all_codes.update(item.get("c") for item in zt_data if item.get("c"))
        all_codes.update(item.get("c") for item in zb_data if item.get("c"))
        all_codes.update(item.get("c") for item in dt_data if item.get("c"))

        if not all_codes:
            return []

        with get_db_context() as db:
            stocks = db.query(BaseStock).filter(
                BaseStock.stock_code.in_(all_codes)
            ).all()
            return [{"stock_code": s.stock_code, "secid": s.secid} for s in stocks]

    @classmethod
    def _get_ztzt_status(cls) -> Dict[str, int]:
        """获取涨停/炸板/跌停状态"""
        trade_date = get_latest_trade_day()
        date_str = trade_date.strftime("%Y%m%d")

        zt_data = EastMoneyRequest.get_zt_pool(date_str)
        zb_data = EastMoneyRequest.get_zb_pool(date_str)
        dt_data = EastMoneyRequest.get_dt_pool(date_str)

        status_map = {}
        for item in zt_data:
            if item.get("c"):
                status_map[item.get("c")] = 1
        for item in zb_data:
            if item.get("c"):
                status_map[item.get("c")] = 2
        for item in dt_data:
            if item.get("c"):
                status_map[item.get("c")] = 3
        return status_map

    @classmethod
    def _mark_pool_stocks_as_imp(cls, stock_codes: Set[str]):
        """标记特殊股票为关注"""
        if not stock_codes:
            return
        with get_db_context() as db:
            db.query(BaseStock).filter(
                BaseStock.stock_code.in_(stock_codes)
            ).update({"stock_imp": 1}, synchronize_session=False)
            db.commit()

    @classmethod
    def collect(cls) -> Dict:
        """采集股票快照"""
        start_time = time.time()

        # 生成批次号
        raw_no, trade_date, snapshot_time = generate_batch_no()

        # 获取涨停/炸板/跌停状态
        ztzt_map = cls._get_ztzt_status()

        # 自动标记涨停/炸板/跌停股票为关注
        if ztzt_map:
            cls._mark_pool_stocks_as_imp(set(ztzt_map.keys()))

        # 获取需要采集的股票列表
        pool_stocks = cls._get_pool_stocks()

        with get_db_context() as db:
            imp_stocks = db.query(BaseStock).filter(
                BaseStock.stock_imp == 1
            ).all()

        all_stocks = [
            {
                "stock_code": s.stock_code,
                "secid": s.secid,
            } for s in imp_stocks
        ]
        seen = set(s["stock_code"] for s in all_stocks)
        for ps in pool_stocks:
            if ps["stock_code"] not in seen:
                all_stocks.append(ps)
                seen.add(ps["stock_code"])

        logger.info(f"开始采集 {len(all_stocks)} 只股票快照")

        # 多线程采集
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(cls._fetch_one_stock, stock, ztzt_map): stock
                for stock in all_stocks
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        # 批量入库
        with get_db_context() as db:
            try:
                db.query(RawMinStock).filter(
                    RawMinStock.raw_no == raw_no
                ).delete()
                db.commit()

                for data in results:
                    data["raw_no"] = raw_no
                    data["snapshot_time"] = snapshot_time
                    data["trade_date"] = trade_date
                    db.add(RawMinStock(**data))
                db.commit()
                success = len(results)
            except Exception as e:
                db.rollback()
                logger.error(f"入库失败: {e}")
                success = 0

        elapsed = time.time() - start_time
        logger.info(f"股票快照采集完成: {success}/{len(all_stocks)} 条, 耗时 {elapsed:.2f}s")

        return {
            "total": len(all_stocks),
            "success": success,
            "elapsed_seconds": round(elapsed, 2),
        }


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=== 股票快照采集测试 ===")
    result = StockRawCollector.collect()
    print(json.dumps(result, ensure_ascii=False))
