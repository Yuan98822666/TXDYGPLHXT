# -*- coding: utf-8 -*-
"""
一次性脚本：导入申万三级行业分类数据

步骤：
1. 创建 base_industry 表
2. 给 base_stock 表新增 sw_industry_l1/l2/l3 字段
3. 解析板块.txt 中的 bk1/bk2/bk3 写入 base_industry
4. 解析 baseinfo 更新 base_stock 的行业字段
5. 验证数据完整性

使用方式：
    cd E:\Python Project\TXDYGPLHXT
    python scripts/import_industry.py
"""
import sys
import os
import json
from datetime import datetime, timezone

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect as sa_inspect
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.base import BaseIndustry, BaseStock


DATA_FILE = r"C:\Users\Yuan9\Desktop\板块.txt"


def load_data():
    """加载板块.txt JSON数据"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_tables():
    """确保表结构存在"""
    print("=" * 60)
    print("步骤1: 检查/创建表结构")
    print("=" * 60)

    # 创建 base_industry 表（如果不存在）
    BaseIndustry.__table__.create(engine, checkfirst=True)
    print("  [OK] base_industry 表就绪")

    # 检查 base_stock 是否已有 sw_industry_l1 字段
    inspector = sa_inspect(engine)
    stock_columns = [col["name"] for col in inspector.get_columns("base_stock")]

    alter_sqls = []
    for col_name in ["sw_industry_l1", "sw_industry_l2", "sw_industry_l3"]:
        if col_name not in stock_columns:
            alter_sqls.append(
                f'ALTER TABLE base_stock ADD COLUMN {col_name} VARCHAR(20)'
            )

    if alter_sqls:
        with engine.connect() as conn:
            for sql in alter_sqls:
                conn.execute(text(sql))
                print(f"  [OK] {sql}")
            conn.commit()
        print("  [OK] base_stock 新增字段完成")
    else:
        print("  [OK] base_stock sw_industry 字段已存在，跳过")

    print()


def import_industries(data):
    """导入行业分类数据（bk1/bk2/bk3 → base_industry）"""
    print("=" * 60)
    print("步骤2: 导入行业分类数据 → base_industry")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 先清空旧数据（幂等）
        db.execute(text("DELETE FROM base_industry"))
        db.commit()

        total = 0

        # 解析 bk1 → 一级行业
        # 格式: "行业名称|数字|BK代码"
        bk1_list = data["bk1"]
        l1_code_to_name = {}  # id → industry_code 映射（供后续构建 parent_code）

        for idx, item in enumerate(bk1_list):
            parts = item.split("|")
            name = parts[0]
            bk_code = parts[2]
            industry_code = f"L1_{idx}"
            l1_code_to_name[idx] = industry_code

            row = BaseIndustry(
                level=1,
                industry_code=industry_code,
                industry_name=name,
                em_bk_code=bk_code,
                parent_code=None,
                sort_order=idx,
            )
            db.add(row)
            total += 1

        db.commit()
        print(f"  [OK] 一级行业: {len(bk1_list)} 条")

        # 解析 bk2 → 二级行业
        # 需要从 baseinfo 中提取 二级ID→一级ID 的映射
        # 先扫描 baseinfo 建立 l2_id → l1_id 映射
        l2_to_l1 = {}
        for line in data["baseinfo"]:
            parts = line.strip(",").split("|")
            if len(parts) >= 6:
                l1_id, l2_id = int(parts[0]), int(parts[1])
                l2_to_l1[l2_id] = l1_id  # 同一个 l2_id 总是映射到同一个 l1_id

        bk2_list = data["bk2"]
        l2_code_to_name = {}

        for idx, item in enumerate(bk2_list):
            parts = item.split("|")
            name = parts[0]
            bk_code = parts[2]
            industry_code = f"L2_{idx}"
            l2_code_to_name[idx] = industry_code

            parent_code = l1_code_to_name.get(l2_to_l1.get(idx))

            row = BaseIndustry(
                level=2,
                industry_code=industry_code,
                industry_name=name,
                em_bk_code=bk_code,
                parent_code=parent_code,
                sort_order=idx,
            )
            db.add(row)
            total += 1

        db.commit()
        print(f"  [OK] 二级行业: {len(bk2_list)} 条")

        # 解析 bk3 → 三级行业
        # 同理，需要 l3_id → l2_id 映射
        l3_to_l2 = {}
        for line in data["baseinfo"]:
            parts = line.strip(",").split("|")
            if len(parts) >= 6:
                l2_id, l3_id = int(parts[1]), int(parts[2])
                l3_to_l2[l3_id] = l2_id

        bk3_list = data["bk3"]
        for idx, item in enumerate(bk3_list):
            parts = item.split("|")
            name = parts[0]
            bk_code = parts[2]
            industry_code = f"L3_{idx}"

            parent_code = l2_code_to_name.get(l3_to_l2.get(idx))

            row = BaseIndustry(
                level=3,
                industry_code=industry_code,
                industry_name=name,
                em_bk_code=bk_code,
                parent_code=parent_code,
                sort_order=idx,
            )
            db.add(row)
            total += 1

        db.commit()
        print(f"  [OK] 三级行业: {len(bk3_list)} 条")
        print(f"  [OK] base_industry 总计: {total} 条")

    finally:
        db.close()

    print()


def import_stock_industries(data):
    """导入股票行业映射（baseinfo → base_stock 更新）"""
    print("=" * 60)
    print("步骤3: 更新股票行业字段 → base_stock")
    print("=" * 60)

    db = SessionLocal()
    try:
        updated = 0
        not_found = 0
        no_l3 = 0

        for line in data["baseinfo"]:
            parts = line.strip(",").split("|")
            if len(parts) < 6:
                continue

            l1_id = parts[0]
            l2_id = parts[1]
            l3_id = parts[2]
            stock_name = parts[3]
            stock_code = parts[5]

            # 检查三级分类
            if int(l3_id) == 0 and l1_id == "0" and l2_id == "0":
                no_l3 += 1

            # 更新 base_stock
            result = db.execute(
                text(
                    "UPDATE base_stock SET sw_industry_l1 = :l1, "
                    "sw_industry_l2 = :l2, sw_industry_l3 = :l3 "
                    "WHERE stock_code = :code"
                ),
                {
                    "l1": f"L1_{l1_id}",
                    "l2": f"L2_{l2_id}",
                    "l3": f"L3_{l3_id}",
                    "code": stock_code,
                },
            )
            if result.rowcount > 0:
                updated += 1
            else:
                not_found += 1

        db.commit()
        print(f"  [OK] 匹配并更新: {updated} 条")
        if not_found > 0:
            print(f"  [!] 板块.txt中有但base_stock中不存在: {not_found} 条")
        if no_l3 > 0:
            print(f"  [!] 无行业分类（L1_0/L2_0/L3_0）: {no_l3} 条")

    finally:
        db.close()

    print()


def verify():
    """验证数据完整性"""
    print("=" * 60)
    print("步骤4: 验证数据完整性")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. base_industry 行数
        for level in [1, 2, 3]:
            count = db.execute(
                text("SELECT COUNT(*) FROM base_industry WHERE level = :lv"),
                {"lv": level},
            ).scalar()
            print(f"  base_industry level={level}: {count} 条")

        # 2. base_stock 行业字段覆盖率
        total_stocks = db.execute(text("SELECT COUNT(*) FROM base_stock")).scalar()
        with_l1 = db.execute(
            text("SELECT COUNT(*) FROM base_stock WHERE sw_industry_l1 IS NOT NULL")
        ).scalar()
        with_l2 = db.execute(
            text("SELECT COUNT(*) FROM base_stock WHERE sw_industry_l2 IS NOT NULL")
        ).scalar()
        with_l3 = db.execute(
            text("SELECT COUNT(*) FROM base_stock WHERE sw_industry_l3 IS NOT NULL")
        ).scalar()

        print(f"\n  base_stock 总数: {total_stocks}")
        print(f"  有一级分类: {with_l1} ({with_l1*100//total_stocks}%)")
        print(f"  有二级分类: {with_l2} ({with_l2*100//total_stocks}%)")
        print(f"  有三级分类: {with_l3} ({with_l3*100//total_stocks}%)")

        # 3. 无行业分类的股票
        no_industry = db.execute(
            text(
                "SELECT COUNT(*) FROM base_stock WHERE sw_industry_l1 IS NULL"
            )
        ).scalar()
        if no_industry > 0:
            print(f"\n  [!] 无行业分类的股票: {no_industry} 条")
            # 看看是哪些
            samples = db.execute(
                text(
                    "SELECT stock_code, stock_name FROM base_stock "
                    "WHERE sw_industry_l1 IS NULL LIMIT 10"
                )
            ).fetchall()
            for row in samples:
                print(f"      {row[0]} {row[1]}")

        # 4. L1_0 是什么？（第一个行业分类）
        l1_0 = db.execute(
            text(
                "SELECT industry_name, em_bk_code FROM base_industry "
                "WHERE industry_code = 'L1_0'"
            )
        ).fetchone()
        if l1_0:
            print(f"\n  L1_0 = {l1_0[0]} (BK: {l1_0[1]})")

        # 5. 验证层级关系：每个三级是否有二级parent，每个二级是否有一级parent
        orphan_l2 = db.execute(
            text(
                "SELECT COUNT(*) FROM base_industry "
                "WHERE level = 2 AND parent_code IS NULL"
            )
        ).scalar()
        orphan_l3 = db.execute(
            text(
                "SELECT COUNT(*) FROM base_industry "
                "WHERE level = 3 AND parent_code IS NULL"
            )
        ).scalar()
        print(f"\n  二级行业无parent: {orphan_l2}")
        print(f"  三级行业无parent: {orphan_l3}")

        # 6. 展示一棵完整的三级行业树（示例）
        print("\n  示例：银行业完整三级行业树")
        banks = db.execute(
            text(
                "SELECT level, industry_code, industry_name, em_bk_code, parent_code "
                "FROM base_industry WHERE industry_name LIKE '%银行%' "
                "ORDER BY level, sort_order"
            )
        ).fetchall()
        for row in banks:
            indent = "    " * (row[0] - 1)
            print(f"  {indent}{row[1]} → {row[2]} ({row[3]}, parent={row[4]})")

    finally:
        db.close()

    print()


def main():
    print("申万三级行业分类数据导入")
    print(f"数据文件: {DATA_FILE}")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 加载数据
    data = load_data()
    print(f"板块.txt 加载成功: {len(data['baseinfo'])} 只股票")
    print(f"  bk1: {len(data['bk1'])} 条 | bk2: {len(data['bk2'])} 条 | bk3: {len(data['bk3'])} 条")
    print()

    # 1. 建表
    ensure_tables()

    # 2. 导入行业分类
    import_industries(data)

    # 3. 导入股票行业映射
    import_stock_industries(data)

    # 4. 验证
    verify()

    print("=" * 60)
    print("导入完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
