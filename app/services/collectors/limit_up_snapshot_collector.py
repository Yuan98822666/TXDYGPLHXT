# 文件: app/services/collectors/limit_up_snapshot_collector.py
import datetime
import requests
from app.models.raw.raw_limit_up_snapshot_event import RawLimitUpSnapshotEvent
from app.services.collectors.kz_generator import KZGenerator

class LimitUpSnapshotCollector:
    def __init__(self, db_session):
        self.db = db_session
        self.base_url = "https://push2ex.eastmoney.com/getTopicZTPool"

    def collect(self, *, kz_no=None, market_time=None, **kwargs) -> int:
        if kz_no is None:
            kz_no = KZGenerator.next_kz_no()
        if market_time is None:
            market_time = datetime.datetime.now()

        trade_date = kwargs.get("trade_date", datetime.date.today())
        count = 0
        try:
            params = {"date": trade_date.strftime("%Y%m%d")}
            resp = requests.get(self.base_url, params=params, timeout=5)
            if resp.status_code != 200:
                return count
            data_list = resp.json().get("data", [])
            for item in data_list:
                event = RawLimitUpSnapshotEvent(
                    kz_no=kz_no,
                    stock_code=item.get("c"),
                    stock_name=item.get("n"),
                    exchange="SH" if item.get("m",0)==1 else "SZ",
                    last_price=(item.get("p")/100) if item.get("p") else None,
                    limit_up_price=None,
                    change_pct=item.get("zdp"),
                    turnover_rate=item.get("hs"),
                    amount=item.get("amount"),
                    continuous_limit_count=item.get("lbc"),
                    first_seal_time=item.get("fbt"),
                    last_seal_time=item.get("lbt"),
                    seal_fund=item.get("fund"),
                    break_count=item.get("zbc"),
                    limit_stat_days=item.get("zttj",{}).get("days"),
                    limit_stat_count=item.get("zttj",{}).get("ct"),
                    industry_block=item.get("hybk"),
                    trade_date=trade_date,
                    market_time=market_time,
                    store_time=datetime.datetime.utcnow()
                )
                self.db.add(event)
                count += 1
        except Exception:
            pass
        self.db.commit()
        return count
