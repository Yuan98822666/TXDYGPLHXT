# 文件: app/services/collectors/block_named_stock_collector.py
import datetime
import requests
from app.models.raw.raw_block_named_stock_event import RawBlockNamedStockEvent
from app.services.collectors.kz_generator import KZGenerator

class BlockNamedStockCollector:
    def __init__(self, db_session):
        self.db = db_session
        self.base_urls = {
            "行业": "https://push2.eastmoney.com/api/qt/clist/get",
            "概念": "https://push2.eastmoney.com/api/qt/clist/get"
        }

    def collect(self, *, kz_no=None, market_time=None, **kwargs) -> int:
        if kz_no is None:
            kz_no = KZGenerator.next_kz_no()
        if market_time is None:
            market_time = datetime.datetime.now()

        block_list = kwargs.get("block_list", [])
        count = 0

        for block in block_list:
            block_code = block["block_code"]
            block_name = block["block_name"]
            block_type = block.get("block_type", "未知")
            url = self.base_urls.get(block_type)
            if not url:
                continue
            fs_param = "m:90+t:2+f:!50" if block_type == "行业" else "m:90+t:3+f:!50"
            params = {
                "cb": "jQueryCallback",
                "fs": fs_param,
                "fields": ",".join([
                    "f12", "f14", "f128", "f140", "f141", "f152",
                    "f207", "f208", "f209", "f136"
                ]),
                "pn": 1,
                "pz": 50,
                "po": 1,
                "invt": 2,
                "fltt": 1,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            }
            try:
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code != 200:
                    continue
                text = resp.text
                start = text.find("(")
                end = text.rfind(")")
                json_str = text[start+1:end]
                json_data = requests.utils.json.loads(json_str)
                data_list = json_data.get("data", {}).get("diff", [])
                for item in data_list:
                    event = RawBlockNamedStockEvent(
                        kz_no=kz_no,
                        block_code=block_code,
                        block_name=block_name,
                        block_type=block_type,
                        stock_code=item.get("f140"),
                        stock_name=item.get("f128"),
                        market=int(item.get("f141",0)),
                        change_pct=(item.get("f136")/100) if item.get("f136") else None,
                        continuous_limit_count=item.get("f152"),
                        last_stock_name=item.get("f207"),
                        last_stock_code=item.get("f208"),
                        last_stock_market=int(item.get("f209",0)),
                        market_time=market_time,
                        fetch_time=datetime.datetime.utcnow()
                    )
                    self.db.add(event)
                    count += 1
            except Exception:
                continue

        self.db.commit()
        return count
