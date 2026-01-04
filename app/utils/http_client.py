# app/utils/http_client.py  这里用的是.env
import requests
from typing import Optional, Dict, Any
import time
import random
from app.config.settings import settings
import json

class EastMoneyClient:
    def __init__(self):
        self.session = requests.Session()
        self.ut = settings.EASTMONEY_UT
        self.cb_prefix = settings.EASTMONEY_CB_PREFIX
        self.timeout = settings.EASTMONEY_TIMEOUT

        # 设置通用 headers 模拟浏览器
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def _build_cb(self) -> str:
        """生成动态 callback，模拟 jQuery 时间戳"""
        timestamp = str(int(time.time() * 1000))
        return f"{self.cb_prefix}_{timestamp}"

    def get_jsonp(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params.update({
            "ut": self.ut,
            "cb": self._build_cb(),
            "_": int(time.time() * 1000)
        })

        time.sleep(random.uniform(0.1, 0.3))
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()

        text = resp.text.strip()

        # 安全剥离 JSONP
        if not text.startswith("jQuery") or "(" not in text or not text.endswith(");"):
            # 可能是 HTML 错误页
            raise ValueError(f"Unexpected response (not JSONP): {text[:200]}...")

        start = text.find('(')
        end = text.rfind(')')
        if start == -1 or end == -1 or start >= end:
            raise ValueError(f"Cannot parse JSONP from response: {text[:200]}...")

        json_str = text[start + 1:end]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON: {e}. Raw: {json_str[:200]}...")


# 全局单例
eastmoney_client = EastMoneyClient()