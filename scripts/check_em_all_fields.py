"""检查东方财富返回的所有字段"""
import sys
import json
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.request_util import EastMoneyRequest

result = EastMoneyRequest.get_stocks(1, 5)
if result:
    stocks = result.get('stocks', [])
    print("完整字段：")
    for i, item in enumerate(stocks[:3]):
        print(f"\n股票 {i+1}:")
        for k, v in item.items():
            print(f"  {k}: {v}")
