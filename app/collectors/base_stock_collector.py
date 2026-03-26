"""
文件路径：app/collectors/base_stock_collector.py
作用说明：基础股票数据采集器

职责边界：
  - 只负责一件事：从东方财富 API 采集股票基础信息，写入 base_stock 表
  - 不做数据转换、不做业务判断

数据流向：
  东方财富 API → 本模块采集函数 → base_stock 表（Upsert）

模块化设计：
  - _fetch_stocks_data()  : 私有，从接口分页采集所有股票
  - collect_base_stocks() : 公开入口，采集+清洗+写入数据库

设计原则：
  - 高内聚：只做股票采集一件事
  - 低耦合：通过配置文件获取接口参数，不硬编码
  - UPSERT 策略：存在则更新名称和风险状态，不存在则新增
  - 字段保护：stock_imp（自选标记）由其他模块维护，Upsert 时不覆盖
"""

from typing import Dict
from app.models.base.base_stock import BaseStock
from sqlalchemy.dialects.postgresql import insert
from app.db.session import get_db_context
from app.utils.http_client import eastmoney_client
from app.utils.stock_type import get_stock_type
from app.config.settings import settings
from datetime import datetime, timezone
import time


# =========================================================
# 私有函数：分页采集股票数据
# =========================================================

def _fetch_stocks_data() -> Dict[str, Dict]:
    """
    从东方财富接口分页采集所有上市股票的基础数据

    分页逻辑：
      - 每页 pz=100 条，逐页翻取
      - 当返回数据 < 100 条时，认为已到最后一页
      - 最多翻 common.max_pages 页，防止异常情况下的无限翻页

    返回:
        Dict[str, Dict]: 以 stock_code 为 key 的股票字典
            {
                "000001": {"name": "平安银行", "risk": 1},
                "600519": {"name": "贵州茅台", "risk": 1},
                ...
            }
    """
    config = settings.request_config
    common = config.common
    endpoint = config.endpoints["base_stocks"]

    # 构建请求参数（合并通用参数 + base_stocks 端点特有参数）
    base_params = {
        "fid": endpoint.fid,
        "po": endpoint.po,
        "pz": endpoint.pz,          # 每页100条（从 yaml 配置读取，不硬编码）
        "np": endpoint.np,
        "fltt": endpoint.fltt,
        "invt": endpoint.invt,
        "fs": endpoint.fs,          # 筛选条件：沪深全市场（从 yaml 配置读取）
        "fields": endpoint.fields,  # 返回字段：f12,f13,f14,f152（从 yaml 配置读取）
        "ut": common.ut,
        "cb": common.cb,
    }

    # stock_code → {name, risk} 的映射
    code_map: Dict[str, Dict] = {}
    pn = 1

    while pn <= common.max_pages:
        params = {**base_params, "pn": pn}

        try:
            data = eastmoney_client.get_jsonp(endpoint.url, params)
        except Exception as e:

            print(f"⚠️  股票第 {pn} 页请求失败: {e}")
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
            stock_name = item.get("f14")
            stock_short = item.get("f152", "")
            exchange = str(item.get("f13", ""))  # 0=深市, 1=沪市

            if stock_code and stock_name:
                # 判断风险状态：通过股票简称判断是否为 *ST 或 ST
                short_str = str(stock_short) if stock_short else ""
                is_st = short_str.startswith("*ST") or short_str.startswith("ST")
                risk = 0 if is_st else 1

                # 判断板块类型（SH_ZB/KCB/SZ_ZB/CYB/BJS）
                stock_type = get_stock_type(stock_code, exchange)

                # secid 格式：exchange.stock_code（东方财富个股接口专用标识）
                # 例如：0.000001（深市平安银行）、1.600519（沪市贵州茅台）
                secid = f"{exchange}.{stock_code}"

                code_map[stock_code] = {
                    "name": stock_name,
                    "exchange": exchange,
                    "secid": secid,
                    "type": stock_type,
                    "risk": risk,
                }

        # 判断是否已到最后一页（返回数量 < 每页数量）
        page_count = len(diff) if isinstance(diff, list) else len(diff.values())
        if page_count < int(endpoint.pz):
            break

        pn += 1

    return code_map


# =========================================================
# 公开函数：采集所有股票并写入数据库
# =========================================================

def collect_base_stocks() -> Dict[str, int]:
    """
    采集所有上市股票的基础信息并更新数据库

    采集流程:
        1. 调用 _fetch_stocks_data() 分页采集所有股票
        2. 数据清洗：
           - 判断风险状态（*ST/ST → risk=0，其他 → risk=1）
           - 判断板块类型（SH_ZB/KCB/SZ_ZB/CYB/BJS）
        3. 查询数据库现有记录，区分更新和新增
        4. 使用 PostgreSQL Upsert 语法写入 base_stock 表
           - stock_code 已存在 → 更新所有字段（stock_imp 除外）
           - stock_code 不存在 → 新增记录
        5. 返回采集统计信息

    返回:
        Dict[str, int]: 采集统计信息
            - updated        : 更新记录数
            - inserted      : 新增记录数
            - total         : 总处理数
            - elapsed_seconds: 耗时（秒）
    """
    start_time = time.time()
    print("📊 开始采集基础股票数据...")

    # ─── Step 1: 采集 ─────────────────────────────────────────
    code_map = _fetch_stocks_data()
    print(f"📈 接口返回 {len(code_map)} 条股票数据")

    if not code_map:
        print("⚠️  没有股票数据，跳过写入")
        return {"updated": 0, "inserted": 0, "total": 0, "elapsed_seconds": 0}

    # ─── Step 2: 查询现有记录，区分更新/新增 ───────────────────
    with get_db_context() as db:
        existing_codes = {
            row.stock_code
            for row in db.query(BaseStock.stock_code).all()
        }

    updated_count = sum(1 for code in code_map if code in existing_codes)
    inserted_count = len(code_map) - updated_count

    # ─── Step 3: Upsert 写入 ───────────────────────────────────
    values = [
        {
            "stock_code": code,
            "stock_name": info["name"],
            "exchange": info["exchange"],
            "secid": info["secid"],
            "stock_type": info["type"],  # 板块类型（SH_ZB/KCB/SZ_ZB/CYB/BJS）
            "stock_risk": info["risk"],
            "stock_imp": 0,             # 默认未添加自选，后续由用户操作维护
            "pdate_time": datetime.now(timezone.utc),
        }
        for code, info in code_map.items()
    ]

    with get_db_context() as db:
        try:
            # PostgreSQL Upsert 语法
            # INSERT ... ON CONFLICT (stock_code) DO UPDATE SET ...
            stmt = insert(BaseStock).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_code"],
                set_={
                    # 已存在时更新：名称、交易所标识、secid、板块类型、风险状态、时间
                    "stock_name": stmt.excluded.stock_name,
                    "exchange": stmt.excluded.exchange,
                    "secid": stmt.excluded.secid,
                    "stock_type": stmt.excluded.stock_type,
                    "stock_risk": stmt.excluded.stock_risk,
                    "pdate_time": stmt.excluded.pdate_time,
                    # stock_imp 不在 set_ 中，保留原值（用户自选标记不被覆盖）
                }
            )
            db.execute(stmt)
            db.commit()
            print(f"\n✅ 数据库写入成功")

        except Exception as e:
            db.rollback()
            print(f"❌ 数据库写入失败: {e}")
            raise

    # ─── Step 4: 返回统计 ─────────────────────────────────────
    elapsed_seconds = time.time() - start_time
    print(f"\n📊 股票采集统计:")
    print(f"   - 更新: {updated_count} 条")
    print(f"   - 新增: {inserted_count} 条")
    print(f"   - 总计: {len(code_map)} 条")
    print(f"   - 耗时: {elapsed_seconds:.2f} 秒")

    return {
        "updated": updated_count,
        "inserted": inserted_count,
        "total": len(code_map),
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
