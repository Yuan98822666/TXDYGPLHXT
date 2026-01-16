# app/collectors/board_collector.py
from typing import List, Set, Tuple
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from datetime import datetime
import yaml
from pathlib import Path
from decimal import Decimal, InvalidOperation
from app.config.settings import settings  # 统一配置入口
from app.utils.common_utils import CommonUtils

def load_request_config():
    # 获取当前文件所在目录 → app/collectors/
    current_dir = Path(__file__).parent
    # 向上回退到 app/ 目录，然后进入 config/
    config_path = current_dir.parent / "config" / "request_conf.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def collect_board_snapshot(market_time: datetime, kz_no: int) -> Tuple[List[RawBlockHuoyue], Set[str]]:
    # 从统一配置中心获取请求配置
    config = settings.request_config
    common = config.common
    endpoints = config.endpoints



    all_blocks = []
    named_stock_secids: Set[str] = set()  # 存储 secid，用于后续个股采集

    # 遍历两种板块类型：概念板块(GN) 和 行业板块(HY)
    for board_type, type_label in [("board_concept", "GN"), ("board_industry", "HY")]:
        endpoint_config = endpoints[board_type]

        # 构建基础请求参数
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

        pn = 1
        while pn <= common.max_pages:
            params = {**base_params, "pn": pn}
            data = eastmoney_client.get_jsonp(endpoint_config.url, params)

            if not data or data.get("rc") != 0:
                break

            diff = data["data"].get("diff", [])
            if not diff:
                break

            for item in diff.values():
                # --- 构建板块快照 ---

                block = RawBlockHuoyue(
                    kz_no=kz_no,
                    market_time=market_time,
                    block_code=item["f12"],
                    block_name=item["f14"],
                    block_type=type_label,
                    # block_zs=item.get("f2"),
                    block_zdf=item.get("f3"),
                    block_zde=item.get("f4"),
                    block_hsl=item.get("f8"),
                    up_count=item.get("f104"),
                    dw_count=item.get("f105"),
                    pi_count=item.get("f106"),
                    block_zl_inflow=CommonUtils.safe_round_div(item.get("f62"), 10000),
                    block_cd_inflow=CommonUtils.safe_round_div(item.get("f66"), 10000),
                    block_dd_inflow=CommonUtils.safe_round_div(item.get("f72"), 10000),
                    block_zd_inflow=CommonUtils.safe_round_div(item.get("f78"), 10000),
                    block_xd_inflow=CommonUtils.safe_round_div(item.get("f84"), 10000),
                    block_zl_zb=item.get("f184"),
                    block_cd_zb=item.get("f69"),
                    block_dd_zb=item.get("f75"),
                    block_zd_zb=item.get("f81"),
                    block_xd_zb=item.get("f87"),
                    money_stock_code=item.get("f205"),
                    money_stock_name=item.get("f204"),
                    money_stock_type=item.get("f206"),
                    lider_stock_code=item.get("f140"),
                    lider_stock_name=item.get("f128"),
                    lider_stock_type=item.get("f141"),
                    lider_stock_pct=item.get("f136"),



                )

                all_blocks.append(block)

                # --- 提取点名股 secid ---
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

            # 分页控制
            if len(diff) < int(endpoint_config.pz):
                break
            pn += 1

    return all_blocks, named_stock_secids