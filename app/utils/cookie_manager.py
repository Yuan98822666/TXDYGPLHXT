# -*- coding: utf-8 -*-
"""
Cookie 管理工具 v2.0

自动获取和管理东方财富 Cookie

分析结论：
- 必须动态获取：ct, ut（会话token，最重要）
- 可选动态：pi（用户信息）
- 完全静态：mtp, vtpst 等

方案：
1. 优先从本地缓存获取（如果未过期）
2. 尝试从浏览器获取（支持Chrome/Edge）
3. 使用手动配置的 Cookie
4. 提供手动更新接口

Edge v127+ 加密变更说明：
- Edge v127+ 使用了新的加密方式，browser-cookie3 库可能无法解密
- 此时会回退到手动配置或缓存
"""
import os
import json
import time
import logging
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cookie 缓存文件路径
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "cookie_cache.json"

# 静态 Cookie（可硬编码）
STATIC_COOKIES = {
    "mtp": "1",
    "vtpst": "%7c",
}

# 关键Cookie名称（必须动态获取的）
ESSENTIAL_COOKIES = ["ct", "ut"]


class CookieManager:
    """Cookie 管理器 v2.0"""

    _cookies: Optional[Dict] = None
    _last_update: float = 0
    _cache_expire: int = 3600  # 缓存1小时
    _last_log_source: Optional[str] = None  # 上次日志来源，避免重复输出

    @classmethod
    def get_cookies(cls) -> Dict[str, str]:
        """获取 Cookie（优先缓存，其次浏览器，最后默认）"""
        # 检查缓存是否有效
        if cls._cookies and time.time() - cls._last_update < cls._cache_expire:
            return cls._cookies

        # 尝试从浏览器获取
        cookies = cls._fetch_from_browser()
        if cookies and cls._validate_cookies(cookies):
            cls._cookies = cookies
            cls._last_update = time.time()
            cls._save_cache(cookies)
            if cls._last_log_source != "browser":
                logger.info("从浏览器获取 Cookie 成功")
                cls._last_log_source = "browser"
            return cookies

        # 尝试从缓存加载
        cookies = cls._load_cache()
        if cookies and cls._validate_cookies(cookies):
            cls._cookies = cookies
            cls._last_update = time.time()
            if cls._last_log_source != "cache":
                logger.info("从缓存加载 Cookie")
                cls._last_log_source = "cache"
            return cookies

        # 使用默认 Cookie（需手动更新）
        if cls._last_log_source != "default":
            logger.warning("使用默认 Cookie，建议手动更新以确保数据准确性")
            cls._last_log_source = "default"
        return cls._get_default_cookies()

    @classmethod
    def _validate_cookies(cls, cookies: Dict[str, str]) -> bool:
        """验证Cookie是否包含必要的字段"""
        for key in ESSENTIAL_COOKIES:
            if key not in cookies or not cookies[key]:
                logger.debug(f"Cookie缺少必要字段: {key}")
                return False
        return True

    @classmethod
    def _fetch_from_browser(cls) -> Optional[Dict[str, str]]:
        """
        从浏览器获取 Cookie
        
        支持：
        - Chrome
        - Edge（v127+ 可能因加密变更而失败）
        
        返回:
            Dict[str, str] 或 None
        """
        try:
            import browser_cookie3 as bc3
            
            # 尝试从Edge获取
            try:
                cj = bc3.edge(domain_name="eastmoney.com")
                cookies = {c.name: c.value for c in cj}
                if cls._validate_cookies(cookies):
                    logger.debug("从 Edge 浏览器获取 Cookie 成功")
                    return {**STATIC_COOKIES, **cookies}
            except Exception as e:
                logger.debug(f"从 Edge 获取 Cookie 失败: {e}")
            
            # 尝试从Chrome获取
            try:
                cj = bc3.chrome(domain_name="eastmoney.com")
                cookies = {c.name: c.value for c in cj}
                if cls._validate_cookies(cookies):
                    logger.debug("从 Chrome 浏览器获取 Cookie 成功")
                    return {**STATIC_COOKIES, **cookies}
            except Exception as e:
                logger.debug(f"从 Chrome 获取 Cookie 失败: {e}")
                
        except ImportError:
            logger.debug("browser_cookie3 库未安装，无法从浏览器获取 Cookie")
        except Exception as e:
            logger.debug(f"从浏览器获取 Cookie 失败: {e}")
        
        return None

    @classmethod
    def _load_cache(cls) -> Optional[Dict[str, str]]:
        """从缓存文件加载"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cookies = data.get("cookies", {})
                    update_time = data.get("update_time", 0)
                    
                    # 检查缓存是否过期（24小时）
                    if time.time() - update_time > 86400:
                        logger.debug("Cookie 缓存已过期（超过24小时）")
                        return None
                    
                    return cookies
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
                    "update_time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

    @classmethod
    def update_cookies(cls, cookies: Dict[str, str]):
        """手动更新 Cookie"""
        merged = {**STATIC_COOKIES, **cookies}
        if not cls._validate_cookies(merged):
            logger.warning("更新的 Cookie 缺少必要字段 (ct, ut)")
        cls._cookies = merged
        cls._last_update = time.time()
        cls._save_cache(cls._cookies)
        cls._last_log_source = "manual"
        logger.info("Cookie 已手动更新")

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
    def get_cookie_status(cls) -> Dict:
        """获取Cookie状态信息"""
        return {
            "source": cls._last_log_source or "unknown",
            "last_update": datetime.fromtimestamp(cls._last_update).strftime("%Y-%m-%d %H:%M:%S") if cls._last_update else None,
            "cache_valid": cls._cookies is not None and time.time() - cls._last_update < cls._cache_expire,
            "has_essential_cookies": cls._validate_cookies(cls._cookies) if cls._cookies else False,
        }

    @classmethod
    def _get_default_cookies(cls) -> Dict[str, str]:
        """默认 Cookie（兜底方案）"""
        # 注意：这些Cookie可能已经过期，需要手动更新
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
    """获取Cookie"""
    return CookieManager.get_cookies()


def update_cookies(cookies: Dict[str, str]):
    """更新Cookie"""
    CookieManager.update_cookies(cookies)


def update_from_string(cookie_str: str):
    """从字符串更新Cookie"""
    CookieManager.update_from_string(cookie_str)


def get_cookie_status() -> Dict:
    """获取Cookie状态"""
    return CookieManager.get_cookie_status()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    cookies = get_cookies()
    print(f"Cookie 数量: {len(cookies)}")
    print(f"关键 Cookie: ct={cookies.get('ct', '')[:30]}...")
    print(f"状态: {get_cookie_status()}")
