# app/collectors/dispatcher.py
from datetime import datetime, timezone
import pytz
from app.utils.kz_generator import next_kz_no
from app.collectors.board_collector import collect_board_snapshot
from app.collectors.stock_collector import collect_named_stocks
from app.writers.snapshot_writer import write_block_and_stock_snapshots

def run_snapshot_cycle():
    shanghai_tz = pytz.timezone("Asia/Shanghai")
    market_time = datetime.now(shanghai_tz).replace(tzinfo=timezone.utc)
    kz_no = next_kz_no(market_time)

    print(f"🚀 开始快照 | kz_no={kz_no}")

    try:
        # 1. 采集板块 + 获取点名股 secid
        blocks, secids = collect_board_snapshot(market_time, kz_no)
        print(f"📊 板块: {len(blocks)} | 点名股候选: {len(secids)}" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 2. 并发采集点名股详情
        stocks = collect_named_stocks(secids, market_time, kz_no)
        print(f"📈 点名股详情: {len(stocks)}" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 3. 批量写入
        write_block_and_stock_snapshots(blocks, stocks)
        print("✅ 快照入库完成" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    except Exception as e:
        print(f"❌ 快照失败: {e}" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        raise