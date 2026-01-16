# app/collectors/stock_collector.py
import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set
from decimal import Decimal, InvalidOperation

from app.utils.common_utils import CommonUtils
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from datetime import datetime
from app.config.settings import settings  # 统一配置入口


# ==============================
# 配置加载（安全路径 + 默认值）
# ==============================
def _load_stock_config():
    # 获取当前文件所在目录 → app/collectors/
    current_dir = Path(__file__).parent
    # 向上回退到 app/ 目录，然后进入 config/
    config_path = current_dir.parent / "config" / "request_conf.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


# ==============================
# 采集逻辑
# ==============================
def fetch_stock_snapshot(secid: str, market_time: datetime, kz_no: int) -> RawStockHuoyue:

    # 从统一配置中心获取请求配置
    endpoint_config = settings.request_config.endpoints["stock_snapshot"]
    common = settings.request_config.common

    base_params = {
        "invt": endpoint_config.invt,
        "fltt": endpoint_config.fltt,
        "wbp2u": endpoint_config.wbp2u,
        "dect": endpoint_config.dect,
        "_": getattr(endpoint_config, "_", None),  # 安全获取下划线字段
        "fields": endpoint_config.fields,
        "ut": common.ut,
        "cb": common.cb,
    }

    params = {**base_params, "secid": secid}
    data = eastmoney_client.get_jsonp(endpoint_config.url, params)

    d = data["data"]
    exchange = "SH" if secid.startswith("1.") else "SZ"

    return RawStockHuoyue(
        kz_no=kz_no,
        market_time=market_time,
        stock_code=d["f57"],
        stock_name=d["f58"],
        exchange=exchange,

        # stock_zxj: 分 -> 元，并保留2位小数
        # 注意：这里原来的 else None 逻辑有误，我修正了
        stock_zxj=CommonUtils.safe_round_div(d.get("f43"), 100) if d.get("f43") is not None else None,

        # 以下字段均改为除以 100 并保留 2 位小数
        stock_zde=CommonUtils.safe_round_div(d.get("f169"), 100),
        stock_zdf=CommonUtils.safe_round_div(d.get("f170"), 100),
        stock_hsl=CommonUtils.safe_round_div(d.get("f168"), 100),
        stock_syl=CommonUtils.safe_round_div(d.get("f162"), 100),
        stock_sjl=CommonUtils.safe_round_div(d.get("f167"), 100),
        stock_zl_zb=CommonUtils.safe_round_div(d.get("f193"), 100),
        stock_cd_zb=CommonUtils.safe_round_div(d.get("f194"), 100),
        stock_dd_zb=CommonUtils.safe_round_div(d.get("f195"), 100),
        stock_zd_zb=CommonUtils.safe_round_div(d.get("f196"), 100),
        stock_xd_zb=CommonUtils.safe_round_div(d.get("f197"), 100),

        # stock_cjlg: 手 -> 股 (这是乘法，不需要除，也不需要四舍五入，因为股数通常是整数)
        # 如果 d.get("f47") 可能为 None，需要处理
        stock_cjlg=d.get("f47") * 100 if d.get("f47") is not None else None,

        # 以下字段：除以 10000 并保留 2 位小数 (原来是 int，现在改为带小数的)
        stock_cjey=CommonUtils.safe_round_div(d.get("f48"), 10000),
        stock_zsz=CommonUtils.safe_round_div(d.get("f116"), 10000),
        stock_ltsz=CommonUtils.safe_round_div(d.get("f117"), 10000),

        # 注意：资金流入这几个字段，如果你的数据库字段类型是 Integer/BigInt，
        # 改成小数后会报错。如果必须存整数“万”，请用 int(round(x/10000))；
        # 如果要存小数“万”，请确认数据库字段是 Numeric/Decimal 类型。
        stock_zl_inflow=CommonUtils.safe_round_div(d.get("f137"), 10000),
        stock_cd_inflow=CommonUtils.safe_round_div(d.get("f140"), 10000),
        stock_dd_inflow=CommonUtils.safe_round_div(d.get("f143"), 10000),
        stock_zd_inflow=CommonUtils.safe_round_div(d.get("f146"), 10000),
        stock_xd_inflow=CommonUtils.safe_round_div(d.get("f149"), 10000),

        source="eastmoney",
    )


def collect_named_stocks(secids: Set[str], market_time: datetime, kz_no: int) -> List[RawStockHuoyue]:
    stocks = []
    with ThreadPoolExecutor(10) as executor:
        futures = {executor.submit(fetch_stock_snapshot, secid, market_time, kz_no): secid for secid in secids}
        for future in as_completed(futures):
            try:
                stock = future.result()
                stocks.append(stock)
            except Exception as e:
                secid = futures[future]
                print(f"⚠️ 个股 {secid} 采集失败: {e}")
    return stocks
