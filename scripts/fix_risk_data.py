"""
修复 stock_risk 数据（当前值是反的）

修复逻辑：
- stock_risk=0 -> 改为 1（正常）
- stock_risk=1 -> 改为 0（风险）

但更准确的做法是：根据股票名称是否含 ST 来判断
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import get_db_context

def main():
    print("=" * 50)
    print("修复 stock_risk 数据")
    print("=" * 50)
    
    with get_db_context() as db:
        # 统计当前状态
        total = db.execute(text("SELECT COUNT(*) FROM base_stock")).scalar()
        risk0 = db.execute(text("SELECT COUNT(*) FROM base_stock WHERE stock_risk = 0")).scalar()
        risk1 = db.execute(text("SELECT COUNT(*) FROM base_stock WHERE stock_risk = 1")).scalar()
        
        print(f"当前状态：")
        print(f"  总数: {total}")
        print(f"  stock_risk=0: {risk0}")
        print(f"  stock_risk=1: {risk1}")
        print()
        
        # 方案：根据名称判断
        # 名称含 ST 或 *ST 的 -> stock_risk=0（风险）
        # 其他 -> stock_risk=1（正常）
        
        print("修复方案：根据股票名称判断风险状态")
        print("  名称含 ST/*ST -> stock_risk=0（风险）")
        print("  其他 -> stock_risk=1（正常）")
        print()
        
        # 执行修复
        # 先全部设为正常
        db.execute(text("UPDATE base_stock SET stock_risk = 1"))
        
        # 再把含 ST 的设为风险
        db.execute(text("""
            UPDATE base_stock 
            SET stock_risk = 0 
            WHERE stock_name LIKE '%ST%' OR stock_name LIKE '%%ST%%'
        """))
        
        db.commit()
        
        # 验证
        risk0_new = db.execute(text("SELECT COUNT(*) FROM base_stock WHERE stock_risk = 0")).scalar()
        risk1_new = db.execute(text("SELECT COUNT(*) FROM base_stock WHERE stock_risk = 1")).scalar()
        
        print(f"修复后：")
        print(f"  stock_risk=0（风险）: {risk0_new}")
        print(f"  stock_risk=1（正常）: {risk1_new}")
        print()
        
        # 抽样验证
        print("抽样验证：")
        st_samples = db.execute(text("""
            SELECT stock_code, stock_name, stock_risk 
            FROM base_stock 
            WHERE stock_name LIKE '%ST%' OR stock_name LIKE '%%ST%%'
            LIMIT 5
        """)).fetchall()
        print("  ST股票（应为risk=0）:")
        for s in st_samples:
            print(f"    {s[0]} {s[1]} -> risk={s[2]} {'OK' if s[2]==0 else 'ERROR'}")
        
        normal_samples = db.execute(text("""
            SELECT stock_code, stock_name, stock_risk 
            FROM base_stock 
            WHERE stock_name NOT LIKE '%ST%' AND stock_name NOT LIKE '%%ST%%'
            LIMIT 5
        """)).fetchall()
        print("  正常股票（应为risk=1）:")
        for s in normal_samples:
            print(f"    {s[0]} {s[1]} -> risk={s[2]} {'OK' if s[2]==1 else 'ERROR'}")
        
        print()
        print("Done!")

if __name__ == "__main__":
    main()
