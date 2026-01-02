"""
文件名：test_dispatcher_run.py
作用说明：
    完整调度链路测试
    依次运行 BlockSnapshot、BlockNamedStock、StockSnapshot、LimitUpSnapshot
    验证数据采集、kz_no 批次、入库逻辑
"""

import datetime
from app.db.session import SessionLocal
from app.services.dispatcher import Dispatcher
from app.services.collectors.block_snapshot_collector import BlockSnapshotCollector
from app.services.collectors.block_named_stock_collector import BlockNamedStockCollector
from app.services.collectors.stock_snapshot_collector import StockSnapshotCollector
from app.services.collectors.limit_up_snapshot_collector import LimitUpSnapshotCollector

def test_full_dispatcher_run():
    """
    测试完整 Dispatcher 流程
    """
    db = SessionLocal()
    dispatcher = Dispatcher(db_session=db)

    # ----------------------------
    # 1. 注册板块快照采集器
    # ----------------------------
    dispatcher.register(
        BlockSnapshotCollector,
        block_type_list=["行业", "概念"]
    )

    # ----------------------------
    # 2. 注册板块点名股采集器
    # ----------------------------
    # 模拟板块列表，可根据前一步结果替换
    block_list = [
        {"block_code": "BK0480", "block_name": "航天航空", "block_type": "行业"},
        {"block_code": "BK0921", "block_name": "卫星互联网", "block_type": "概念"}
    ]
    dispatcher.register(
        BlockNamedStockCollector,
        block_list=block_list
    )

    # ----------------------------
    # 3. 注册个股快照采集器
    # ----------------------------
    # 模拟个股列表，可根据点名股结果替换
    stock_list = ["002196", "600118"]
    dispatcher.register(
        StockSnapshotCollector,
        stock_list=stock_list
    )

    # ----------------------------
    # 4. 注册涨停池采集器
    # ----------------------------
    dispatcher.register(
        LimitUpSnapshotCollector,
        trade_date=datetime.date(2026, 1, 2)
    )

    # ----------------------------
    # 5. 执行 Dispatcher
    # ----------------------------
    print("=== 开始完整调度链路测试 ===")
    dispatcher.run()
    print("=== 调度测试完成 ===")

    db.close()

if __name__ == "__main__":
    test_full_dispatcher_run()
