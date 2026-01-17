"""
东方财富数据采集 HTTP 客户端

功能说明：
- 封装对东方财富 API 的 JSONP 请求
- 自动处理反爬机制（User-Agent、Referer 等）
- 解析 JSONP 响应并转换为标准 Python 字典
- 全局单例模式，复用 Session 提升性能

设计特点：
- 模拟真实浏览器请求头，降低被封风险
- 随机延迟（0.1-0.3秒）避免请求过于频繁
- 严格的 JSONP 解析验证，防止 HTML 错误页干扰
"""

import requests
from typing import  Dict, Any
from requests.adapters import HTTPAdapter

import time
import random
import json


class EastMoneyClient:
    """东方财富专用 HTTP 客户端"""

    def __init__(self):
        """初始化客户端，设置通用请求头模拟浏览器"""
        self.session = requests.Session()
        # 设置通用 headers 模拟浏览器，避免被反爬
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/",  # 必须的来源引用
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        # === 2. 扩大连接池容量（关键优化！）===
        # pool_connections: 缓存多少个不同 host 的连接池（我们主要用 push2.eastmoney.com）
        # pool_maxsize: 每个 host 最多允许的并发连接数（必须 ≥ ThreadPoolExecutor 的 max_workers）
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=30,  # 支持最多 30 个并发连接
            max_retries=0  # 不自动重试（由上层逻辑控制更合适）
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_jsonp(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 GET 请求获取 JSONP 数据并解析为字典

        参数:
            url (str): API 接口完整 URL
            params (Dict[str, Any]): 请求参数字典

        返回:
            Dict[str, Any]: 解析后的 JSON 数据字典

        异常:
            requests.HTTPError: HTTP 请求失败
            ValueError: 响应不是有效的 JSONP 格式

        内部逻辑:
            1. 随机延迟 0.1-0.3 秒，模拟人工操作
            2. 发送 GET 请求并检查 HTTP 状态
            3. 验证响应是否为 JSONP 格式（以 jQuery 开头，以 ); 结尾）
            4. 提取括号内的 JSON 字符串
            5. 解析 JSON 并返回 Python 字典
        """
        # 随机延迟，避免请求过于频繁被限流
        time.sleep(random.uniform(0.1, 0.3))

        # 发送 HTTP 请求
        resp = self.session.get(url, params=params)
        resp.raise_for_status()  # 抛出 HTTP 错误

        text = resp.text.strip()

        # 安全剥离 JSONP - 验证基本格式
        if not text.startswith("jQuery") or "(" not in text or not text.endswith(");"):
            # 可能是 HTML 错误页或服务不可用
            raise ValueError(f"Unexpected response (not JSONP): {text[:200]}...")

        # 提取 JSONP 中的 JSON 部分
        start = text.find('(')
        end = text.rfind(')')
        if start == -1 or end == -1 or start >= end:
            raise ValueError(f"Cannot parse JSONP from response: {text[:200]}...")

        json_str = text[start + 1:end]

        # 解析 JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON: {e}. Raw: {json_str[:200]}...")


# 全局单例实例，确保整个应用复用同一个 Session
eastmoney_client = EastMoneyClient()