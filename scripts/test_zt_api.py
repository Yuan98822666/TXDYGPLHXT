# -*- coding: utf-8 -*-
"""测试涨停潜力API"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 测试统计API
print("=" * 60)
print("测试统计API")
print("=" * 60)
res = client.get('/api/analysis/zt-potential/stats?query_date=2026-06-02')
print(f"Status: {res.status_code}")
print(f"Response: {res.json()}")

# 测试排名API
print("\n" + "=" * 60)
print("测试排名API")
print("=" * 60)
res = client.get('/api/analysis/zt-potential/ranking?query_date=2026-06-02&page_size=5')
print(f"Status: {res.status_code}")
data = res.json()
print(f"Total: {data['total']}, Data count: {len(data['data'])}")
if data['data']:
    print(f"First item: {data['data'][0]}")

# 测试强度排名API
print("\n" + "=" * 60)
print("测试强度排名API")
print("=" * 60)
res = client.get('/api/analysis/zt-potential/strength-ranking?query_date=2026-06-02&page_size=5')
print(f"Status: {res.status_code}")
data = res.json()
print(f"Total: {data['total']}, Data count: {len(data['data'])}")
if data['data']:
    print(f"First item: {data['data'][0]}")

# 测试个股共振详情API
print("\n" + "=" * 60)
print("测试个股共振详情API")
print("=" * 60)
res = client.get('/api/analysis/zt-potential/stock/000001/resonance?query_date=2026-06-02')
print(f"Status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    print(f"Stock: {data['stock_code']} {data['stock_name']}")
    print(f"Total blocks: {data['total_blocks']}")
    print(f"Resonance blocks: {data['resonance_blocks']}")
else:
    print(f"Response: {res.json()}")

print("\n" + "=" * 60)
print("API测试完成")
print("=" * 60)
