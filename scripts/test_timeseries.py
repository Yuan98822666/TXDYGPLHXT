# -*- coding: utf-8 -*-
"""测试 timeseries 接口时间轴"""
import requests

def test_timeseries():
    """测试 timeseries 接口"""
    resp = requests.get('http://localhost:8084/api/block-flow/timeseries?block_type=GN&query_date=2026-04-02', timeout=10)
    print(f'[/timeseries] Status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f"Date: {data.get('date')}")
        print(f"Time labels ({len(data.get('time_labels', []))}):")
        for t in data.get('time_labels', []):
            print(f"  {t}")
        print(f"\nBlocks count: {len(data.get('blocks', []))}")
    else:
        print(f'Error: {resp.text}')

if __name__ == "__main__":
    test_timeseries()
