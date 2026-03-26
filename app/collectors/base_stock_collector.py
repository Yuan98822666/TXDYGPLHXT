"""
基础股票信息采集器（改造版 - 使用独立采集函数）

功能说明：
- 从独立采集函数获取基础股票数据
- 先查询数据库所有现有股票
- 与接口数据对比，更新已有的、新增不存在的
- 根据股票简称判断风险状态（*ST/ST/N/C等）
- 保留用户自选标记（stock_imp），不被自动更新覆盖

数据流向：
fetch_base_stocks_data() → 基础股票数据 → 查询数据库现有数据 → 对比 → 更新/新增

设计特点：
- 调用独立的基础股票采集函数，减少不必要的请求
- 完整的对比逻辑，确保新增数据不会遗漏
- 自动判断风险状态（根据股票简称）
- 保留用户自选标记，不被覆盖
- 完善的异常处理和日志记录
"""

from typing import Dict, Set
from app.models.base.base_stock import BaseStock
from app.db.session import get_db_context
from datetime import datetime, timezone
import time
from app.collectors.unified_collector import unified_collector


def collect_base_stocks() -> Dict[str, int]:
    """
    采集所有上市股票的基础信息并更新数据库（使用独立采集函数）

    返回:
        Dict[str, int]: 采集统计信息
        {
            "updated": 更新的记录数,
            "inserted": 新增的记录数,
            "total": 处理的总记录数,
            "elapsed_seconds": 耗时（秒）
        }

    采集流程:
        1. 调用独立采集函数获取基础股票数据
        2. 查询数据库所有现有股票
        3. 对比接口数据和数据库数据：
           - 如果股票在数据库中存在：更新 stock_name, stock_risk, pdate_time（保留 stock_imp）
           - 如果股票在数据库中不存在：新增记录（stock_risk 根据名称判断, stock_imp=0）
        4. 返回采集统计信息
    """
    start_time = time.time()

    # 调用独立采集函数获取基础股票数据
    print("📊 调用基础股票采集函数获取数据...")
    base_stocks_data = unified_collector.fetch_base_stocks_data()

    code_to_name = base_stocks_data["code_to_name"]
    code_to_risk = base_stocks_data["code_to_risk"]

    print(f"📈 接口返回 {len(code_to_name)} 条股票数据")

    # 查询数据库所有现有股票
    print("🔍 查询数据库现有股票...")
    with get_db_context() as db:
        existing_stocks = db.query(BaseStock).all()
        existing_codes: Set[str] = {stock.stock_code for stock in existing_stocks}
        print(f"📊 数据库现有 {len(existing_codes)} 条股票数据")

    # 对比并更新
    updated_count = 0
    inserted_count = 0

    with get_db_context() as db:
        # ─── 第一步：更新已有的股票 ─────────────────────────────────
        print("🔄 更新已有股票...")
        for stock_code in existing_codes:
            if stock_code in code_to_name:
                try:
                    existing = db.query(BaseStock).filter_by(stock_code=stock_code).first()
                    if existing:
                        existing.stock_name = code_to_name[stock_code]
                        existing.stock_risk = code_to_risk.get(stock_code, 1)
                        existing.pdate_time = datetime.now(timezone.utc)
                        updated_count += 1
                except Exception as e:
                    print(f"⚠️  更新股票 {stock_code} 时出错: {e}")

        # ─── 第二步：新增不存在的股票 ─────────────────────────────────
        print("➕ 新增不存在的股票...")
        for stock_code, stock_name in code_to_name.items():
            if stock_code not in existing_codes:
                try:
                    new_stock = BaseStock(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        stock_type="",  # 不更新 stock_type
                        stock_risk=code_to_risk.get(stock_code, 1),
                        stock_imp=0,  # 默认未自选
                        pdate_time=datetime.now(timezone.utc)
                    )
                    db.add(new_stock)
                    inserted_count += 1
                except Exception as e:
                    print(f"⚠️  新增股票 {stock_code} 时出错: {e}")

        # 提交事务
        try:
            db.commit()
            print(f"\n✅ 数据库提交成功")
        except Exception as e:
            db.rollback()
            print(f"❌ 数据库提交失败: {e}")
            raise

    elapsed_seconds = time.time() - start_time

    result = {
        "updated": updated_count,
        "inserted": inserted_count,
        "total": len(code_to_name),
        "elapsed_seconds": round(elapsed_seconds, 2)
    }

    print(f"\n📊 采集统计:")
    print(f"   - 更新: {updated_count} 条")
    print(f"   - 新增: {inserted_count} 条")
    print(f"   - 总计: {len(code_to_name)} 条")
    print(f"   - 耗时: {elapsed_seconds:.2f} 秒")

    return result
