# app/collectors/board_collector.py
from typing import List, Set, Tuple
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_block_huoyue import RawBlockHuoyue
from datetime import datetime
import yaml
from pathlib import Path
from decimal import Decimal, InvalidOperation


def load_request_config():
    # 获取当前文件所在目录 → app/collectors/
    current_dir = Path(__file__).parent
    # 向上回退到 app/ 目录，然后进入 config/
    config_path = current_dir.parent / "config" / "request_conf.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

# 辅助函数：安全地进行除法和四舍五入
def safe_round_div(value, divisor, decimal_places=2):
    """
        安全的除法与四舍五入函数。
        - 如果 value 为 None 或非数字字符串，返回 0.00。
        - 如果计算出错，返回 0.00。
        """
    # 第一步：清洗数据。如果值为空，或者非数字字符，转为 0
    try:
        if value is None or value == "" or value == "--":
            clean_value = 0
        else:
            # 尝试将输入转换为浮点数，测试是否为有效数字
            # 这里使用 float 先做一次校验，兼容字符串数字如 "123.45"
            clean_value = float(value)
    except (ValueError, TypeError):
        # 如果转换失败（例如传入了 "abc"），则强制设为 0
        clean_value = 0

    # 第二步：进行除法和四舍五入
    try:
        # 将清洗后的数字转为 Decimal 进行精确计算
        result = Decimal(str(clean_value)) / Decimal(str(divisor))
        # 四舍五入并转为 float 返回
        return float(round(result, decimal_places))
    except (InvalidOperation, TypeError, ZeroDivisionError):
        # 理论上 divisor 是固定的（100/10000），不会除零，这里做双重保险
        return 0.0

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
                    block_zl_inflow=safe_round_div(item.get("f62"), 10000),
                    block_cd_inflow=safe_round_div(item.get("f66"), 10000),
                    block_dd_inflow=safe_round_div(item.get("f72"), 10000),
                    block_zd_inflow=safe_round_div(item.get("f78"), 10000),
                    block_xd_inflow=safe_round_div(item.get("f84"), 10000),
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