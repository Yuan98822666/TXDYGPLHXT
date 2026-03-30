# -*- coding: utf-8 -*-
"""测试板块接口"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.request_util import EastMoneyRequest

# 测试 get_blocks（已验证成功）
blocks = EastMoneyRequest.get_blocks('concept')
print(f'概念板块数量: {len(blocks)}')

# 测试原始请求（添加 pn 参数）
cfg = EastMoneyRequest._get_endpoint('board_concept')
url = cfg.get('url')
print(f'URL: {url}')

params = {
    'pn': '1',  # 添加页码
    'np': cfg.get('np', '1'),
    'fltt': cfg.get('fltt', '2'),
    'invt': cfg.get('invt', '2'),
    'fs': cfg.get('fs'),
    'fields': cfg.get('fields'),
    'fid': cfg.get('fid'),
    'po': cfg.get('po', '1'),
    'pz': cfg.get('pz', '500'),
    'ut': cfg.get('ut'),
}

data = EastMoneyRequest.get_jsonp(url, params)
print(f'rc: {data.get("rc")}')
total = data.get('data', {}).get('total', 0) if data.get('data') else 0
print(f'total: {total}')
