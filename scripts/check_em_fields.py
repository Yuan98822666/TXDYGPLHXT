"""检查东方财富返回的字段"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.request_util import EastMoneyRequest

result = EastMoneyRequest.get_stocks(1, 20)
if result:
    stocks = result.get('stocks', [])
    print("字段示例：")
    for item in stocks[:10]:
        code = item.get('f12')
        name = item.get('f14')
        short = item.get('f152')
        f13 = item.get('f13')
        # 打印所有字段
        print(f"{code} {name} | f152={short} | f13={f13}")
