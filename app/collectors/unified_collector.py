"""
文件路径：app/collectors/unified_collector.py
作用说明：统一数据聚合采集器

功能说明：
- 提供独立的数据采集函数，可按需调用
- 复用单一 Session 连接，减少链接数量，降低被反爬检测的风险
- 支持缓存机制，避免重复请求

采集函数：
- fetch_boards_data()      → 只采集板块数据（概念+行业），返回点名股 secid
- fetch_base_stocks_data() → 只采集基础股票数据
- fetch_all_data()         → 采集所有数据（向后兼容）

设计特点：
- 只建立一个 HTTP Session，所有请求复用同一连接
- 减少链接数量，降低被反爬系统检测的风险
- 统一的错误处理和日志记录
- 支持可选的内存缓存
"""

from typing import Dict, List, Set, Tuple, Any, Optional
from app.utils.http_client import eastmoney_client
from app.config.settings import settings
from datetime import datetime, timezone
import time

config = settings.request_config
common = config.common
endpoints = config.endpoints


class UnifiedCollector:
    """统一数据聚合采集器"""

    def __init__(self):
        """初始化采集器"""
        self.session = eastmoney_client.session  # 复用全局 Session
        self.cache = {}  # 内存缓存
        self.cache_ttl = 300  # 缓存有效期（秒）

    def _get_cache_key(self, endpoint: str, params_hash: str) -> str:
        """生成缓存键"""
        return f"{endpoint}:{params_hash}"

    def _check_cache(self, cache_key: str) -> Optional[Dict]:
        """检查缓存是否有效"""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return data
            else:
                del self.cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Dict):
        """设置缓存"""
        self.cache[cache_key] = (data, time.time())

    # ─────────────────────────────────────────────────────────────
    # 独立采集函数：板块数据
    # ─────────────────────────────────────────────────────────────

    def fetch_boards_data(self) -> Tuple[List[Dict], Set[str]]:
        """
        采集板块数据（概念板块 + 行业板块）

        返回:
            Tuple[List[Dict], Set[str]]:
                - 板块数据列表（包含 code, name, type, zdf, zde, hsl 等）
                - 点名股 secid 集合（格式：市场代码.股票代码）

        采集范围：
            - 概念板块 (GN): 通过 board_concept 接口
            - 行业板块 (HY): 通过 board_industry 接口

        使用场景：
            - board_collector.py → 获取板块快照数据 + 点名股 secid
            - base_block_collector.py → 获取基础板块数据
        """
        start_time = time.time()
        all_boards = []
        named_stock_secids = set()

        print("📊 开始采集板块数据...")

        # 概念板块
        print(f"   采集 GN 概念板块...")
        boards_gn, secids_gn = self._fetch_boards_by_type("board_concept", "GN")
        all_boards.extend(boards_gn)
        named_stock_secids.update(secids_gn)
        print(f"   ✓ GN 概念板块采集完成：{len(boards_gn)} 条记录")

        # 行业板块
        print(f"   采集 HY 行业板块...")
        boards_hy, secids_hy = self._fetch_boards_by_type("board_industry", "HY")
        all_boards.extend(boards_hy)
        named_stock_secids.update(secids_hy)
        print(f"   ✓ HY 行业板块采集完成：{len(boards_hy)} 条记录")

        elapsed = time.time() - start_time
        print(f"📊 板块数据采集完成：共 {len(all_boards)} 条，耗时 {elapsed:.2f} 秒")

        return all_boards, named_stock_secids

    def _fetch_boards_by_type(self, board_type: str, type_label: str) -> Tuple[List[Dict], Set[str]]:
        """
        根据板块类型采集数据

        参数:
            board_type (str): 板块类型配置键（board_concept/board_industry）
            type_label (str): 类型标签（GN=概念/HY=行业）

        返回:
            Tuple[List[Dict], Set[str]]: (板块数据列表, 点名股 secid 集合)
        """
        endpoint_config = endpoints[board_type]
        base_params = {
            "fid": endpoint_config.fid,
            "po": endpoint_config.po,
            "pz": endpoint_config.pz,
            "np": endpoint_config.np,
            "fltt": endpoint_config.fltt,
            "invt": endpoint_config.invt,
            "fs": endpoint_config.fs,
            "fields": endpoint_config.fields,
            "ut": common.ut,
            "cb": common.cb,
        }

        all_boards = []
        named_stock_secids = set()
        pn = 1

        while pn <= common.max_pages:
            params = {**base_params, "pn": pn}

            try:
                data = eastmoney_client.get_jsonp(endpoint_config.url, params)

                if not data or data.get("rc") != 0:
                    break

                diff = data["data"].get("diff", {})
                if not diff:
                    break

                # 兼容 diff 为字典或列表两种格式
                if isinstance(diff, list):
                    items = diff
                else:
                    items = diff.values()

                for item in items:
                    board_code = item.get("f12")
                    board_name = item.get("f14")

                    # 领涨股代码 f140，市场 f141（1=深市，0=沪市）
                    leading_code = item.get("f140")
                    leading_market = item.get("f141")
                    leading_secid = f"{'1' if leading_market == 1 else '0'}.{leading_code}" if leading_code else None

                    board_data = {
                        "code": board_code,
                        "name": board_name,
                        "type": type_label,
                        "zdf": item.get("f3"),
                        "zde": item.get("f4"),
                        "hsl": item.get("f8"),
                        "up_count": item.get("f104"),
                        "pi_count": item.get("f106"),
                        "dw_count": item.get("f105"),
                    }
                    all_boards.append(board_data)

                    # 提取点名股（包含领涨股）
                    if leading_secid:
                        named_stock_secids.add(leading_secid)

                    # f205/f206 = 主力流入最多股
                    if item.get("f205"):
                        market = "1" if item.get("f206") == 1 else "0"
                        named_stock_secids.add(f"{market}.{item['f205']}")

                if len(diff) < int(endpoint_config.pz):
                    break

                pn += 1

            except Exception as e:
                print(f"   ⚠️  第 {pn} 页采集失败: {e}")
                break

        return all_boards, named_stock_secids

    # ─────────────────────────────────────────────────────────────
    # 独立采集函数：基础股票数据
    # ─────────────────────────────────────────────────────────────

    def fetch_base_stocks_data(self) -> Dict[str, Dict]:
        """
        采集基础股票数据

        返回:
            Dict[str, Dict]: 基础股票数据
            {
                "code_to_name": {stock_code: stock_name},
                "code_to_risk": {stock_code: risk_status}
            }

        使用场景：
            - base_stock_collector.py → 更新 base_stock 表
        """
        start_time = time.time()

        print("📊 开始采集基础股票数据...")

        endpoint_config = endpoints["board_concept"]
        base_params = {
            "fid": endpoint_config.fid,
            "po": endpoint_config.po,
            "pz": "100",  # 每页 100 条，减少请求次数
            "np": endpoint_config.np,
            "fltt": endpoint_config.fltt,
            "invt": endpoint_config.invt,
            "fs": "m:0+t:6+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:81+s:262144+f:!2",
            "fields": "f12,f14,f152",  # 只取必要字段
            "ut": common.ut,
            "cb": common.cb,
        }

        code_to_name = {}
        code_to_risk = {}
        pn = 1

        while pn <= common.max_pages:
            params = {**base_params, "pn": pn}

            try:
                data = eastmoney_client.get_jsonp(endpoint_config.url, params)

                if not data or data.get("rc") != 0:
                    break

                diff = data["data"].get("diff", {})
                if not diff:
                    break

                # 兼容 diff 为字典或列表两种格式
                if isinstance(diff, list):
                    items = diff
                else:
                    items = diff.values()

                for item in items:
                    stock_code = item.get("f12")
                    stock_name = item.get("f14")
                    stock_short_name = item.get("f152", stock_name)

                    if stock_code and stock_name:
                        code_to_name[stock_code] = stock_name
                        short_name_str = str(stock_short_name) if stock_short_name else ""
                        risk = 0 if (short_name_str.startswith("*ST") or short_name_str.startswith("ST")) else 1
                        code_to_risk[stock_code] = risk

                if len(diff) < 100:
                    break

                pn += 1

            except Exception as e:
                print(f"   ⚠️  基础股票第 {pn} 页采集失败: {e}")
                break

        elapsed = time.time() - start_time
        print(f"📊 基础股票数据采集完成：{len(code_to_name)} 条，耗时 {elapsed:.2f} 秒")

        return {
            "code_to_name": code_to_name,
            "code_to_risk": code_to_risk
        }

    # ─────────────────────────────────────────────────────────────
    # 综合采集函数：保留向后兼容
    # ─────────────────────────────────────────────────────────────

    def fetch_all_data(self) -> Dict[str, Any]:
        """
        一次性获取所有需要的数据（向后兼容）

        返回:
            Dict[str, Any]: 统一的数据结构
            {
                "boards": [板块数据列表],
                "named_stocks": Set[secid],
                "base_stocks": {
                    "code_to_name": {stock_code: stock_name},
                    "code_to_risk": {stock_code: risk_status}
                },
                "timestamp": datetime,
                "elapsed_seconds": float
            }
        """
        start_time = time.time()

        # 调用独立采集函数
        boards, named_stocks = self.fetch_boards_data()
        base_stocks = self.fetch_base_stocks_data()

        elapsed = time.time() - start_time

        print(f"\n✅ 综合数据采集完成，耗时 {elapsed:.2f} 秒")

        return {
            "boards": boards,
            "named_stocks": named_stocks,
            "base_stocks": base_stocks,
            "timestamp": datetime.now(timezone.utc),
            "elapsed_seconds": round(elapsed, 2)
        }


# 全局单例实例
unified_collector = UnifiedCollector()
