# 文件: app/services/collectors/stock_snapshot_collector.py
import datetime
import requests
from app.models.raw.raw_stock_snapshot_event import RawStockSnapshotEvent
from app.services.collectors.kz_generator import KZGenerator

class StockSnapshotCollector:
    def __init__(self, db_session):
        self.db = db_session
        self.base_url = "https://push2.eastmoney.com/api/qt/stock/get"

    def collect(self, *, kz_no=None, market_time=None, **kwargs) -> int:
        if kz_no is None:
            kz_no = KZGenerator.next_kz_no()
        if market_time is None:
            market_time = datetime.datetime.now()

        stock_list = kwargs.get("stock_list", [])
        count = 0
        for stock in stock_list:
            try:
                stock_code = stock["stock_code"]
                exchange = stock.get("exchange","SZ")
                secid_prefix = "0" if exchange=="SZ" else "1"
                secid = f"{secid_prefix}.{stock_code}"
                params = {
                    "secid": secid,
                    "invt": 2,
                    "fltt": 1,
                    "dect": 1,
                    "fields": ",".join([
                        "f43","f44","f47","f48",
                        "f57","f58",
                        "f168","f169","f170",
                        "f116","f117",
                        "f162","f167",
                        "f260","f261"
                    ])
                }
                resp = requests.get(self.base_url, params=params, timeout=5)
                if resp.status_code != 200:
                    continue
                data = resp.json().get("data")
                if not data:
                    continue
                event = RawStockSnapshotEvent(
                    kz_no=kz_no,
                    stock_code=data.get("f57"),
                    stock_name=data.get("f58"),
                    dqjg=(data.get("f43")/100) if data.get("f43") else None,
                    zde=(data.get("f169")/100) if data.get("f169") else None,
                    zdf=(data.get("f170")/100) if data.get("f170") else None,
                    cjl=data.get("f47"),
                    cje=data.get("f48"),
                    hsl=(data.get("f168")/100) if data.get("f168") else None,
                    total_market_cap=data.get("f116"),
                    circulating_market_cap=data.get("f117"),
                    pe=data.get("f162"),
                    pb=(data.get("f167")/100) if data.get("f167") else None,
                    market_time=market_time,
                    fetch_time=datetime.datetime.utcnow()
                )
                self.db.add(event)
                count += 1
            except Exception:
                continue
        self.db.commit()
        return count
