# app/collectors/board_collector.py
from typing import List, Set, Tuple
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from datetime import datetime
import yaml
from pathlib import Path


def load_request_config():
    # 获取当前文件所在目录 → app/collectors/
    current_dir = Path(__file__).parent
    # 向上回退到 app/ 目录，然后进入 config/
    config_path = current_dir.parent / "config" / "request_conf.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def collect_board_snapshot(market_time: datetime, kz_no: int) -> Tuple[List[RawBlockHuoyue], Set[str]]:
    config = load_request_config()
    common = config["common"]
    endpoints = config["endpoints"]

    all_blocks = []
    named_stock_secids: Set[str] = set()  # 存储 secid，用于后续个股采集

    for board_type, type_label in [("board_concept", "GN"), ("board_industry", "HY")]:
        url = endpoints[board_type]["url"]
        base_params = {
            "fid": endpoints[board_type]["fid"],
            "po": endpoints[board_type]["po"],
            "pz": endpoints[board_type]["pz"],
            "np": endpoints[board_type]["np"],
            "fltt": endpoints[board_type]["fltt"],
            "invt": endpoints[board_type]["invt"],
            "fs": endpoints[board_type]["fs"],
            "fields": endpoints[board_type]["fields"],
        }

        pn = 1
        while pn <= common["max_pages"]:
            params = {**base_params, "pn": pn}
            data = eastmoney_client.get_jsonp(url, params)

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
                    block_zl_inflow=item.get("f62"),
                    block_cd_inflow=item.get("f66"),
                    block_dd_inflow=item.get("f72"),
                    block_zd_inflow=item.get("f78"),
                    block_xd_inflow=item.get("f84"),
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
            if len(diff) < int(endpoints[board_type]["pz"]):
                break
            pn += 1

    return all_blocks, named_stock_secids