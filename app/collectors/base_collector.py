"""
文件路径：app/collectors/base_collector.py
作用说明：基础股票数据采集器

采集函数：
- collect_base_stocks() → 更新 base_stock 表（股票基础信息）
"""

from typing import Dict
from app.models.base.base_stock import BaseStock
from sqlalchemy.dialects.postgresql import insert
from app.db.session import get_db_context
from app.collectors.unified_collector import unified_collector
from datetime import datetime, timezone
import time


def collect_base_stocks() -> Dict[str, int]:
    """
    采集所有上市股票的基础信息并更新数据库（Upsert 方式）

    返回:
        Dict[str, int]: 采集统计信息
    """
    start_time = time.time()

    print("📊 调用基础股票采集函数获取数据...")
    base_stocks_data = unified_collector.fetch_base_stocks_data()

    code_to_name = base_stocks_data["code_to_name"]
    code_to_risk = base_stocks_data["code_to_risk"]

    print(f"📈 接口返回 {len(code_to_name)} 条股票数据")

    if not code_to_name:
        print("⚠️  没有股票数据可写入")
        return {"updated": 0, "inserted": 0, "total": 0, "elapsed_seconds": 0}

    updated_count = 0
    inserted_count = 0

    with get_db_context() as db:
        try:
            # 构建 Upsert 数据
            values = []
            for stock_code, stock_name in code_to_name.items():
                values.append({
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "stock_type": "",
                    "stock_risk": code_to_risk.get(stock_code, 1),
                    "stock_imp": 0,
                    "pdate_time": datetime.now(timezone.utc),
                })

            # 使用 PostgreSQL Upsert 语法
            stmt = insert(BaseStock).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_code"],
                set_={
                    "stock_name": stmt.excluded.stock_name,
                    "stock_risk": stmt.excluded.stock_risk,
                    "pdate_time": stmt.excluded.pdate_time,
                }
            )

            db.execute(stmt)
            db.commit()

            # 统计
            for stock_code in code_to_name.keys():
                exists = db.query(BaseStock).filter_by(stock_code=stock_code).first()
                if exists:
                    updated_count += 1
                else:
                    inserted_count += 1

            print(f"\n✅ 数据库写入成功")

        except Exception as e:
            db.rollback()
            print(f"❌ 数据库写入失败: {e}")
            raise

    elapsed_seconds = time.time() - start_time

    result = {
        "updated": updated_count,
        "inserted": inserted_count,
        "total": len(code_to_name),
        "elapsed_seconds": round(elapsed_seconds, 2)
    }

    print(f"\n📊 股票采集统计:")
    print(f"   - 更新: {updated_count} 条")
    print(f"   - 新增: {inserted_count} 条")
    print(f"   - 总计: {len(code_to_name)} 条")
    print(f"   - 耗时: {elapsed_seconds:.2f} 秒")

    return result
