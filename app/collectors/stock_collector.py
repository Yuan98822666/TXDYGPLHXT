# app/collectors/stock_collector.py
import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set

from app.utils.http_client import eastmoney_client
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from datetime import datetime


# ==============================
# 配置加载（安全路径 + 默认值）
# ==============================
def _load_stock_config():
    current_dir = Path(__file__).parent
    config_path = current_dir.parent / "config" / "request_conf.yaml"

    # 默认配置
    default_config = {
        "stock_fields": "f57,f58,f43,f169,f170,f47,f48,f168,f116,f117,f137,f140,f143,f146,f149,f162,f167,f193,f194,f195,f196,f197",
        "stock_max_workers": 10,
    }

    if not config_path.exists():
        print(f"⚠️ 股票采集配置文件未找到，使用默认配置: {config_path.resolve()}")
        return default_config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        # 合并默认值
        return {
            "stock_fields": config.get("stock_fields", default_config["stock_fields"]),
            "stock_max_workers": config.get("stock_max_workers", default_config["stock_max_workers"]),
        }
    except Exception as e:
        print(f"⚠️ 加载股票配置失败，使用默认值: {e}")
        return default_config


# 全局加载一次配置
_CONFIG = _load_stock_config()
FIELDS = _CONFIG["stock_fields"]
MAX_WORKERS = _CONFIG["stock_max_workers"]


# ==============================
# 采集逻辑
# ==============================
def fetch_stock_snapshot(secid: str, market_time: datetime, kz_no: int) -> RawStockHuoyue:
    params = {
        "secid": secid,
        "invt": 2,
        "fltt": 1,
        "dect": 1,
        "fields": FIELDS,
    }
    data = eastmoney_client.get_jsonp(
        "https://push2.eastmoney.com/api/qt/stock/get",
        params
    )

    d = data["data"]
    exchange = "SH" if secid.startswith("1.") else "SZ"

    return RawStockHuoyue(
        kz_no=kz_no,
        market_time=market_time,
        stock_code=d["f57"],
        stock_name=d["f58"],
        exchange=exchange,
        stock_zxj=d.get("f43") / 100.0 if d.get("f43") else None,  # 分 → 元
        stock_zde=d.get("f169"),
        stock_zdf=d.get("f170"),
        stock_zjlg=d.get("f47") * 100,  # 手 → 股
        stock_cjey=int(d.get("f48")) if d.get("f48") else None,
        stock_hsl=d.get("f168"),
        stock_zsz=int(d.get("f116")) if d.get("f116") else None,
        stock_ltsz=int(d.get("f117")) if d.get("f117") else None,
        stock_syl=d.get("f162"),
        stock_sjl=d.get("f167"),
        stock_zl_inflow=int(d.get("f137")) if d.get("f137") else None,
        stock_cd_inflow=int(d.get("f140")) if d.get("f140") else None,
        stock_dd_inflow=int(d.get("f143")) if d.get("f143") else None,
        stock_zd_inflow=int(d.get("f146")) if d.get("f146") else None,
        stock_xd_inflow=int(d.get("f149")) if d.get("f149") else None,
        stock_zl_zb=d.get("f193"),
        stock_cd_zb=d.get("f194"),
        stock_dd_zb=d.get("f195"),
        stock_zd_zb=d.get("f196"),
        stock_xd_zb=d.get("f197"),
        source="eastmoney",
        # raw_symbol=secid,
    )


def collect_named_stocks(secids: Set[str], market_time: datetime, kz_no: int) -> List[RawStockHuoyue]:
    stocks = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_stock_snapshot, secid, market_time, kz_no): secid
            for secid in secids
        }
        for future in as_completed(futures):
            try:
                stock = future.result()
                stocks.append(stock)
            except Exception as e:
                secid = futures[future]
                print(f"⚠️ 个股 {secid} 采集失败: {e}")
    return stocks