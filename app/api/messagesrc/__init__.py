#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息源API包
"""

from .cls_telegram_api import router as cls_telegram_router
from .cls_a_share_api import router as cls_a_share_router
from .cls_headline_api import router as cls_headline_router
from .cls_global_api import router as cls_global_router
from .cls_company_depth_api import router as cls_company_depth_router

__all__ = [
    'cls_telegram_router',
    'cls_a_share_router', 
    'cls_headline_router',
    'cls_global_router',
    'cls_company_depth_router',
]
