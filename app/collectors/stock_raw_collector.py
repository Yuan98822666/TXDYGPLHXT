# -*- coding: utf-8 -*-
"""
股票快照采集器

功能：采集 stock_imp=1 的股票快照数据，写入 raw_min_stock 表
     同时检查 raw_day_stock 表，无当日数据则插入

stock_type 实际值： 上证所主板/深交所主板/创业板/科创板
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Set

from app.utils.request_util import EastMoneyRequest
from app.utils.batch_no import generate_batch_no
from app.utils.trade_calendar import get_latest_trade_day
from app.utils.stock_calculator import StockCalculator
from app.models.raw.raw_min_stock import RawMinStock
from app.models.raw.raw_day_stock import RawDayStock
from app.models.base.base_stock import BaseStock
from app.db.session import get_db_context
from app.config.runtime_config import get_runtime_config

logger = logging.getLogger(__name__)


def get_collector_config():
    """获取运行时配置"""
    runtime = get_runtime_config()
    return {
        "max_workers": runtime.get_stock_max_workers(),
        "batch_size": runtime.get_stock_batch_size(),
        "batch_delay": runtime.get_stock_batch_delay(),
    }


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
        """
        标记涨停/炸板/跌停股票为关注

        全部标记，不限制板块类型
        只标记 stock_imp == 0 的（去重）
        """
        if not stock_codes:
            return
        
        with get_db_context() as db:
            # 只更新未标记的（去重）
            updated_count = db.query(BaseStock).filter(
                BaseStock.stock_code.in_(stock_codes),
                BaseStock.stock_imp == 0,
            ).update({"stock_imp": 1}, synchronize_session=False)
            db.commit()
            logger.info(f"标记涨停/炸板/跌停股为关注: {updated_count} 只")

    @classmethod
    def _ensure_day_records(cls, db, results: List[Dict], trade_date, raw_no: str):
        """
        检查 raw_day_stock 表，无当日数据则插入
        
        参数:
            db: 数据库会话
            results: 本次采集的结果列表
            trade_date: 交易日期
            raw_no: 批次号
        """
        if not results:
            return
        
        # 提取本次采集的股票代码
        stock_codes = {r["stock_code"] for r in results}
        
        # 查询 day 表中已存在的股票（只查本次涉及的）
        existing = {
            row[0] for row in db.query(RawDayStock.stock_code).filter(
                RawDayStock.trade_date == trade_date,
                RawDayStock.stock_code.in_(stock_codes)
            ).all()
        }
        
        # 找出需要插入的股票
        new_codes = stock_codes - existing
        if not new_codes:
            return
        
        # 从 results 中获取需要插入的数据
        new_records = []
        for r in results:
            if r["stock_code"] in new_codes:
                record = RawDayStock(
                    stock_code=r["stock_code"],
                    raw_no=raw_no,
                    trade_date=trade_date,
                    stock_zsj=r.get("stock_zsj"),
                    stock_kpj=r.get("stock_kpj"),
                    stock_zgj=r.get("stock_zgj"),
                    stock_zdj=r.get("stock_zdj"),
                    stock_spj=r.get("stock_spj"),
                    stock_ztj=r.get("stock_ztj"),
                    stock_dtj=r.get("stock_dtj"),
                    stock_cjl=r.get("stock_cjl"),
                    stock_cje=r.get("stock_cje"),
                    stock_zdf=r.get("stock_zdf"),
                    stock_zf=r.get("stock_zf"),
                    stock_zde=r.get("stock_zde"),
                    stock_hsl=r.get("stock_hsl"),
                    stock_sjhsl=r.get("stock_sjhsl"),
                    stock_syl=r.get("stock_syl"),
                    stock_sjl=r.get("stock_sjl"),
                    stock_zsz=r.get("stock_zsz"),
                    stock_ltsz=r.get("stock_ltsz"),
                    stock_ltg=r.get("stock_ltg"),
                    stock_ztzt=r.get("stock_ztzt", 0),
                    stock_zl_inflow=r.get("stock_zl_inflow"),
                    stock_cd_inflow=r.get("stock_cd_inflow"),
                    stock_dd_inflow=r.get("stock_dd_inflow"),
                    stock_zd_inflow=r.get("stock_zd_inflow"),
                    stock_xd_inflow=r.get("stock_xd_inflow"),
                    stock_zl_zb=r.get("stock_zl_zb"),
                    stock_cd_zb=r.get("stock_cd_zb"),
                    stock_dd_zb=r.get("stock_dd_zb"),
                    stock_zd_zb=r.get("stock_zd_zb"),
                    stock_xd_zb=r.get("stock_xd_zb"),
                    notes=[],
                    score=None,
                )
                new_records.append(record)
        
        if new_records:
            db.bulk_save_objects(new_records)
            db.commit()
            logger.info(f"日K表新增: {len(new_records)} 只股票（{trade_date}）")

    @classmethod
    def collect(cls, raw_no: str = None, trade_date: str = None, snapshot_time: datetime = None) -> Dict:
        """采集股票快照
        
        参数:
            raw_no: 批次号，如果为None则自动生成
            trade_date: 交易日期，如果为None则根据raw_no或自动生成
            snapshot_time: 采集时间戳，如果为None则根据raw_no或自动生成
        """
        start_time = time.time()

        # 如果未提供批次号，则生成新的
        if raw_no is None:
            raw_no, trade_date, snapshot_time = generate_batch_no()

        # 获取涨停/炸板/跌停状态
        ztzt_map = cls._get_ztzt_status()

        # 自动标记涨停/炸板/跌停股票为关注
        if ztzt_map:
            cls._mark_pool_stocks_as_imp(set(ztzt_map.keys()))

        # 获取需要采集的股票列表
        # 查询数据库里总共有多少只关注股，同时获取列表
        # 过滤掉 skip_until 未过期的股票
        now_utc = datetime.utcnow()
        with get_db_context() as db:
            imp_stocks = db.query(BaseStock).filter(
                BaseStock.stock_imp == 1,
                (BaseStock.skip_until.is_(None)) | (BaseStock.skip_until <= now_utc)
            ).all()
            # 统计被跳过的股票数量
            skipped_count = db.query(BaseStock).filter(
                BaseStock.stock_imp == 1,
                BaseStock.skip_until.isnot(None),
                BaseStock.skip_until > now_utc
            ).count()
            total_imp_count = len(imp_stocks) + skipped_count

        if skipped_count > 0:
            logger.info(f"跳过采集: {skipped_count} 只股票（在 skip_until 期内）")

        pool_stocks = cls._get_pool_stocks()

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

        logger.info(f"关注股票总数: {total_imp_count} 只（数据库），本次采集 {len(all_stocks)} 只（去重后）")

        # 多线程采集（并发数由运行时配置控制，每批间隔避免触发限流）
        results = []
        failed_stocks = []  # 记录失败的股票，用于重试
        
        # 获取运行时配置
        config = get_collector_config()
        max_workers = config["max_workers"]
        batch_size = config["batch_size"]
        batch_delay = config["batch_delay"]
        
        logger.info(f"开始采集，配置: 线程={max_workers}, 批次={batch_size}, 间隔={batch_delay}s")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            
            for i in range(0, len(all_stocks), batch_size):
                batch = all_stocks[i:i + batch_size]
                futures = {
                    executor.submit(cls._fetch_one_stock, stock, ztzt_map): stock
                    for stock in batch
                }
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
                    else:
                        failed_stocks.append(futures[future])
                
                # 批次间隔（平衡速度与限流）
                if i + batch_size < len(all_stocks):
                    time.sleep(batch_delay)
                    fail_count = len([s for s in batch if s in failed_stocks])
                    success_count = len(batch) - fail_count
                    logger.info(f"已采集 {min(i + batch_size, len(all_stocks))}/{len(all_stocks)} 只 (成功 {success_count}, 失败 {fail_count})")

        # 重试失败的股票
        if failed_stocks:
            logger.warning(f"第一轮失败 {len(failed_stocks)} 只，开始重试...")
            retry_results = []
            for stock in failed_stocks:
                result = cls._fetch_one_stock(stock, ztzt_map)
                if result:
                    retry_results.append(result)
                time.sleep(0.3)  # 重试间隔
            
            results.extend(retry_results)
            logger.info(f"重试完成：成功 {len(retry_results)}/{len(failed_stocks)} 只")

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
                
                # 入库后检查 day 表，无当日数据则插入
                cls._ensure_day_records(db, results, trade_date, raw_no)
            except Exception as e:
                db.rollback()
                logger.error(f"入库失败: {e}")
                success = 0

        elapsed = time.time() - start_time
        logger.info(f"股票快照采集完成: {success}/{total_imp_count} 只（入库/关注总数）, {len(all_stocks)} 只（本次去重）, 耗时 {elapsed:.2f}s")

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
