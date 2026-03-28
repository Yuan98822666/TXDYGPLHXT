"""
Cookie 管理 API 路由

接口列表：
  POST /api/cookie/refresh   → 从浏览器自动获取最新 Cookie
  POST /api/cookie/update    → 手动粘贴 Cookie 字符串更新
  GET  /api/cookie/status    → 查看当前 Cookie 状态
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import time

from app.utils.cookie_manager import CookieManager

router = APIRouter()


class CookieUpdateRequest(BaseModel):
    """手动更新 Cookie 请求"""
    cookie_str: str  # 从浏览器 F12 复制的 Cookie 字符串


@router.post("/refresh", summary="从浏览器自动获取最新 Cookie（暂不支持）")
async def refresh_cookie():
    """
    Edge v127+ 使用了新的 Cookie 加密方式，暂时无法自动读取。
    请使用 POST /api/cookie/update 手动粘贴 Cookie 字符串。
    """
    raise HTTPException(
        status_code=501,
        detail="Edge v127+ 加密方式变更，暂不支持自动读取。请使用 POST /api/cookie/update 手动粘贴 Cookie 字符串。"
    )


@router.post("/update", summary="手动粘贴 Cookie 字符串更新")
async def update_cookie(request: CookieUpdateRequest):
    """
    手动更新 Cookie

    使用方式：
    1. 打开 Edge，访问 eastmoney.com
    2. F12 → Network → 找任意请求 → 复制请求头中的 Cookie 字符串
    3. 粘贴到 cookie_str 字段提交

    示例：
    {
        "cookie_str": "qgqp_b_id=xxx; ct=yyy; ut=zzz; ..."
    }
    """
    if not request.cookie_str or len(request.cookie_str) < 10:
        raise HTTPException(status_code=400, detail="Cookie 字符串无效")

    CookieManager.update_from_string(request.cookie_str)

    # 验证关键字段
    cookies = CookieManager.get_cookies()
    has_ct = "ct" in cookies
    has_ut = "ut" in cookies

    if not has_ct or not has_ut:
        return {
            "status": "warning",
            "message": "Cookie 已保存，但缺少关键字段 ct 或 ut，采集可能失败",
            "has_ct": has_ct,
            "has_ut": has_ut,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return {
        "status": "success",
        "message": f"Cookie 已更新，共 {len(cookies)} 个",
        "has_ct": has_ct,
        "has_ut": has_ut,
        "cookie_count": len(cookies),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/status", summary="查看当前 Cookie 状态")
async def cookie_status():
    """
    查看当前 Cookie 状态

    返回：
    - cookie_count: Cookie 数量
    - has_ct: 是否有会话 token
    - has_ut: 是否有用户 token
    - last_update: 最后更新时间
    - source: Cookie 来源（browser/cache/default）
    """
    cookies = CookieManager.get_cookies()
    last_update = CookieManager._last_update

    # 判断来源
    if last_update > 0:
        elapsed = time.time() - last_update
        last_update_str = datetime.fromtimestamp(last_update).strftime("%Y-%m-%d %H:%M:%S")
        is_fresh = elapsed < 3600
    else:
        last_update_str = "未更新"
        is_fresh = False

    return {
        "status": "ok",
        "cookie_count": len(cookies),
        "has_ct": "ct" in cookies,
        "has_ut": "ut" in cookies,
        "is_fresh": is_fresh,
        "last_update": last_update_str,
        "tip": "Cookie 正常" if ("ct" in cookies and "ut" in cookies) else "缺少关键 Cookie，建议调用 /refresh 或 /update",
    }
