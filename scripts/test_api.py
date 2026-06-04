# -*- coding: utf-8 -*-
"""测试API接口"""
import requests
import json

def test_stats():
    """测试 stats 接口"""
    resp = requests.get('http://localhost:8084/api/block-flow/stats?query_date=2026-04-02', timeout=10)
    print(f'[/stats] Status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f'Response keys: {list(data.keys())}')
        print(f"Concept: total={data.get('concept', {}).get('total')}, active={data.get('concept', {}).get('active')}, top5_count={len(data.get('concept', {}).get('top5', []))}")
        print(f"Industry: total={data.get('industry', {}).get('total')}, active={data.get('industry', {}).get('active')}, top5_count={len(data.get('industry', {}).get('top5', []))}")
    else:
        print(f'Error: {resp.text}')

def test_timeseries():
    """测试 timeseries 接口"""
    resp = requests.get('http://localhost:8084/api/block-flow/timeseries?block_type=GN&query_date=2026-04-02', timeout=10)
    print(f'[/timeseries] Status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f'Response keys: {list(data.keys())}')
        print(f"Date: {data.get('date')}")
        print(f"Time labels count: {len(data.get('time_labels', []))}")
        print(f"Blocks count: {len(data.get('blocks', []))}")
        if data.get('blocks'):
            print(f"First block: {data['blocks'][0]}")
    else:
        print(f'Error: {resp.text}')

def test_stocks():
    """测试 stocks 接口"""
    resp = requests.get('http://localhost:8084/api/block-flow/stocks?query_date=2026-04-02&page=1&size=5', timeout=10)
    print(f'[/stocks] Status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f'Response keys: {list(data.keys())}')
        print(f"Total: {data.get('total')}")
        print(f"Stocks count: {len(data.get('stocks', []))}")
        if data.get('stocks'):
            print(f"First stock: {data['stocks'][0]}")
    else:
        print(f'Error: {resp.text}')

if __name__ == "__main__":
    print("=" * 50)
    test_stats()
    print("=" * 50)
    test_timeseries()
    print("=" * 50)
    test_stocks()
