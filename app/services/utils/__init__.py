import requests
import json
import re
from typing import Dict, Any


class EastMoneyRequest:
    """
    东方财富 HTTP 请求工具
    - 支持 JSONP 自动解包
    """

    DEFAULT_TIMEOUT = 10

    @staticmethod
    def get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.get(url, params=params, timeout=EastMoneyRequest.DEFAULT_TIMEOUT)
        resp.raise_for_status()

        text = resp.text.strip()

        # JSONP 解包
        if text.startswith("jQuery"):
            match = re.search(r"\((\{.*\})\)", text)
            if not match:
                raise ValueError("JSONP 响应解析失败")
            return json.loads(match.group(1))

        return resp.json()
