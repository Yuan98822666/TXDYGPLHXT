"""
东方财富数据采集 HTTP 客户端

功能说明：
- 使用 curl_cffi 替代 requests，彻底解决 TLS 指纹检测问题
- 自动模拟 Chrome / Edge / Firefox 浏览器的 TLS JA3 指纹
- 模拟真实浏览器的请求头（包括 Sec-CH-UA、Viewport 等）
- 解析 JSONP 响应并转换为标准 Python 字典
- 全局单例模式，复用 Session 提升性能

设计特点：
- curl_cffi 基于 pycurl + undici，性能优于 requests
- impersonate="chrome" 自动匹配最新版 Chrome TLS 指纹
- 随机延迟（0.1-0.3秒）避免请求过于频繁被限流
- 严格的 JSONP 解析验证，防止 HTML 错误页干扰
"""

import time
import random
import json
from typing import Dict, Any
from curl_cffi.requests import Session


class EastMoneyClient:
    """东方财富专用 HTTP 客户端（curl_cffi 驱动）"""

    def __init__(self, impersonate: str = "chrome120"):
        """
        初始化客户端，模拟真实浏览器 TLS 指纹 + 请求头

        参数:
            impersonate (str): 模拟的浏览器指纹，支持:
                - "chrome120" / "chrome"  → Chrome 120
                - "edge101"              → Edge 101
                - "firefox110"           → Firefox 110
                - "safari15_5"           → Safari 15.5
        """
        self.session = Session(impersonate=impersonate)

        # ─── 模拟 Windows 真实浏览器请求头 ───────────────────────────────
        # 这些头在浏览器开发者工具 Network 面板里可以看到
        self.session.headers.update({
            # 基础身份头
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            ),
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Accept-Encoding": "gzip, deflate, br",

            # ─── Sec-CH-UA 系列（Chrome 99+ 特有，爬虫必带）───────────────
            "Sec-Ch-Ua": (
                '"Not_A Brand";v="8", "Chromium";v="120", '
                '"Microsoft Edge";v="120", "Chromium";v="120"'
            ),
            "Sec-Ch-Ua-Mobile": "?0",                              # 桌面端，非手机
            "Sec-Ch-Ua-Platform": '"Windows"',                      # Windows 系统
            "Sec-Ch-Ua-Platform-Version": '"15.0.0"',              # Windows 10

            # ─── Windows 视口尺寸（关键！告诉服务器你的窗口大小）───────────
            # 常见分辨率组合：
            #   1920x1080  → 笔记本常见
            #   1536x864   → 笔记本缩放后
            #   1366x768   → 经典笔记本
            #   2560x1440  → 桌面常见
            "Sec-Ch-Width": str(random.choice([1920, 1536, 1366, 2560])),
            "Sec-Ch-Height": str(random.choice([1080, 864, 768, 1440])),
            "Sec-Ch-Viewport-Width": str(random.choice([1920, 1536, 1366, 2560])),
            "Sec-Ch-Viewport-Height": str(random.choice([1080, 864, 768, 1440])),
            "Sec-Ch-Device-Memory": "8",        # 设备内存（GB）
            "Sec-Ch-Rtt": "50",                 # 网络延迟（ms）
            "Sec-Ch-Downlink": "10",            # 下载速度（Mbps）
            "Sec-Ch-Ect": "4g",                # 网络类型 4G

            # ─── 浏览器特性开关（告诉服务器支持哪些 Web API）───────────────
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",

            # ─── 固定版本信息（和 User-Agent 对应）────────────────────
            "X-Requested-With": "XMLHttpRequest",
        })

    def get_jsonp(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 GET 请求获取 JSONP 数据并解析为字典

        参数:
            url (str):  API 接口完整 URL
            params (Dict[str, Any]): 请求参数字典

        返回:
            Dict[str, Any]: 解析后的 JSON 数据字典

        异常:
            curl_cffi.exceptions.RequestsError: HTTP 请求失败
            ValueError: 响应不是有效的 JSONP 格式
        """
        # 随机延迟，避免请求过于频繁被限流
        time.sleep(random.uniform(0.1, 0.3))

        # ─── 每次请求随机化视口尺寸 ───────────────────────────────────
        # 让不同请求看起来来自不同的窗口大小，进一步模拟真实用户
        width  = random.choice([1920, 1536, 1366, 2560])
        height = random.choice([1080, 864,  768,  1440])
        self.session.headers["Sec-Ch-Width"]           = str(width)
        self.session.headers["Sec-Ch-Height"]          = str(height)
        self.session.headers["Sec-Ch-Viewport-Width"]  = str(width)
        self.session.headers["Sec-Ch-Viewport-Height"] = str(height)

        # ─── 发送请求 ────────────────────────────────────────────────
        # timeout: 连接超时 / 读取超时（秒）
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()  # 抛出 HTTP 错误（4xx/5xx）

        text = resp.text.strip()

        # ─── 安全剥离 JSONP ─────────────────────────────────────────
        if not text.startswith("jQuery") or "(" not in text or not text.endswith(");"):
            raise ValueError(f"Unexpected response (not JSONP): {text[:300]}...")

        start = text.find("(")
        end   = text.rfind(")")
        if start == -1 or end == -1 or start >= end:
            raise ValueError(f"Cannot parse JSONP from response: {text[:200]}...")

        json_str = text[start + 1:end]

        # ─── 解析 JSON ─────────────────────────────────────────────
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON: {e}. Raw: {json_str[:300]}...")


# 全局单例实例，确保整个应用复用同一个 Session
eastmoney_client = EastMoneyClient(impersonate="chrome120")
