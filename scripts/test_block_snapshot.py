# -*- coding: utf-8 -*-
"""测试板块快照接口"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.request_util import EastMoneyRequest
from app.utils.cookie_manager import CookieManager
from curl_cffi.requests import Session
import json

print('测试板块快照接口...')

# 获取 Cookie
cookies = CookieManager.get_cookies()

# 测试不同的 fs 参数
session = Session(impersonate="chrome120")

test_cases = [
    ("概念板块", "m:90+t:3"),
    ("行业板块", "m:90+s:4"),
    ("风格板块", "m:90+t:2"),
]

for name, fs in test_cases:
    params = {
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fs": fs,
        "fields": "f12,f14,f2,f3",
        "fid": "f3",
        "po": "1",
        "pz": "5",
        "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
        "cb": "jQuery1",
    }
    
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    resp = session.get(url, params=params, cookies=cookies, timeout=10)
    
    # 解析 JSONP
    import re
    match = re.search(r'jQuery\d+\((.*)\)', resp.text)
    if match:
        data = json.loads(match.group(1))
        rc = data.get('rc')
        total = data.get('data', {}).get('total', 0) if data.get('data') else 0
        print(f'{name}: rc={rc}, total={total}')
    else:
        print(f'{name}: 解析失败')
