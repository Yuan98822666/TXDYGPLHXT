# app/behavior/mentioned_stock_behavior.py
from collections import Counter
from typing import List, Dict, Any
from app.services.mentioned_stock_service import MentionedStockService


class MentionedStockBehavior:
    def __init__(self, service: MentionedStockService):
        self.service = service

    def get_hot_mentioned_stocks(self) -> Dict[str, Any]:
        """主入口：返回带点名次数的个股快照列表"""
        kz_no = self.service.get_latest_kz_no()
        if not kz_no:
            return {"kz_no": None, "stocks": []}

        # 获取所有被提及的代码（含重复）
        all_codes = self.service.get_mentioned_codes_from_blocks(kz_no)
        if not all_codes:
            return {"kz_no": kz_no, "stocks": []}

        # 统计频次
        code_counter = Counter(all_codes)
        unique_codes = list(code_counter.keys())

        # 获取个股快照
        snapshots = self.service.get_stock_snapshots_by_codes(kz_no, unique_codes)
        stock_map = {s.stock_code: s for s in snapshots}

        # 构建结果（仅包含有快照的股票）
        stocks = []
        for code, count in code_counter.items():
            if code in stock_map:
                s = stock_map[code]
                if s.stock_zdf/100 < 11:
                    stocks.append({
                    "stock_code": s.stock_code,
                    "stock_name": s.stock_name,
                    "mention_count": count,
                    # 行情
                    "stock_zxj": s.stock_zxj,
                    "stock_zdf": s.stock_zdf,
                    "stock_zjlg": s.stock_zjlg,
                    "stock_cjey": s.stock_cjey,
                    "stock_hsl": s.stock_hsl,
                    # 市值
                    "stock_zsz": s.stock_zsz,
                    "stock_ltsz": s.stock_ltsz,
                    # 估值
                    "stock_syl": s.stock_syl,
                    "stock_sjl": s.stock_sjl,
                    # 资金流（金额）
                    "stock_zl_inflow": s.stock_zl_inflow,
                    "stock_cd_inflow": s.stock_cd_inflow,
                    "stock_dd_inflow": s.stock_dd_inflow,
                    "stock_zd_inflow": s.stock_zd_inflow,
                    "stock_xd_inflow": s.stock_xd_inflow,
                    # 资金流（占比）
                    "stock_zl_zb": s.stock_zl_zb,
                    "stock_cd_zb": s.stock_cd_zb,
                    "stock_dd_zb": s.stock_dd_zb,
                    "stock_zd_zb": s.stock_zd_zb,
                    "stock_xd_zb": s.stock_xd_zb,
                })

        return {
            "kz_no": kz_no,
            "stocks": stocks
        }

    def sort_stocks(self, stocks: List[Dict], sort_by: str, ascending: bool = False) -> List[Dict]:
        """安全排序"""
        valid_fields = {"mention_count", "stock_ltsz", "stock_zdf","stock_zl_zb", "stock_cd_zb"}
        if sort_by not in valid_fields:
            sort_by = "mention_count"

        return sorted(
            stocks,
            key=lambda x: x.get(sort_by) or 0,
            reverse=not ascending
        )