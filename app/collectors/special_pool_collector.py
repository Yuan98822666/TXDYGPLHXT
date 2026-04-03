# -*- coding: utf-8 -*-
"""
特殊股票池采集器

功能：采集涨停池、昨日涨停池、强势股池、炸板池、跌停池数据
入库规则：删除当天数据，重新插入，同时更新 base_stock.stock_imp = 1
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from datetime import date, datetime, timezone
from typing import Dict, List

from sqlalchemy.dialects.postgresql import insert
from app.utils.request_util import EastMoneyRequest
from app.utils.trade_calendar import get_latest_trade_day, get_prev_trade_day
from app.models.special import SpecialZt, SpecialZrzt, SpecialZb, SpecialDt
from app.models.base.base_stock import BaseStock
from app.db.session import get_db_context

logger = logging.getLogger(__name__)


class SpecialPoolCollector:
    """特殊股票池采集器"""

    @classmethod
    def _date_str(cls, d: date) -> str:
        """日期转字符串 YYYYMMDD"""
        return d.strftime("%Y%m%d")

    @classmethod
    def _safe_float(cls, value, default=None):
        """安全转浮点数"""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _safe_int(cls, value, default=None):
        """安全转整数"""
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _parse_zt_data(cls, item: Dict, trade_date: date) -> Dict:
        """解析涨停池数据"""
        zttj = item.get("zttj", {}) or {}
        return {
            "stock_code": item.get("c"),
            "stock_name": item.get("n"),
            "mkt": cls._safe_int(item.get("m")),
            "price": cls._safe_float(item.get("p")),
            "ztp": cls._safe_float(item.get("ztp")),
            "zdp": cls._safe_float(item.get("zdp")),
            "amount": cls._safe_float(item.get("amount")),
            "ltsz": cls._safe_float(item.get("ltsz")),
            "tshare": cls._safe_float(item.get("tshare")),
            "hs": cls._safe_float(item.get("hs")),
            "zf": cls._safe_float(item.get("zf")),
            "zs": cls._safe_float(item.get("zs")),
            "yfbt": cls._safe_int(item.get("yfbt")),
            "ylbc": cls._safe_int(item.get("ylbc")),
            "hybk": item.get("hybk"),
            "zt_days": cls._safe_int(zttj.get("days")),
            "zt_count": cls._safe_int(zttj.get("ct")),
            "trade_date": trade_date,
        }

    @classmethod
    def _parse_zb_data(cls, item: Dict, trade_date: date) -> Dict:
        """解析炸板池数据"""
        zttj = item.get("zttj", {}) or {}
        return {
            "stock_code": item.get("c"),
            "stock_name": item.get("n"),
            "mkt": cls._safe_int(item.get("m")),
            "price": cls._safe_float(item.get("p")),
            "ztp": cls._safe_float(item.get("ztp")),
            "zdp": cls._safe_float(item.get("zdp")),
            "amount": cls._safe_float(item.get("amount")),
            "ltsz": cls._safe_float(item.get("ltsz")),
            "tshare": cls._safe_float(item.get("tshare")),
            "hs": cls._safe_float(item.get("hs")),
            "zf": cls._safe_float(item.get("zf")),
            "zs": cls._safe_float(item.get("zs")),
            "fbt": cls._safe_int(item.get("fbt")),
            "zbc": cls._safe_int(item.get("zbc")),
            "hybk": item.get("hybk"),
            "zt_days": cls._safe_int(zttj.get("days")),
            "zt_count": cls._safe_int(zttj.get("ct")),
            "trade_date": trade_date,
        }

    @classmethod
    def _parse_dt_data(cls, item: Dict, trade_date: date) -> Dict:
        """解析跌停池数据"""
        return {
            "stock_code": item.get("c"),
            "stock_name": item.get("n"),
            "mkt": cls._safe_int(item.get("m")),
            "price": cls._safe_float(item.get("p")),
            "zdp": cls._safe_float(item.get("zdp")),
            "amount": cls._safe_float(item.get("amount")),
            "ltsz": cls._safe_float(item.get("ltsz")),
            "tshare": cls._safe_float(item.get("tshare")),
            "hs": cls._safe_float(item.get("hs")),
            "pe": cls._safe_float(item.get("pe")),
            "fund": cls._safe_float(item.get("fund")),
            "lbt": cls._safe_float(item.get("lbt")),
            "fba": cls._safe_float(item.get("fba")),
            "days": cls._safe_int(item.get("days")),
            "oc": cls._safe_int(item.get("oc")),
            "hybk": item.get("hybk"),
            "trade_date": trade_date,
        }

    @classmethod
    def _parse_zrzt_data(cls, item: Dict, trade_date: date) -> Dict:
        """解析昨日涨停池数据（与涨停池相同）"""
        return cls._parse_zt_data(item, trade_date)

    @classmethod
    def _upsert(cls, model, values: List[Dict]):
        """批量插入（跳过重复）"""
        if not values:
            return
        with get_db_context() as db:
            try:
                stmt = insert(model).values(values)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["stock_code", "trade_date"]
                )
                db.execute(stmt)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"入库失败: {e}")

    @classmethod
    def _update_stock_imp(cls, stock_codes: set):
        """
        标记特殊股票池中的股票为关注

        只标记主板股票（深交所主板/上证所主板/创业板/科创板）
        只标记 stock_imp == 0 的（去重）
        """
        if not stock_codes:
            return 0
        with get_db_context() as db:
            try:
                # 查出已标记过的，跳过
                already_marked = {row[0] for row in db.query(BaseStock.stock_code).filter(
                    BaseStock.stock_code.in_(stock_codes),
                    BaseStock.stock_imp == 1,
                ).all()}

                new_codes = stock_codes - already_marked
                if not new_codes:
                    return 0

                # 只更新主板 + 未标记的
                updated = db.query(BaseStock).filter(
                    BaseStock.stock_code.in_(new_codes),
                    BaseStock.stock_type.in_(["深交所主板", "上证所主板", "创业板", "科创板"]),
                    BaseStock.stock_imp == 0,
                ).update({"stock_imp": 1}, synchronize_session=False)
                db.commit()
                logger.info(f"标记特殊股票池为关注: {updated} 只（{len(new_codes) - updated} 只非主板）")
                return updated
            except Exception as e:
                db.rollback()
                logger.error(f"更新 stock_imp 失败: {e}")
                return 0

    @classmethod
    def collect(cls, pool_type: str) -> Dict:
        """
        采集指定类型的特殊股票池

        参数:
            pool_type: 池类型 (zt/zrzt/qs/zb/dt)

        返回:
            {"type": 类型, "count": 数量, "elapsed_seconds": 耗时}
        """
        start_time = time.time()
        type_map = {
            "zt": {"model": SpecialZt, "func": "get_zt_pool", "date_func": get_latest_trade_day},
            "zrzt": {"model": SpecialZrzt, "func": "get_zrzt_pool", "date_func": get_prev_trade_day},
            "zb": {"model": SpecialZb, "func": "get_zb_pool", "date_func": get_latest_trade_day},
            "dt": {"model": SpecialDt, "func": "get_dt_pool", "date_func": get_latest_trade_day},
        }

        config = type_map.get(pool_type)
        if not config:
            return {"type": pool_type, "error": "未知类型"}

        model = config["model"]
        api_func = getattr(EastMoneyRequest, config["func"])

        # 获取日期
        # - zrzt（昨日涨停）: 用今天日期
        # - zt（今日涨停池）: 用今天日期，盘中采集实时数据，盘后（16点后）采集完整数据
        # - zb/dt: 用今天
        trade_date = get_latest_trade_day()
        date_str = cls._date_str(trade_date)

        logger.info(f"采集 {pool_type} 股票池，日期: {date_str}")

        # 获取数据
        try:
            # get_zt_pool / get_zrzt_pool / get_zb_pool / get_dt_pool
            raw_data = api_func(date_str)
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return {"type": pool_type, "error": str(e)}

        if not raw_data:
            return {"type": pool_type, "count": 0, "elapsed_seconds": time.time() - start_time}

        # 解析数据
        parse_func = getattr(cls, f"_parse_{pool_type}_data")
        results = []
        stock_codes = set()

        for item in raw_data:
            try:
                parsed = parse_func(item, trade_date)
                if parsed.get("stock_code"):
                    results.append(parsed)
                    stock_codes.add(parsed["stock_code"])
            except Exception as e:
                logger.error(f"解析失败: {item} - {e}")

        # 检查股票池是否有变化，无变化则跳过入库和标记
        new_imp_count = 0
        with get_db_context() as db:
            existing = db.query(model).filter(model.trade_date == trade_date).all()
            existing_codes = {r.stock_code for r in existing}
            if existing_codes == stock_codes:
                logger.info(f"{pool_type} 股票池无变化，跳过入库（{len(stock_codes)} 只）")
                elapsed = time.time() - start_time
                return {
                    "type": pool_type,
                    "count": len(results),
                    "trade_date": cls._date_str(trade_date),
                    "elapsed_seconds": round(elapsed, 2),
                    "skipped": True,
                }

        # 有变化，删除旧数据
        with get_db_context() as db:
            try:
                db.query(model).filter(model.trade_date == trade_date).delete()
                db.commit()
            except Exception as e:
                logger.error(f"删除旧数据失败: {e}")

        # 插入新数据
        cls._upsert(model, results)

        # 标记新增的特殊股票
        new_imp_count = cls._update_stock_imp(stock_codes)

        elapsed = time.time() - start_time
        logger.info(f"{pool_type} 采集完成: {len(results)} 条, 耗时 {elapsed:.2f}s, 新增关注 {new_imp_count} 只")

        return {
            "type": pool_type,
            "count": len(results),
            "trade_date": cls._date_str(trade_date),
            "elapsed_seconds": round(elapsed, 2),
            "new_imp_count": new_imp_count,
        }

    @classmethod
    def collect_all(cls) -> List[Dict]:
        """采集所有特殊股票池"""
        results = []
        for pool_type in ["zt", "qs", "zb", "dt"]:
            result = cls.collect(pool_type)
            results.append(result)
        # 昨日涨停池单独处理
        result = cls.collect("zrzt")
        results.append(result)
        return results


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=== 特殊股票池采集测试 ===")
    results = SpecialPoolCollector.collect_all()
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
