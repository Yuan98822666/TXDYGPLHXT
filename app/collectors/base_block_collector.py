"""
文件路径：app/collectors/base_block_collector.py
作用说明：基础板块信息采集器（Upsert 版本）

功能说明：
- 从独立采集函数获取基础板块数据
- 使用 PostgreSQL Upsert 语法（ON CONFLICT DO UPDATE）
- 用 block_code 作为唯一标识进行更新或新增
- 保留板块内股票数量不被覆盖
"""

from typing import Dict
from app.models.base.base_block import BaseBlock
from sqlalchemy.dialects.postgresql import insert
from app.db.session import get_db_context
from app.collectors.unified_collector import unified_collector
import time


def collect_base_blocks() -> Dict[str, int]:
    """采集所有板块的基础信息并更新数据库（Upsert 方式）"""
    start_time = time.time()

    print("📊 调用板块采集函数获取基础板块数据...")
    all_boards, _ = unified_collector.fetch_boards_data()

    print(f"📈 接口返回 {len(all_boards)} 条板块数据")

    if not all_boards:
        print("⚠️  没有板块数据可写入")
        return {"updated": 0, "inserted": 0, "total": 0, "elapsed_seconds": 0}

    inserted_count = 0
    updated_count = 0

    with get_db_context() as db:
        try:
            # 构建 Upsert 数据（暂时只写入已有字段）
            values = []
            for board in all_boards:
                values.append({
                    "block_code": board["code"],
                    "block_name": board["name"],
                    "block_type": board["type"],
                    "block_stock_count": 0,
                })

            # 使用 PostgreSQL Upsert 语法
            stmt = insert(BaseBlock).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["block_code"],
                set_={
                    "block_name": stmt.excluded.block_name,
                    "block_type": stmt.excluded.block_type,
                }
            )

            db.execute(stmt)
            db.commit()

            # 统计
            for board in all_boards:
                exists = db.query(BaseBlock).filter_by(block_code=board["code"]).first()
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
        "total": len(all_boards),
        "elapsed_seconds": round(elapsed_seconds, 2)
    }

    print(f"\n📊 采集统计:")
    print(f"   - 更新: {updated_count} 条")
    print(f"   - 新增: {inserted_count} 条")
    print(f"   - 总计: {len(all_boards)} 条")
    print(f"   - 耗时: {elapsed_seconds:.2f} 秒")

    return result
