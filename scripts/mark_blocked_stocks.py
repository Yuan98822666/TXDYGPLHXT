# -*- coding: utf-8 -*-
"""
标记受限股票脚本

功能：
1. 将 ST/*ST/退市股票 (stock_risk=0) 的 skip_until 设置为7年后
2. 将 科创板(KCB)、创业板(CYB)、北交所(BJS) 股票的 skip_until 设置为7年后
3. 如果股票已被标记为关注(stock_imp=1)，则取消关注

执行方式:
    python scripts/mark_blocked_stocks.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from app.db.session import get_db_context
from app.models.base.base_stock import BaseStock

# 配置
SKIP_YEARS = 7  # 跳过采集年限
BLOCKED_STOCK_TYPES = {"KCB", "CYB", "BJS"}  # 科创板、创业板、北交所


def mark_blocked_stocks():
    """标记所有受限股票"""
    
    skip_until_date = datetime.now(timezone.utc) + timedelta(days=365 * SKIP_YEARS)
    
    with get_db_context() as db:
        # 查询所有受限股票
        # 条件1: stock_risk = 0 (ST/*ST/退市)
        # 条件2: stock_type in (KCB, CYB, BJS) (科创板、创业板、北交所)
        blocked_stocks = db.query(BaseStock).filter(
            or_(
                BaseStock.stock_risk == 0,
                BaseStock.stock_type.in_(BLOCKED_STOCK_TYPES)
            )
        ).all()
        
        if not blocked_stocks:
            print("没有找到需要标记的受限股票")
            return
        
        print(f"找到 {len(blocked_stocks)} 只受限股票需要处理")
        print(f"跳过采集截止时间将设置为: {skip_until_date.strftime('%Y-%m-%d %H:%M:%S')} (7年后)")
        print("-" * 80)
        
        # 分类统计
        risk_stocks = []  # 风险股
        kcb_stocks = []   # 科创板
        cyb_stocks = []   # 创业板
        bjs_stocks = []   # 北交所
        
        marked_count = 0  # 被取消关注的数量
        
        for stock in blocked_stocks:
            # 如果已被关注，取消关注
            if stock.stock_imp == 1:
                stock.stock_imp = 0
                marked_count += 1
            
            # 设置跳过采集时间
            stock.skip_until = skip_until_date
            
            # 分类记录
            if stock.stock_risk == 0:
                risk_stocks.append(stock)
            elif stock.stock_type == "KCB":
                kcb_stocks.append(stock)
            elif stock.stock_type == "CYB":
                cyb_stocks.append(stock)
            elif stock.stock_type == "BJS":
                bjs_stocks.append(stock)
        
        # 提交事务
        db.commit()
        
        # 输出统计
        print("\n处理结果统计:")
        print("-" * 80)
        print(f"ST/*ST/退市股票 (stock_risk=0): {len(risk_stocks)} 只")
        print(f"科创板股票 (KCB): {len(kcb_stocks)} 只")
        print(f"创业板股票 (CYB): {len(cyb_stocks)} 只")
        print(f"北交所股票 (BJS): {len(bjs_stocks)} 只")
        print("-" * 80)
        print(f"总计: {len(blocked_stocks)} 只股票")
        print(f"取消关注: {marked_count} 只")
        print(f"\n所有受限股票已标记 skip_until 至 {skip_until_date.strftime('%Y-%m-%d')}")
        
        # 输出部分示例
        if risk_stocks:
            print("\n风险股示例 (前5只):")
            for s in risk_stocks[:5]:
                print(f"  - {s.stock_code} {s.stock_name}")
        
        if kcb_stocks:
            print("\n科创板示例 (前5只):")
            for s in kcb_stocks[:5]:
                print(f"  - {s.stock_code} {s.stock_name}")
        
        if cyb_stocks:
            print("\n创业板示例 (前5只):")
            for s in cyb_stocks[:5]:
                print(f"  - {s.stock_code} {s.stock_name}")
        
        if bjs_stocks:
            print("\n北交所示例 (前5只):")
            for s in bjs_stocks[:5]:
                print(f"  - {s.stock_code} {s.stock_name}")


if __name__ == "__main__":
    print("=" * 80)
    print("受限股票标记脚本")
    print("=" * 80)
    print()
    
    try:
        mark_blocked_stocks()
        print("\n[OK] 执行完成")
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
