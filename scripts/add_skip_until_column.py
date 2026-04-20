"""
数据库迁移脚本：为 base_stock 表添加 skip_until 字段

执行方式：
    python scripts/add_skip_until_column.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import get_db_context


def main():
    """添加 skip_until 字段"""
    print("=" * 50)
    print("数据库迁移：添加 skip_until 字段")
    print("=" * 50)
    
    with get_db_context() as db:
        # 检查字段是否已存在
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'base_stock' AND column_name = 'skip_until'
        """))
        
        if result.fetchone():
            print("✓ skip_until 字段已存在，无需迁移")
            return
        
        # 添加字段
        print("正在添加 skip_until 字段...")
        db.execute(text("""
            ALTER TABLE base_stock 
            ADD COLUMN skip_until TIMESTAMP WITH TIME ZONE NULL
        """))
        
        # 创建索引
        print("正在创建索引...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_base_stock_skip_until 
            ON base_stock(skip_until)
        """))
        
        # 添加注释
        db.execute(text("""
            COMMENT ON COLUMN base_stock.skip_until IS '跳过采集截止时间（UTC时区），设置后在此时间前不采集'
        """))
        
        db.commit()
        print("✓ 迁移完成！")
        print()
        print("字段说明：")
        print("  - skip_until: 跳过采集截止时间（可空）")
        print("  - 设置后，该股票在此时间前不会被采集")
        print("  - 用途：取消关注时可选择「三日内不再采集」")


if __name__ == "__main__":
    main()
