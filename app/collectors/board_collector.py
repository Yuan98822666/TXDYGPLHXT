"""
板块活跃度采集器

功能说明：
- 从东方财富 API 并发采集概念板块和行业板块的活跃度快照数据
- 提取每个板块中的"点名股"（领涨股 + 主力流入最多股）
- 返回结构化的板块数据和待采集的个股 secid 集合

数据流向：
东方财富 API → RawBlockHuoyue 模型 → 板块快照列表 + 点名股 secid 集合

设计特点：
- 支持分页采集，避免单次请求数据量过大
- 自动提取两种类型的点名股用于后续个股采集
- 使用统一配置中心，便于维护和扩展
- 安全的数据转换和异常处理
"""

from typing import List, Set, Tuple, Dict
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config.settings import settings  # 统一配置入口
from app.utils.common_utils import CommonUtils

config = settings.request_config
common = config.common
endpoints = config.endpoints
commonutils = CommonUtils()

def _fetch_single_lb(block_code: str) -> float:
    """
    内部工具函数：获取单个板块的量比（LB）

    参数:
        block_code (str): 板块代码（如 'BK0868'）

    返回:
        float: 量比数值（例如 1.85）。若获取失败或字段为空，返回 0.0
    """
    board_info_config = settings.request_config.endpoints["board_info"]
    common = settings.request_config.common

    base_params = {
        "invt": board_info_config.invt,
        "fltt": board_info_config.fltt,
        "wbp2u": board_info_config.wbp2u,
        "dect": board_info_config.dect,
        "_": getattr(board_info_config, "_", None),  # 安全获取下划线字段（时间戳）
        "fields": board_info_config.fields,
        "ut": common.ut,
        "cb": common.cb,
    }

    params = {**base_params, "secid": f"90.{block_code}"}
    try:
        data = eastmoney_client.get_jsonp(board_info_config.url, params)
        block_lb = data["data"].get("f50")
        if block_lb is not None:
            return float(block_lb)
        else:
            return 0.0
    except Exception as e:
        print(f"⚠️ 获取板块 {block_code} 量比时出错: {e}")
        return 0.0


def get_block_lb_batch(block_codes: List[str]) -> Dict[str, float]:
    """
    批量并发获取多个板块的量比（LB）

    参数:
        block_codes (List[str]): 待查询的板块代码列表

    返回:
        Dict[str, float]: 键为板块代码，值为对应的量比。失败项也会包含（值为0.0）
    """
    if not block_codes:
        return {}

    lb_results = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_code = {
            executor.submit(_fetch_single_lb, code): code for code in block_codes
        }
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                lb_value = future.result()
                lb_results[code] = lb_value
            except Exception as e:
                print(f"❌ 严重错误：板块 {code} 的量比任务异常: {e}")
                lb_results[code] = 0.0

    return lb_results


def collect_board_snapshot(market_time: datetime, kz_no: int) -> Tuple[List[RawBlockHuoyue], Set[str]]:
    """
    采集板块活跃度快照数据

    参数:
        market_time (datetime): 市场时间（带时区信息），作为快照的时间戳
        kz_no (int): 快照批次号，用于关联同一时刻的所有数据

    返回:
        Tuple[List[RawBlockHuoyue], Set[str]]:
            - 第一个元素：板块快照对象列表
            - 第二个元素：点名股的 secid 集合（格式：市场代码.股票代码）

    采集范围：
        - 概念板块 (GN): 通过 fs="m:90+t:3" 筛选
        - 行业板块 (HY): 通过 fs="m:90+t:2" 筛选

    内部逻辑流程：
        1. 从统一配置中心获取请求配置
        2. 遍历两种板块类型（概念/行业）
        3. 构建基础请求参数
        4. 分页循环采集数据（最多 max_pages 页）
        5. 对每条板块数据：
           - 构建 RawBlockHuoyue 模型对象
           - 提取领涨股和主力流入最多股的 secid
        6. 返回板块数据列表和 secid 集合
    """

    all_blocks_data: List[Dict] = []  # 存储所有板块快照字典
    named_stock_secids: Set[str] = set()  # 存储 secid，用于后续个股采集
    all_block_codes: List[str] = []  # 存储所有板块代码，用于批量获取量比

    # 遍历两种板块类型：概念板块(GN) 和 行业板块(HY)
    for board_type, type_label in [("board_concept", "GN"), ("board_industry", "HY")]:
        endpoint_config = endpoints[board_type]

        # 构建基础请求参数（不包含分页参数 pn）
        base_params = {
            "fid": endpoint_config.fid,
            "po": endpoint_config.po,
            "pz": endpoint_config.pz,
            "np": endpoint_config.np,
            "fltt": endpoint_config.fltt,
            "invt": endpoint_config.invt,
            "fs": endpoint_config.fs,
            "fields": endpoint_config.fields,  # 直接从顶层获取 fields
            "ut": common.ut,
            "cb": common.cb,
        }

        pn = 1  # 当前页码，从1开始
        while pn <= common.max_pages:
            # 添加分页参数
            params = {**base_params, "pn": pn}

            # 发送 HTTP 请求获取 JSONP 数据
            data = eastmoney_client.get_jsonp(endpoint_config.url, params)

            # 检查响应是否有效
            if not data or data.get("rc") != 0:
                break  # 接口返回错误，跳出循环

            diff = data["data"].get("diff", {})
            if not diff:
                break  # 没有更多数据，跳出循环

            # 处理当前页的每条板块数据
            for item in diff.values():
                block_code = item["f12"]  # 板块代码
                all_block_codes.append(block_code)

                # 构建板块快照字典
                block_data = {
                    "kz_no": kz_no,
                    "market_time": market_time,
                    "block_code": block_code,  # 板块代码
                    "block_name": item["f14"],  # 板块名称
                    "block_type": type_label,  # 板块类型：GN 或 HY

                    # 以下字段需要进行单位转换和安全处理
                    "block_zdf": item.get("f3"),  # 涨跌幅（百分比，保留原值）
                    "block_zde": item.get("f4"),  # 涨跌额（元，保留原值）
                    "block_hsl": item.get("f8"),  # 换手率（百分比，保留原值）
                    "up_count": item.get("f104"),  # 上涨家数
                    "dw_count": item.get("f105"),  # 下跌家数
                    "pi_count": item.get("f106"),  # 平盘家数
                    "stock_count": item.get("f104", 0) + item.get("f105", 0) + item.get("f106", 0),  # 总家数

                    # 资金流字段：原始单位为元，转换为万元（除以10000）
                    "block_zl_inflow": commonutils.safe_round_div(item.get("f62"), 10000),
                    "block_cd_inflow": commonutils.safe_round_div(item.get("f66"), 10000),
                    "block_dd_inflow": commonutils.safe_round_div(item.get("f72"), 10000),
                    "block_zd_inflow": commonutils.safe_round_div(item.get("f78"), 10000),
                    "block_xd_inflow": commonutils.safe_round_div(item.get("f84"), 10000),

                    # 资金流占比字段（百分比，保留原值）
                    "block_zl_zb": item.get("f184"),
                    "block_cd_zb": item.get("f69"),
                    "block_dd_zb": item.get("f75"),
                    "block_zd_zb": item.get("f81"),
                    "block_xd_zb": item.get("f87"),

                    # 主力流入最多股信息
                    "money_stock_code": item.get("f205"),
                    "money_stock_name": item.get("f204"),
                    "money_stock_type": item.get("f206"),

                    # 领涨股信息
                    "lider_stock_code": item.get("f140"),
                    "lider_stock_name": item.get("f128"),
                    "lider_stock_type": item.get("f141"),
                    "lider_stock_pct": item.get("f136"),  # 领涨股涨幅
                }
                all_blocks_data.append(block_data)

                # 提取点名股 secid 只含主板上市
                # 领涨股
                if commonutils.is_main_board(item.get("f140")):  # 股票代码存在
                    market = "1" if item.get("f141") == 1 else "0"
                    secid = f"{market}.{item['f140']}"
                    named_stock_secids.add(secid)

                # 主力流入最多股
                if item.get("f205"):
                    market = "1" if item.get("f206") == 1 else "0"
                    secid = f"{market}.{item['f205']}"
                    named_stock_secids.add(secid)

            # 分页控制：如果当前页数据量小于每页数量，说明已到最后一页
            if len(diff) < int(endpoint_config.pz):
                break
            pn += 1

    # 批量获取所有板块的量比
    print(f"🔄 开始批量获取 {len(all_block_codes)} 个板块的量比...")
    block_lb_dict = get_block_lb_batch(all_block_codes)
    print("✅ 量比获取完成")

    # 构建最终的板块快照对象列表
    final_blocks: List[RawBlockHuoyue] = []
    for block_data in all_blocks_data:
        block_code = block_data["block_code"]
        block_data["block_lb"] = block_lb_dict.get(block_code, 0.0)
        block_obj = RawBlockHuoyue(**block_data)
        final_blocks.append(block_obj)

    return final_blocks, named_stock_secids