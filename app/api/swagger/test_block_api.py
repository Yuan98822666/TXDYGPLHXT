"""
文件名：test_block_api.py
作用说明：
    使用 Swagger 测试 东方财富板块行情接口
    用于验证：
        1. 接口是否可访问
        2. 返回结构是否稳定
        3. 字段是否符合 RawBlockSnapshotEvent 设计预期

注意：
    本文件仅用于开发期接口验证
    不涉及任何入库逻辑
"""

import requests
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import json

router = APIRouter  (
    prefix="/test/block",  # 所有路由自动加此前缀
    tags=["板块测试"]       # 在 Swagger 中分组显示
)

# =========================================================
# 东方财富 行业板块行情接口（测试用）
# =========================================================
EASTMONEY_BLOCK_URL = "https://push2.eastmoney.com/api/qt/clist/get"


@router.get("/industry")
def test_industry_block_api():
    """
    测试 行业板块 行情接口

    返回：
        东方财富接口原始 JSON（不做任何处理）
    """

    params = {
        "pn": 1,
        "pz": 200,
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": "m:90+t:2",  # t:2 = 行业板块
        "fields": (
            "f12,f14,f2,f3,"
            "f62,f66,f72,f78,f84,"
            "f104,f105"
        )
    }

    resp = requests.get(EASTMONEY_BLOCK_URL, params=params, timeout=10)
    resp.raise_for_status()

    raw_json = resp.json()

    # =========================================================
    # 控制台打印（仅用于开发期观察）
    # =========================================================
    data_list = raw_json.get("data", {}).get("diff", [])

    print("\n" + "=" * 80)
    print("[DEBUG] 东方财富 行业板块接口 返回数据")
    print(f"[DEBUG] 板块数量: {len(data_list)}")

    # 只打印前 5 条，防止刷屏
    for idx, item in enumerate(data_list[:5], start=1):
        print(f"\n[DEBUG] --- 板块样本 #{idx} ---")
        print(json.dumps(item, ensure_ascii=False, indent=2))

    print("=" * 80 + "\n")

    return JSONResponse(content=raw_json)
