"""
文件路径：app/collectors/base_block_stock_lnk_collector.py
作用说明：板块成分股关联表采集器

职责边界：
  - 遍历 base_block 表中所有板块
  - 对每个板块调用东方财富成分股接口，获取该板块下所有股票代码
  - 将 (block_code, stock_code) 关联关系 Upsert 写入 base_block_stock_lnk 表

数据流向：
  base_block 表（板块列表）
      ↓ 遍历每个板块
  东方财富成分股接口（动态拼接 fs 参数）
      ↓ 采集 stock_code 列表
  base_block_stock_lnk 表（Upsert）

模块化设计：
  - _fetch_block_stocks()          : 私有，采集单个板块的成分股代码列表
  - collect_base_block_stock_lnk() : 公开入口，遍历所有板块并写入关联表

设计原则：
  - 高内聚：只做板块成分股关联采集一件事
  - 低耦合：接口参数从 yaml 配置读取，fs 参数动态拼接
  - 容错性：单个板块采集失败不中断整体流程，记录失败列表
  - 限流保护：每个板块之间随机延迟 1~3s，模拟人工浏览，避免封 IP
  - Upsert 策略：(block_code, stock_code) 联合唯一，冲突时更新 update_time
"""

import time
import random
from typing import Dict, List, Tuple
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.config.settings import settings
from app.db.session import get_db_context
from app.models.base.base_block import BaseBlock
from app.models.base.base_block_stock_lnk import BaseBlockStockLnk
from app.utils.http_client import eastmoney_client


# =========================================================
# 私有函数：采集单个板块的成分股代码列表
# =========================================================

def _fetch_block_stocks(block_code: str) -> List[str]:
    """
    采集指定板块内的所有成分股代码

    接口说明：
      - URL：push2.eastmoney.com/api/qt/clist/get
      - fs 参数格式：b:bk{block_code}+f:!50
        * 板块代码全小写，如 BK0428 → bk0428
        * f:!50 表示排除停牌股
      - 每页 100 条，分页翻取直到最后一页
      - 此接口使用独立的 ut、wbp2u、cb，与 common 不同

    参数:
        block_code: 板块代码（原始大写格式，如 BK0428）

    返回:
        List[str]: 该板块下所有成分股的股票代码列表
                   采集失败时返回空列表
    """
    config = settings.request_config
    common = config.common
    endpoint = config.endpoints["block_stocks"]

    # fs 参数动态拼接：板块代码转小写
    # 格式：b:bk{block_code}+f:!50
    # 示例：BK0428 → b:bk0428+f:!50
    fs_value = f"b:{block_code.lower()}+f:!50"

    base_params = {
        "fid": endpoint.fid,
        "po": endpoint.po,
        "pz": endpoint.pz,
        "np": endpoint.np,
        "fltt": endpoint.fltt,
        "invt": endpoint.invt,
        "dect": endpoint.dect,
        "fs": fs_value,           # 动态拼接的筛选条件
        "fields": endpoint.fields,
        "ut": common.ut,          # 使用 common.ut
        "wbp2u": endpoint.wbp2u,  # ⚠️ 此接口必须携带，否则连接被关闭
        "cb": common.cb,          # 使用 common.cb
    }

    stock_codes: List[str] = []
    pn = 1

    while pn <= common.max_pages:
        params = {**base_params, "pn": pn}

        try:
            data = eastmoney_client.get_jsonp(endpoint.url, params)
        except Exception as e:
            from urllib.parse import urlencode
            debug_url = f"{endpoint.url}?{urlencode(params)}"
            print(f"      ⚠️  板块 {block_code} 第 {pn} 页请求失败: {e}")
            print(f"      🔗 失败URL: {debug_url}")
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
            stock_code = item.get("f12")
            if stock_code:
                stock_codes.append(str(stock_code))

        # 判断是否已到最后一页（返回数量 < 每页数量）
        page_count = len(diff) if isinstance(diff, list) else len(diff.values())
        if page_count < int(endpoint.pz):
            break

        pn += 1

    return stock_codes


# =========================================================
# 公开函数：遍历所有板块，采集成分股并写入关联表
# =========================================================

def collect_base_block_stock_lnk() -> Dict:
    """
    遍历所有板块，采集每个板块的成分股，写入 base_block_stock_lnk 关联表

    采集流程:
        1. 从 base_block 表查出所有板块（block_code + block_name）
        2. 遍历每个板块：
           a. 动态拼接 fs = b:bk{block_code}+f:!50（板块代码全小写）
           b. 分页采集成分股，收集 stock_code 列表
           c. 每个板块采集完后立即 Upsert 写入（避免内存积压）
           d. 随机延迟 1~3s，模拟人工浏览，避免封 IP
        3. 返回统计信息（总关联数、成功板块数、失败板块数）

    容错策略：
        - 单个板块采集失败 → 记录到 failed_blocks，继续下一个板块
        - 单个板块写入失败 → 回滚该板块，继续下一个板块

    返回:
        Dict: 采集统计信息
            - total_blocks   : 总板块数
            - success_blocks : 成功采集的板块数
            - failed_blocks  : 失败的板块列表
            - total_links    : 写入的总关联数
            - elapsed_seconds: 总耗时（秒）
    """
    start_time = time.time()
    print("📊 开始采集板块成分股关联数据...")

    # ─── Step 1: 查询所有板块 ────────────────────────────────────
    with get_db_context() as db:
        blocks: List[Tuple[str, str]] = [
            (row.block_code, row.block_name)
            for row in db.query(BaseBlock.block_code, BaseBlock.block_name).all()
        ]

    total_blocks = len(blocks)
    print(f"📋 共 {total_blocks} 个板块待采集")

    if not blocks:
        print("⚠️  base_block 表为空，请先采集板块基础数据")
        return {
            "total_blocks": 0,
            "success_blocks": 0,
            "failed_blocks": [],
            "total_links": 0,
            "elapsed_seconds": 0,
        }

    # ─── Step 2: 遍历板块，逐个采集成分股 ───────────────────────
    success_blocks = 0
    failed_blocks: List[Tuple[str, str]] = []
    total_links = 0
    now_utc = datetime.now(timezone.utc)

    for idx, (block_code, block_name) in enumerate(blocks, start=1):
        print(f"   [{idx:>4}/{total_blocks}] 采集板块: {block_code} {block_name}", end="")

        # 采集该板块的成分股
        stock_codes = _fetch_block_stocks(block_code)

        if not stock_codes:
            print(f"  → ⚠️  无成分股数据，跳过")
            failed_blocks.append((block_code, block_name))
            # 失败也要延迟，避免连续快速请求触发封禁
            time.sleep(random.uniform(1.0, 2.0))
            continue

        print(f"  → {len(stock_codes)} 只成分股")

        # ─── Step 3: Upsert 写入关联表 ───────────────────────────
        values = [
            {
                "block_code": block_code,
                "block_name": block_name,
                "stock_code": stock_code,
                "update_time": now_utc,
            }
            for stock_code in stock_codes
        ]

        with get_db_context() as db:
            try:
                stmt = insert(BaseBlockStockLnk).values(values)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_block_stock",
                    set_={
                        # 冲突时只更新 update_time，关联关系本身不变
                        "update_time": stmt.excluded.update_time,
                    }
                )
                db.execute(stmt)
                db.commit()
                total_links += len(stock_codes)
                success_blocks += 1

            except Exception as e:
                db.rollback()
                print(f"      ❌ 板块 {block_code} 写入失败: {e}")
                failed_blocks.append((block_code, block_name))

        # 每个板块之间随机延迟 1~3s，模拟人工浏览，避免封 IP
        time.sleep(random.uniform(1.0, 3.0))

    # ─── Step 4: 返回统计 ─────────────────────────────────────
    elapsed_seconds = time.time() - start_time

    print(f"\n📊 板块成分股关联采集统计:")
    print(f"   - 总板块数  : {total_blocks}")
    print(f"   - 成功板块  : {success_blocks}")
    print(f"   - 失败板块  : {len(failed_blocks)}")
    print(f"   - 总关联数  : {total_links}")
    print(f"   - 耗时      : {elapsed_seconds:.2f} 秒")

    if failed_blocks:
        print(f"\n⚠️  失败板块列表:")
        for code, name in failed_blocks:
            print(f"   - {code} {name}")

    return {
        "total_blocks": total_blocks,
        "success_blocks": success_blocks,
        "failed_blocks": [{"code": c, "name": n} for c, n in failed_blocks],
        "total_links": total_links,
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
