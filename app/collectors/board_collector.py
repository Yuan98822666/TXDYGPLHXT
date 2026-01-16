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

from typing import List, Set, Tuple
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from datetime import datetime
import yaml
from pathlib import Path
from decimal import Decimal, InvalidOperation
from app.config.settings import settings  # 统一配置入口
from app.utils.common_utils import CommonUtils


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

    # 从统一配置中心获取请求配置（实际这里不需要 load_request_config，直接用 settings）
    config = settings.request_config
    common = config.common
    endpoints = config.endpoints

    all_blocks = []  # 存储所有板块快照对象
    named_stock_secids: Set[str] = set()  # 存储 secid，用于后续个股采集

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

            diff = data["data"].get("diff", [])
            if not diff:
                break  # 没有更多数据，跳出循环

            # 处理当前页的每条板块数据
            for item in diff.values():
                # --- 构建板块快照模型对象 ---
                block = RawBlockHuoyue(
                    kz_no=kz_no,
                    market_time=market_time,
                    block_code=item["f12"],  # 板块代码
                    block_name=item["f14"],  # 板块名称
                    block_type=type_label,  # 板块类型：GN 或 HY

                    # 以下字段需要进行单位转换和安全处理
                    block_zdf=item.get("f3"),  # 涨跌幅（百分比，保留原值）
                    block_zde=item.get("f4"),  # 涨跌额（元，保留原值）
                    block_hsl=item.get("f8"),  # 换手率（百分比，保留原值）
                    up_count=item.get("f104"),  # 上涨家数
                    dw_count=item.get("f105"),  # 下跌家数
                    pi_count=item.get("f106"),  # 平盘家数

                    # 资金流字段：原始单位为元，转换为万元（除以10000）
                    block_zl_inflow=CommonUtils.safe_round_div(item.get("f62"), 10000),
                    block_cd_inflow=CommonUtils.safe_round_div(item.get("f66"), 10000),
                    block_dd_inflow=CommonUtils.safe_round_div(item.get("f72"), 10000),
                    block_zd_inflow=CommonUtils.safe_round_div(item.get("f78"), 10000),
                    block_xd_inflow=CommonUtils.safe_round_div(item.get("f84"), 10000),

                    # 资金流占比字段（百分比，保留原值）
                    block_zl_zb=item.get("f184"),
                    block_cd_zb=item.get("f69"),
                    block_dd_zb=item.get("f75"),
                    block_zd_zb=item.get("f81"),
                    block_xd_zb=item.get("f87"),

                    # 主力流入最多股信息
                    money_stock_code=item.get("f205"),
                    money_stock_name=item.get("f204"),
                    money_stock_type=item.get("f206"),

                    # 领涨股信息
                    lider_stock_code=item.get("f140"),
                    lider_stock_name=item.get("f128"),
                    lider_stock_type=item.get("f141"),
                    lider_stock_pct=item.get("f136"),  # 领涨股涨幅
                )
                all_blocks.append(block)

                # --- 提取点名股 secid ---
                # secid 格式：市场代码.股票代码
                # 市场代码：1 = 深圳(SZ), 0 = 上海(SH)

                # 领涨股
                if item.get("f140"):  # 股票代码存在
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

    return all_blocks, named_stock_secids