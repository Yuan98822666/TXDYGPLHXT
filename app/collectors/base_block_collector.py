"""
文件路径：app/collectors/base_block_collector.py
作用说明：基础板块数据采集器

职责边界：
  - 只负责一件事：从东方财富 API 采集板块基础信息，写入 base_block 表
  - 不做数据转换、不做业务判断

数据流向：
  东方财富 API → 本模块采集函数 → base_block 表（Upsert）

模块化设计：
  - _fetch_boards_by_type()  : 私有，按板块类型采集数据（概念/行业）
  - collect_base_blocks()    : 公开入口，采集所有板块并写入数据库

设计原则：
  - 高内聚：只做板块采集一件事
  - 低耦合：通过配置文件获取接口参数，不硬编码
  - UPSERT 策略：存在则更新名称和类型，不存在则新增
  - 字段保护：block_stock_count 由其他模块维护，Upsert 时不覆盖
"""

from typing import Dict, List
from app.models.base.base_block import BaseBlock
from sqlalchemy.dialects.postgresql import insert
from app.db.session import get_db_context
from app.utils.http_client import eastmoney_client
from app.config.settings import settings
from datetime import datetime, timezone
import time


# =========================================================
# 私有函数：按板块类型采集数据
# =========================================================

def _fetch_boards_by_type(board_type_key: str, type_label: str) -> List[Dict]:
    """
    根据板块类型采集该类型下所有板块的基础信息

    参数:
        board_type_key  : request_conf.yaml 中 endpoints 下的 key 名
                          如 "board_concept"（概念板块）、"board_industry"（行业板块）
        type_label      : 板块类型中文标识
                          GN = 概念板块，HY = 行业板块

    返回:
        List[Dict]: 板块列表，每条记录包含:
            - code : 板块代码（f12，东方财富唯一标识）
            - name : 板块名称（f14）
            - type : 板块类型（GN/HY）
    """
    config = settings.request_config
    common = config.common
    endpoint = config.endpoints[board_type_key]

    # 构建请求参数（合并通用参数 + 接口特有参数）
    base_params = {
        "fid": endpoint.fid,
        "po": endpoint.po,
        "pz": endpoint.pz,
        "np": endpoint.np,
        "fltt": endpoint.fltt,
        "invt": endpoint.invt,
        "fs": endpoint.fs,
        "fields": endpoint.fields,
        "ut": common.ut,
        "cb": common.cb,
    }

    all_boards = []
    pn = 1

    while pn <= common.max_pages:
        params = {**base_params, "pn": pn}

        try:
            data = eastmoney_client.get_jsonp(endpoint.url, params)
        except Exception as e:
            print(f"⚠️  {type_label} 板块第 {pn} 页请求失败: {e}")
            break

        # 校验响应状态
        if not data or data.get("rc") != 0:
            break

        diff = data["data"].get("diff", {})
        if not diff:
            break

        # 兼容 diff 字段的两种格式：字典或列表
        items = diff if isinstance(diff, list) else diff.values()

        for item in items:
            board_code = item.get("f12")
            board_name = item.get("f14")

            if board_code and board_name:
                all_boards.append({
                    "code": board_code,
                    "name": board_name,
                    "type": type_label,
                })

        # 判断是否已到最后一页（返回数量 < 每页数量）
        page_count = len(diff) if isinstance(diff, list) else len(diff.values())
        if page_count < int(endpoint.pz):
            break

        pn += 1

    return all_boards


# =========================================================
# 公开函数：采集所有板块并写入数据库
# =========================================================

def collect_base_blocks() -> Dict[str, int]:
    """
    采集所有板块（概念板块 + 行业板块）的基础信息并更新数据库

    采集流程:
        1. 调用 _fetch_boards_by_type() 分别采集概念板块和行业板块
        2. 合并两个列表
        3. 使用 PostgreSQL Upsert 语法写入 base_block 表
           - block_code 已存在 → 更新 block_name、block_type
           - block_code 不存在 → 新增记录，block_stock_count 默认为 0
        4. 返回采集统计信息

    返回:
        Dict[str, int]: 采集统计信息
            - updated        : 更新记录数
            - inserted       : 新增记录数
            - total          : 总处理数
            - elapsed_seconds : 耗时（秒）
    """
    start_time = time.time()
    print("📊 开始采集基础板块数据...")

    # ─── Step 1: 分类型采集 ───────────────────────────────────────
    print("   → 采集 GN 概念板块...")
    boards_gn = _fetch_boards_by_type("board_concept", "GN")
    print(f"   ✓ GN 概念板块：{len(boards_gn)} 条")

    print("   → 采集 HY 行业板块...")
    boards_hy = _fetch_boards_by_type("board_industry", "HY")
    print(f"   ✓ HY 行业板块：{len(boards_hy)} 条")

    all_boards = boards_gn + boards_hy
    print(f"📈 接口返回共 {len(all_boards)} 条板块数据")

    if not all_boards:
        print("⚠️  没有板块数据，跳过写入")
        return {"updated": 0, "inserted": 0, "total": 0, "elapsed_seconds": 0}

    # ─── Step 2: Upsert 写入 ─────────────────────────────────────
    # 先查询数据库现有记录数，用于区分更新和新增
    with get_db_context() as db:
        # 获取当前数据库中已有的板块代码集合
        existing_codes = {
            row.block_code
            for row in db.query(BaseBlock.block_code).all()
        }

    # 统计
    updated_count = 0
    inserted_count = 0
    for board in all_boards:
        if board["code"] in existing_codes:
            updated_count += 1
        else:
            inserted_count += 1

    # 构建 Upsert 数据
    values = [
        {
            "block_code": board["code"],
            "block_name": board["name"],
            "block_type": board["type"],
            "block_stock_count": 0,          # 默认 0，后续由其他模块维护
        }
        for board in all_boards
    ]

    with get_db_context() as db:
        try:
            # PostgreSQL Upsert 语法
            # INSERT ... ON CONFLICT (block_code) DO UPDATE SET ...
            stmt = insert(BaseBlock).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["block_code"],
                set_={
                    # 已存在时更新：名称和类型
                    "block_name": stmt.excluded.block_name,
                    "block_type": stmt.excluded.block_type,
                    # block_stock_count 不在 set_ 中，保留原值（不被覆盖）
                }
            )
            db.execute(stmt)
            db.commit()
            print(f"\n✅ 数据库写入成功")

        except Exception as e:
            db.rollback()
            print(f"❌ 数据库写入失败: {e}")
            raise

    # ─── Step 3: 返回统计 ───────────────────────────────────────
    elapsed_seconds = time.time() - start_time
    print(f"\n📊 板块采集统计:")
    print(f"   - 更新: {updated_count} 条")
    print(f"   - 新增: {inserted_count} 条")
    print(f"   - 总计: {len(all_boards)} 条")
    print(f"   - 耗时: {elapsed_seconds:.2f} 秒")

    return {
        "updated": updated_count,
        "inserted": inserted_count,
        "total": len(all_boards),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
