"""
板块活跃度采集器（改造版 - 使用独立采集函数）

功能说明：
- 从独立采集函数获取板块数据
- 提取每个板块中的"点名股"（领涨股 + 主力流入最多股）
- 返回结构化的板块数据和待采集的个股 secid 集合

数据流向：
fetch_boards_data() → 板块数据 + 点名股 → RawBlockHuoyue 模型 → 板块快照列表

设计特点：
- 调用独立的板块采集函数，减少不必要的请求
- 自动提取两种类型的点名股用于后续个股采集
- 使用统一配置中心，便于维护和扩展
- 安全的数据转换和异常处理
"""

from typing import List, Set, Tuple, Dict
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config.settings import settings
from app.utils.common_utils import CommonUtils
from app.utils.http_client import eastmoney_client
from app.collectors.unified_collector import unified_collector

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
        "_": getattr(board_info_config, "_", None),
        "fields": board_info_config.fields,
        "ut": common.ut,
        "cb": common.cb,
    }

    params = {**base_params, "secid": f"90.{block_code}"}
    try:
        data = eastmoney_client.get_jsonp(board_info_config.url, params)
        block_lb = data["data"].get("f50")
        if block_lb is not None:
            return float(commonutils.safe_round_div(block_lb))
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
    采集板块活跃度快照数据（使用独立采集函数）

    参数:
        market_time (datetime): 市场时间（带时区信息），作为快照的时间戳
        kz_no (int): 快照批次号，用于关联同一时刻的所有数据

    返回:
        Tuple[List[RawBlockHuoyue], Set[str]]:
            - 第一个元素：板块快照对象列表
            - 第二个元素：点名股的 secid 集合（格式：市场代码.股票代码）

    采集范围：
        - 概念板块 (GN)
        - 行业板块 (HY)

    内部逻辑流程：
        1. 调用独立采集函数获取板块数据
        2. 对每条板块数据构建 RawBlockHuoyue 模型对象
        3. 提取领涨股和主力流入最多股的 secid
        4. 批量获取所有板块的量比
        5. 返回板块数据列表和 secid 集合
    """

    # 调用独立采集函数获取板块数据
    print("📊 调用板块采集函数获取板块数据...")
    all_boards, named_stock_secids = unified_collector.fetch_boards_data()

    all_block_codes = []
    all_blocks_data = []

    # 处理板块数据
    for board in all_boards:
        block_code = board["code"]
        all_block_codes.append(block_code)

        block_data = {
            "kz_no": kz_no,
            "market_time": market_time,
            "block_code": block_code,
            "block_name": board["name"],
            "block_type": board["type"],
            "block_zdf": commonutils.purify(board.get("zdf")),
            "block_zde": commonutils.purify(board.get("zde")),
            "block_hsl": commonutils.purify(board.get("hsl")),
            "up_count": commonutils.purify(board.get("up_count")),
            "pi_count": commonutils.purify(board.get("pi_count")),
            "dw_count": commonutils.purify(board.get("dw_count")),
            "stock_count": (
                commonutils.purify(board.get("up_count", 0)) +
                commonutils.purify(board.get("dw_count", 0)) +
                commonutils.purify(board.get("pi_count", 0))
            ),
            "block_zl_inflow": 0,
            "block_cd_inflow": 0,
            "block_dd_inflow": 0,
            "block_zd_inflow": 0,
            "block_xd_inflow": 0,
            "block_zl_zb": 0,
            "block_cd_zb": 0,
            "block_dd_zb": 0,
            "block_zd_zb": 0,
            "block_xd_zb": 0,
            "money_stock_code": "",
            "money_stock_name": "",
            "money_stock_type": "",
            "lider_stock_code": "",
            "lider_stock_name": "",
            "lider_stock_type": "",
            "lider_stock_pct": 0,
        }

        all_blocks_data.append(block_data)

    print(f"📄 处理 {len(all_blocks_data)} 条板块记录，提取点名股 {len(named_stock_secids)} 个")

    # 批量获取所有板块的量比
    if all_block_codes:
        print(f"🔄 开始批量获取 {len(all_block_codes)} 个板块的量比...")
        block_lb_dict = get_block_lb_batch(all_block_codes)
        print("✅ 量比获取完成")
    else:
        block_lb_dict = {}

    # 构建最终的板块快照对象列表
    final_blocks: List[RawBlockHuoyue] = []
    for block_data in all_blocks_data:
        block_code = block_data["block_code"]
        block_data["block_lb"] = block_lb_dict.get(block_code, 0.0)
        block_obj = RawBlockHuoyue(**block_data)
        final_blocks.append(block_obj)

    return final_blocks, named_stock_secids
