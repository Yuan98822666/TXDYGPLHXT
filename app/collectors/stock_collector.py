# app/collectors/stock_collector.py
import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set
from decimal import Decimal, InvalidOperation

from app.utils.http_client import eastmoney_client
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from datetime import datetime

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

        # stock_zxj: 分 -> 元，并保留2位小数
        # 注意：这里原来的 else None 逻辑有误，我修正了
        stock_zxj=safe_round_div(d.get("f43"), 100) if d.get("f43") is not None else None,

        # 以下字段均改为除以 100 并保留 2 位小数
        stock_zde=safe_round_div(d.get("f169"), 100),
        stock_zdf=safe_round_div(d.get("f170"), 100),
        stock_hsl=safe_round_div(d.get("f168"), 100),
        stock_syl=safe_round_div(d.get("f162"), 100),
        stock_sjl=safe_round_div(d.get("f167"), 100),
        stock_zl_zb=safe_round_div(d.get("f193"), 100),
        stock_cd_zb=safe_round_div(d.get("f194"), 100),
        stock_dd_zb=safe_round_div(d.get("f195"), 100),
        stock_zd_zb=safe_round_div(d.get("f196"), 100),
        stock_xd_zb=safe_round_div(d.get("f197"), 100),

        # stock_cjlg: 手 -> 股 (这是乘法，不需要除，也不需要四舍五入，因为股数通常是整数)
        # 如果 d.get("f47") 可能为 None，需要处理
        stock_cjlg=d.get("f47") * 100 if d.get("f47") is not None else None,

        # 以下字段：除以 10000 并保留 2 位小数 (原来是 int，现在改为带小数的)
        stock_cjey=safe_round_div(d.get("f48"), 10000),
        stock_zsz=safe_round_div(d.get("f116"), 10000),
        stock_ltsz=safe_round_div(d.get("f117"), 10000),

        # 注意：资金流入这几个字段，如果你的数据库字段类型是 Integer/BigInt，
        # 改成小数后会报错。如果必须存整数“万”，请用 int(round(x/10000))；
        # 如果要存小数“万”，请确认数据库字段是 Numeric/Decimal 类型。
        stock_zl_inflow=safe_round_div(d.get("f137"), 10000),
        stock_cd_inflow=safe_round_div(d.get("f140"), 10000),
        stock_dd_inflow=safe_round_div(d.get("f143"), 10000),
        stock_zd_inflow=safe_round_div(d.get("f146"), 10000),
        stock_xd_inflow=safe_round_div(d.get("f149"), 10000),

        source="eastmoney",
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