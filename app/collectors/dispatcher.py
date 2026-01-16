"""
采集调度器

功能说明：
- 协调整个快照采集周期的执行流程
- 串联板块采集 → 个股采集 → 数据持久化三个阶段
- 提供完整的日志输出和错误处理

执行流程：
1. 生成快照批次号（kz_no）
2. 采集板块数据并提取点名股 secid
3. 并发采集点名股详细行情
4. 批量写入数据库

设计特点：
- 时间戳统一使用上海时区并转换为 UTC 存储
- 完整的异常处理和回滚机制
- 详细的执行日志便于监控和调试
- 单一入口函数 run_snapshot_cycle()
"""

from datetime import datetime, timezone
import pytz
from app.utils.snapshot_no import next_kz_no
from app.collectors.board_collector import collect_board_snapshot
from app.collectors.stock_collector import collect_named_stocks
from app.utils.snapshot_writer import write_block_and_stock_snapshots


def run_snapshot_cycle():
    """
    执行完整的快照采集周期

    功能流程：
        1. 获取当前上海时间并转换为 UTC（用于数据库存储）
        2. 生成唯一的快照批次号（kz_no）
        3. 采集板块活跃度数据
        4. 提取点名股 secid 集合
        5. 并发采集点名股详细行情
        6. 批量写入数据库

    时间处理说明：
        - 采集时间使用上海时区（Asia/Shanghai）
        - 存储到数据库时转换为 UTC 时区
        - 这样保证了数据的时间一致性，无论服务器在哪个时区

    异常处理：
        - 任何阶段的异常都会被捕获并打印错误信息
        - 异常会重新抛出，便于上层监控系统处理
        - 数据库写入失败会自动回滚，保证数据一致性

    日志输出：
        - 使用 emoji 图标提高日志可读性
        - 包含关键指标（板块数量、股票数量等）
        - 包含精确的时间戳便于问题排查
    """

    # 设置上海时区
    shanghai_tz = pytz.timezone("Asia/Shanghai")

    # 获取当前上海时间，并转换为 UTC（用于数据库存储）
    # 注意：datetime.now(shanghai_tz) 返回带时区的 datetime
    # .replace(tzinfo=timezone.utc) 将其标记为 UTC（实际时间值不变）
    # 这样存储到数据库的是 UTC 时间，但代表的是上海时间点
    market_time = datetime.now(shanghai_tz).replace(tzinfo=timezone.utc)

    # 生成快照批次号
    kz_no = next_kz_no(market_time)
    print(f"🚀 开始快照 | kz_no={kz_no}")

    try:
        # 1. 采集板块 + 获取点名股 secid
        blocks, secids = collect_board_snapshot(market_time, kz_no)
        print(f"📊 板块: {len(blocks)} | 点名股候选: {len(secids)}\t" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 2. 并发采集点名股详情
        stocks = collect_named_stocks(secids, market_time, kz_no)
        print(f"📈 点名股详情: {len(stocks)}\t" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # 3. 批量写入数据库
        write_block_and_stock_snapshots(blocks, stocks)
        print("✅ 快照入库完成\t" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    except Exception as e:
        # 捕获所有异常，打印错误信息后重新抛出
        print(f"❌ 快照失败: {e}" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        raise