# -*- coding: utf-8 -*-
"""
板块快照采集器

功能：每分钟采集概念（GN）和行业（HY）板块的快照数据，写入 raw_min_block 表
注意：只采集 GN+HY，排除风格（FG）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from datetime import datetime
from typing import List, Dict

from app.utils.request_util import EastMoneyRequest
from app.utils.batch_no import generate_batch_no
from app.models.raw.raw_min_block import RawMinBlock
from app.models.base.base_stock import BaseStock
from app.db.session import get_db_context
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)


class BlockRawCollector:
    """板块快照采集器"""

    @classmethod
    def _safe_divide(cls, value, divisor=100.0):
        """安全除法，处理None值"""
        if value is None:
            return None
        try:
            return float(value) / divisor
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse_block_data(cls, item: Dict) -> Dict:
        """解析单条板块数据"""
        return {
            "block_code": item.get("f12"),
            "block_name": item.get("f14"),
            "block_zs": cls._safe_divide(item.get("f2")),    # 指数
            "block_zdf": cls._safe_divide(item.get("f3")),   # 涨跌幅
            "block_lb": cls._safe_divide(item.get("f10")),   # 量比
            "block_hsl": cls._safe_divide(item.get("f8")),   # 换手率
            "stock_cjls": item.get("f5"),                    # 成交量
            "block_zl_inflow": item.get("f62"),             # 主力净流入
            "block_cd_inflow": item.get("f66"),             # 超大单净流入
            "block_dd_inflow": item.get("f72"),             # 大单净流入
            "block_zd_inflow": item.get("f78"),             # 中单净流入
            "block_xd_inflow": item.get("f84"),             # 小单净流入
            "block_zl_zb": cls._safe_divide(item.get("f184")),  # 主力占比
            "block_cd_zb": cls._safe_divide(item.get("f69")),   # 超大单占比
            "block_dd_zb": cls._safe_divide(item.get("f75")),   # 大单占比
            "block_zd_zb": cls._safe_divide(item.get("f81")),   # 中单占比
            "block_xd_zb": cls._safe_divide(item.get("f87")),   # 小单占比
            "block_ltg": item.get("f39"),                   # 流通股
            "block_up_stock": item.get("f104"),            # 上涨家数
            "block_pi_stock": item.get("f105"),            # 平盘家数
            "block_dw_stock": item.get("f106"),            # 下跌家数
            "leader_stock_code": item.get("f140"),          # 领涨股代码
            "leader_stock_name": item.get("f128"),          # 领涨股名称
            "leader_stock_zdf": cls._safe_divide(item.get("f136")),  # 领涨股涨幅
            "money_stock_code": item.get("f205"),           # 资金流入最多股代码
            "money_stock_name": item.get("f204"),           # 资金流入最多股名称
        }

    @classmethod
    def collect(cls) -> Dict:
        """采集板块快照数据（仅 GN+HY）"""
        start_time = time.time()

        # 生成批次号
        raw_no, trade_date, snapshot_time = generate_batch_no()

        # 分页获取 GN+HY 板块数据（已在 API 层过滤）
        all_data = EastMoneyRequest.get_block_snapshot_all()

        if not all_data:
            return {"total": 0, "success": 0, "elapsed_seconds": 0}

        logger.info(f"板块快照：GN+HY 共 {len(all_data)} 条")

        # 解析数据
        results = []
        for item in all_data:
            try:
                parsed = cls._parse_block_data(item)
                if parsed.get("block_code"):
                    parsed["raw_no"] = raw_no
                    parsed["snapshot_time"] = snapshot_time
                    parsed["trade_date"] = trade_date
                    results.append(parsed)
            except Exception as e:
                logger.error(f"解析板块数据失败: {e}")

        # 批量入库（逐条 upsert 防止并发冲突）
        success = 0
        conflict_fields = ["block_code", "snapshot_time"]
        with get_db_context() as db:
            for data in results:
                try:
                    stmt = insert(RawMinBlock).values(data)
                    update_dict = {k: v for k, v in data.items() if k not in conflict_fields}
                    stmt = stmt.on_conflict_do_update(
                        index_elements=conflict_fields,
                        set_=update_dict
                    )
                    db.execute(stmt)
                    success += 1
                except Exception as ex:
                    logger.error(f"入库失败: {data.get('block_code')} - {ex}")
            db.commit()

        # 从板块快照中提取领涨股和资金流入最多股，标记为关注（仅限主板）
        new_imp_count = cls._mark_block_stocks_as_imp(results)

        elapsed = time.time() - start_time
        logger.info(f"板块快照采集完成: GN+HY共{len(results)}条, 耗时{elapsed:.2f}s, 新增关注股票 {new_imp_count} 只")

        return {
            "total": len(results),
            "success": success,
            "new_imp_count": new_imp_count,
            "elapsed_seconds": round(elapsed, 2),
        }

    @classmethod
    def _mark_block_stocks_as_imp(cls, block_results: List[Dict]) -> int:
        """
        从板块快照中提取领涨股和资金流入最多股，标记为关注

        只标记主板股票（SH_ZB/SZ_ZB），排除科创板、创业板、北交所
        只标记 stock_imp != 1 的股票
        """
        # 收集所有领涨股和资金最多股的股票代码
        all_codes = set()
        for item in block_results:
            leader = item.get("leader_stock_code")
            money = item.get("money_stock_code")
            if leader:
                all_codes.add(leader)
            if money:
                all_codes.add(money)

        if not all_codes:
            return 0

        with get_db_context() as db:
            # 查出未标记的主板股票
            existing_imp = db.query(BaseStock.stock_code).filter(
                BaseStock.stock_code.in_(all_codes),
                BaseStock.stock_imp == 1,
                BaseStock.stock_type.in_(["上海主板", "中小板", "创业板", "科创板"])
            ).all()
            already_marked = {row[0] for row in existing_imp}

            new_codes = all_codes - already_marked
            if not new_codes:
                logger.debug(f"领涨/资金股标记：无新增（{len(all_codes)} 只均已标记或非主板）")
                return 0

            # 只更新主板股票
            db.query(BaseStock).filter(
                BaseStock.stock_code.in_(new_codes),
                BaseStock.stock_type.in_(["上海主板", "中小板", "创业板", "科创板"])
            ).update({"stock_imp": 1}, synchronize_session=False)
            db.commit()
            logger.info(f"标记领涨/资金股为关注: {len(new_codes)} 只（非主板股票已过滤）")

        return len(new_codes)


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=== 板块快照采集测试（仅 GN+HY）===")
    result = BlockRawCollector.collect()
    print(json.dumps(result, ensure_ascii=False))
