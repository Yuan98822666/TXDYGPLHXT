# -*- coding: utf-8 -*-
"""
东方财富统一请求工具

功能：
1. 自动注入 Cookie 和防反爬 Headers
2. 统一 JSONP 解析
3. 错误处理和重试
4. 所有请求参数统一从 request_conf.yaml 读取

使用方式：
    from app.utils.request_util import EastMoneyRequest

    # 板块列表
    blocks = EastMoneyRequest.get_blocks("concept")

    # 成分股
    data = EastMoneyRequest.get_block_stocks("BK0968", page=1)

    # 股票列表
    data = EastMoneyRequest.get_stocks(page=1)
"""
import time
import random
import json
import logging
from typing import Dict, Any, Optional
from curl_cffi.requests import Session

from app.utils.cookie_manager import get_cookies
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EastMoneyRequest:
    """东方财富统一请求工具"""

    _session: Optional[Session] = None

    # 防反爬 Headers
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
    }

    @classmethod
    def _get_session(cls) -> Session:
        """获取或创建 Session"""
        if cls._session is None:
            cls._session = Session(impersonate="chrome120")
            cls._session.headers.update(cls.HEADERS)
        return cls._session

    @classmethod
    def _get_endpoint(cls, key: str) -> Dict[str, Any]:
        """
        从 request_conf.yaml 读取指定接口配置

        参数:
            key: endpoints 下的 key 名，如 "board_concept"、"block_stocks"、"base_stocks"

        返回:
            配置字典（已合并 common 参数）
        """
        cfg = settings.request_config
        endpoint = cfg.endpoints[key].model_dump(exclude_none=True)
        common = cfg.common.model_dump()

        # common 参数作为默认值，endpoint 参数优先
        merged = {**common, **endpoint}
        return merged

    @classmethod
    def get_jsonp(cls, url: str, params: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
        """
        发送 GET 请求获取 JSONP 数据

        参数:
            url: API 接口 URL
            params: 请求参数（会自动添加 cb 和 _ 时间戳）
            timeout: 超时时间（秒）

        返回:
            解析后的 JSON 数据字典
        """
        session = cls._get_session()

        # 随机延迟
        time.sleep(random.uniform(0.1, 0.3))

        # 获取 Cookie
        cookies = get_cookies()

        # 生成动态回调名
        ts = int(time.time() * 1000)
        cb = params.get("cb", f"jQuery{ts}")
        params["cb"] = cb
        params.setdefault("_", ts + 1)

        try:
            resp = session.get(url, params=params, cookies=cookies, timeout=timeout)
            resp.raise_for_status()
            text = resp.text.strip()

            # 解析 JSONP
            if f"{cb}(" in text:
                json_str = text.split(f"{cb}(", 1)[1].rsplit(")", 1)[0]
                return json.loads(json_str)
            elif "(" in text and ")" in text:
                start = text.find("(")
                end = text.rfind(")")
                json_str = text[start + 1:end]
                return json.loads(json_str)
            else:
                return json.loads(text)

        except Exception as e:
            logger.error(f"请求失败: {url} - {e}")
            raise

    @classmethod
    def get_blocks(cls, board_type: str = "concept") -> list:
        """
        获取板块列表

        参数:
            board_type: "concept"（概念板块）或 "industry"（行业板块）

        返回:
            [{"code": "BK0968", "name": "固态电池", "type": "GN"}, ...]
        """
        key_map = {"concept": "board_concept", "industry": "board_industry"}
        type_map = {"concept": "GN", "industry": "HY"}

        yaml_key = key_map.get(board_type, "board_concept")
        block_type = type_map.get(board_type, "GN")
        cfg = cls._get_endpoint(yaml_key)
        url = cfg.pop("url")

        params = {
            "np":    cfg.get("np", "1"),
            "fltt":  cfg.get("fltt", "2"),
            "invt":  cfg.get("invt", "2"),
            "fs":    cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid":   cfg.get("fid"),
            "pz":    cfg.get("pz", "500"),
            "po":    cfg.get("po", "1"),
            "ut":    cfg.get("ut"),     # 来自 yaml common.ut
        }

        all_blocks = []
        page = 1

        while True:
            params["pn"] = str(page)
            try:
                data = cls.get_jsonp(url, dict(params))
                if data.get("rc") != 0:
                    break

                diff = data.get("data", {}).get("diff", [])
                if not diff:
                    break

                for item in diff:
                    code = item.get("f12")
                    name = item.get("f14")
                    if code and name:
                        all_blocks.append({
                            "code": code,
                            "name": name,
                            "type": block_type,
                        })

                if len(diff) < int(params["pz"]):
                    break
                page += 1
            except Exception as e:
                logger.error(f"获取板块列表失败: {e}")
                break

        return all_blocks

    @classmethod
    def get_block_stocks(cls, block_code: str, page: int = 1, page_size: int = 100) -> Optional[Dict]:
        """
        获取板块成分股

        参数:
            block_code: 板块代码（如 BK0968）
            page: 页码
            page_size: 每页数量

        返回:
            {"total": 总数, "codes": [股票代码列表], "data": [原始数据]}
        """
        cfg = cls._get_endpoint("block_stocks")
        url = cfg.pop("url")

        params = {
            "np":    cfg.get("np", "1"),
            "fltt":  cfg.get("fltt", "1"),
            "invt":  cfg.get("invt", "2"),
            "fs":    f"b:{block_code.lower()}+f:!50",   # 动态拼接
            "fields": cfg.get("fields", "f12"),
            "fid":   cfg.get("fid", "f3"),
            "pn":    str(page),
            "pz":    str(page_size),
            "po":    cfg.get("po", "1"),
            "dect":  cfg.get("dect", "1"),
            "ut":    cfg.get("ut"),                       # 来自 yaml common.ut
            "wbp2u": cfg.get("wbp2u"),                    # 来自 yaml block_stocks.wbp2u
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                total = data.get("data", {}).get("total", 0)
                codes = [item.get("f12") for item in diff if item.get("f12")]
                return {"total": total, "codes": codes, "data": diff}
        except Exception as e:
            logger.error(f"获取板块成分股失败: {block_code} - {e}")

        return None

    @classmethod
    def get_stocks(cls, page: int = 1, page_size: int = 100) -> Optional[Dict]:
        """
        获取股票列表

        参数:
            page: 页码
            page_size: 每页数量

        返回:
            {"total": 总数, "stocks": [{...}, ...]}
        """
        cfg = cls._get_endpoint("base_stocks")
        url = cfg.pop("url")

        params = {
            "np":    cfg.get("np", "1"),
            "fltt":  cfg.get("fltt", "2"),
            "invt":  cfg.get("invt", "2"),
            "fs":    cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid":   cfg.get("fid", "f12"),
            "pn":    str(page),
            "pz":    str(page_size),
            "po":    cfg.get("po", "1"),
            "ut":    cfg.get("ut"),     # 来自 yaml common.ut
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                total = data.get("data", {}).get("total", 0)
                return {"total": total, "stocks": diff}
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")

        return None


# 兼容旧代码的别名
eastmoney_client = type("EastMoneyClient", (), {
    "get_jsonp": staticmethod(EastMoneyRequest.get_jsonp)
})()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== 测试统一请求工具 ===\n")

    result = EastMoneyRequest.get_block_stocks("BK0968")
    if result:
        print(f"BK0968: {result['total']} 只, 前5只: {result['codes'][:5]}")

    blocks = EastMoneyRequest.get_blocks("concept")
    print(f"概念板块: {len(blocks)} 个")
