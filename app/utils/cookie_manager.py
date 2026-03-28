# -*- coding: utf-8 -*-
"""
Cookie 管理工具

自动从浏览器获取东方财富 Cookie

分析结论：
- 必须动态获取：ct, ut（会话token，最重要）
- 可选动态：pi（用户信息）
- 完全静态：mtp, vtpst 等

方案：
1. 优先从 Edge 浏览器 CDP 自动获取
2. 失败则使用本地缓存的 Cookie
3. 提供手动更新接口
"""
import os
import json
import time
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Cookie 缓存文件路径
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "cookie_cache.json"

# 静态 Cookie（可硬编码）
STATIC_COOKIES = {
    "mtp": "1",
    "vtpst": "%7c",
}


class CookieManager:
    """Cookie 管理器"""

    _cookies: Optional[Dict] = None
    _last_update: float = 0
    _cache_expire: int = 3600  # 缓存1小时

    @classmethod
    def get_cookies(cls) -> Dict[str, str]:
        """获取 Cookie（优先从浏览器，失败用缓存）"""
        # 检查缓存是否有效
        if cls._cookies and time.time() - cls._last_update < cls._cache_expire:
            return cls._cookies

        # 尝试从浏览器获取
        cookies = cls._fetch_from_browser()
        if cookies:
            cls._cookies = cookies
            cls._last_update = time.time()
            cls._save_cache(cookies)
            logger.info("从浏览器获取 Cookie 成功")
            return cookies

        # 尝试从缓存加载
        cookies = cls._load_cache()
        if cookies:
            cls._cookies = cookies
            logger.info("从缓存加载 Cookie")
            return cookies

        # 使用默认 Cookie（需手动更新）
        logger.debug("使用默认 Cookie")
        return cls._get_default_cookies()

    @classmethod
    def _fetch_from_browser(cls) -> Optional[Dict[str, str]]:
        """从 Edge 浏览器获取 Cookie（暂不支持，Edge v127+ 加密方式变更）"""
        return None

    @classmethod
    def _load_cache(cls) -> Optional[Dict[str, str]]:
        """从缓存文件加载"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("cookies")
        except Exception as e:
            logger.debug(f"加载缓存失败: {e}")
        return None

    @classmethod
    def _save_cache(cls, cookies: Dict[str, str]):
        """保存到缓存文件"""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "cookies": cookies,
                    "update_time": time.time(),
                    "update_time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

    @classmethod
    def update_cookies(cls, cookies: Dict[str, str]):
        """手动更新 Cookie"""
        cls._cookies = {**STATIC_COOKIES, **cookies}
        cls._last_update = time.time()
        cls._save_cache(cls._cookies)
        logger.info("Cookie 已更新")

    @classmethod
    def update_from_string(cls, cookie_str: str):
        """从字符串更新 Cookie（格式：name=value; name2=value2）"""
        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()
        cls.update_cookies(cookies)

    @classmethod
    def _get_default_cookies(cls) -> Dict[str, str]:
        """默认 Cookie（需手动更新）"""
        return {
            **STATIC_COOKIES,
            "qgqp_b_id": "598291964dc8ab4cc01ac6de4f6c2296",
            "st_nvi": "021PS9A01VseM5luF921Nd2b2",
            "ct": "K5Bs8w2pbmaGP8xlGidc679Yqo3YX9Y1IFrI93FmisSr2HVv5OFV9dYiTdNjIU55gnZE1dArpIdLFV7EG_WenozrM0O75AuF_4rfj9YPdfr1yTeP37wVFOTCeG6WTY4sOttIIEsS887muiUAb_AAVQU358ZUXSOsYatjAXT8mqQ",
            "ut": "FobyicMgeV54OLFNgnrRk89pqzVtSDOYz8h76AUqlmLdJexPUgka-05NcoNzUVGkhHCA0pDHUCum4BsFuph6TGosihCqo9kfjBlF0KDzVnndIWxnAIH0JjrZX1Q26Kz9kHcXmSEwJ4Dmgm_Zt_9knrfsuIww13XafQ8UTrhblxQ7XdhU6u6c0icJNw2SIYJ5Td6SB3o33OXTkpADjnKJXfV7cbb-pVdbe8K18IG-VbRPAIWJ-9GviaF1RKKIRp38MacJFnhGKxaxKg4ISYrAe5xvz1fGVPXW",
            "pi": "3951356261349626%3Bn3951356261349626%3B%E8%B0%B7%E5%BE%B7%E6%8B%9C%3BlIsfHzaSD8CVPdQTuvHissIJi7kVl7UZKVycu0O%2F2TOwnS90pRhJFI04%2FqwWgR9MrvBOAHIiOa4aNgczYF9h%2B3bcm%2FKs2AfgHZ6KsBABjhvea6gk5wCrS1jGrzcvnMZEh%2BIBWg1r15LLt8FeR2MhbhtoouDxaZWjbnDrvlxV5egMj%2Ffbj%2FCsEGJFOsrAA3ULogIqgbTf%3BKfsTtu7tFjigPzp23zR8eLkBWbPtnaJf1kRZKQ7sGrNQhaDNO7SACj11Bh8aPdqO3Z%2BYfKeugc0EP9C3sDmDIpWxyQN3AsXtvTLaSbZA0%2FmMUlhL50C9QKOJCtidNMQ7qlvLy5s0%2Fz5dKVZRVUYdxos4VaorqA%3D%3D",
            "uidal": "3951356261349626%e8%b0%b7%e5%be%b7%e6%8b%9c",
            "sid": "166237526",
            "st_si": "49798075943576",
            "st_pvi": "39999945198105",
            "st_sp": "2025-05-13%2009%3A20%3A50",
        }


# 便捷函数
def get_cookies() -> Dict[str, str]:
    return CookieManager.get_cookies()

def update_cookies(cookies: Dict[str, str]):
    CookieManager.update_cookies(cookies)

def update_from_string(cookie_str: str):
    CookieManager.update_from_string(cookie_str)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    cookies = get_cookies()
    print(f"Cookie 数量: {len(cookies)}")
    print(f"关键 Cookie: ct={cookies.get('ct', '')[:30]}...")
