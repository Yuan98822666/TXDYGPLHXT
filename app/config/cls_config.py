#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社 API 配置管理器

从 request_conf.yaml 读取财联社相关配置
支持动态更新 token/sign（从浏览器获取后修改配置文件即可）
"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache


# 配置文件路径
CONFIG_PATH = Path(__file__).parent / "request_conf.yaml"


@lru_cache(maxsize=1)
def _load_yaml_config() -> Dict:
    """加载 YAML 配置文件（带缓存）"""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_cls_common_params() -> Dict[str, str]:
    """
    获取财联社通用参数
    
    Returns:
        {
            'app': 'CailianpressWeb',
            'os': 'web', 
            'sv': '8.7.9',
            'token': 'xxx',
            'uid': 'xxx',
            'sign': 'xxx'  # 深度资讯接口需要
        }
    """
    config = _load_yaml_config()
    cls_common = config.get('cls_common', {})
    return {
        'app': cls_common.get('app', 'CailianpressWeb'),
        'os': cls_common.get('os', 'web'),
        'sv': cls_common.get('sv', '8.7.9'),
        'token': cls_common.get('token', ''),
        'uid': cls_common.get('uid', ''),
        'sign': cls_common.get('sign', ''),
    }


def get_cls_endpoint(name: str) -> Optional[str]:
    """
    获取财联社接口 URL
    
    Args:
        name: 接口名称
            - telegram_all: 全部电报
            - depth_headline: 头条消息
            - depth_a_share: A股消息
            - depth_company: 公司消息
            - depth_global: 环球消息
    
    Returns:
        接口 URL 或 None
    """
    config = _load_yaml_config()
    endpoints = config.get('cls_endpoints', {})
    endpoint = endpoints.get(name, {})
    return endpoint.get('url')


def get_telegram_params() -> Dict[str, str]:
    """
    获取电报接口专用参数
    
    Returns:
        {
            'name': 'telegraph',
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '8.7.9',
            'token': 'xxx',
            'uid': 'xxx'
        }
    """
    common = get_cls_common_params()
    return {
        'name': 'telegraph',
        **common
    }


def get_depth_params() -> Dict[str, str]:
    """
    获取深度资讯接口通用参数（包含 sign）
    
    Returns:
        {
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '8.7.9',
            'token': 'xxx',
            'uid': 'xxx',
            'sign': 'xxx'
        }
    """
    return get_cls_common_params()


def update_cls_config(token: str = None, uid: str = None, sign: str = None):
    """
    更新财联社配置（token/uid/sign）
    
    用法:
        # 从浏览器复制新 token 后更新
        update_cls_config(token='新token', uid='新uid')
    
    Args:
        token: 新的 token
        uid: 新的 uid
        sign: 新的 sign（可选，sign 通常需要动态计算）
    """
    config = _load_yaml_config()
    
    if 'cls_common' not in config:
        config['cls_common'] = {}
    
    if token:
        config['cls_common']['token'] = token
    if uid:
        config['cls_common']['uid'] = uid
    
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False)
    
    # 清除缓存，下次读取最新配置
    _load_yaml_config.cache_clear()
    print(f"财联社配置已更新: token={'***' if token else '未变更'}, uid={'***' if uid else '未变更'}")


# 快捷访问
TELEGRAM_URL = "https://www.cls.cn/api/cache"
DEPTH_BASE_URL = "https://www.cls.cn/v3/depth/home/assembled"


if __name__ == "__main__":
    # 测试配置读取
    print("=== 财联社配置测试 ===")
    print("\n通用参数:")
    print(get_cls_common_params())
    print("\n电报接口参数:")
    print(get_telegram_params())
    print("\n深度资讯接口:")
    for name in ['telegram_all', 'depth_headline', 'depth_a_share', 'depth_company', 'depth_global']:
        url = get_cls_endpoint(name)
        print(f"  {name}: {url}")
