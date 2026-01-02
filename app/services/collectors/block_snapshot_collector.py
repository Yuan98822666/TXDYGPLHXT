# 文件: app/services/collectors/block_snapshot_collector.py
import datetime
from app.models.raw.raw_block_snapshot_event import RawBlockSnapshotEvent
from app.services.collectors.kz_generator import KZGenerator
import requests

class BlockSnapshotCollector:
    """
    板块行情快照采集器
    """
    def __init__(self, db_session):
        self.db = db_session
        self.base_urls = {
            "行业": "https://push2.eastmoney.com/api/qt/clist/get?fs=m:90+t:2",
            "概念": "https://push2.eastmoney.com/api/qt/clist/get?fs=m:90+t:3"
        }

    def collect(self, *, kz_no=None, market_time=None, **kwargs) -> int:
        if kz_no is None:
            kz_no = KZGenerator.next_kz_no()
        if market_time is None:
            market_time = datetime.datetime.now()

        block_type_list = kwargs.get("block_type_list", ["行业","概念"])
        count = 0

        for block_type in block_type_list:
            url = self.base_urls.get(block_type)
            if not url:
                continue

            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code != 200:
                    continue
                data_list = resp.json().get("data", {}).get("diff", [])
                for item in data_list:
                    event = RawBlockSnapshotEvent(
                        kz_no=kz_no,
                        block_code=item.get("f12"),
                        block_name=item.get("f14"),
                        block_type=block_type,
                        clock_=item.get("f3"),
                        clock_marke=item.get("f2"),
                        block_zl_inflow=item.get("f62"),
                        block_cd_inflow=item.get("f66"),
                        block_dd_inflow=item.get("f72"),
                        block_zd_inflow=item.get("f78"),
                        block_xd_inflow=item.get("f84"),
                        # block_up_count=item.get("f104"),
                        # block_dw_count=item.get("f105"),
                        market_time=market_time,
                        fetch_time=datetime.datetime.utcnow()
                    )
                    self.db.add(event)
                    count += 1
            except Exception:
                continue

        self.db.commit()
        return count
