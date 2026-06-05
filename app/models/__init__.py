# -*- coding: utf-8 -*-
"""
SQLAlchemy 模型统一注册模块

设计原则：
- 所有模型必须在此注册，确保 Base.metadata 能感知到所有表
- 子包通过 __init__.py 导出模型，此处统一导入
- 新增模型时，只需在对应子包的 __init__.py 中添加导出

使用方式：
    from app.models import BaseStock, RawMinStock, MessageSrcCLSTelegram
    # 或
    from app.models.base import BaseStock
    from app.models.raw import RawMinStock
"""

# ==========================================
# 基础数据模型 (base_*)
# ==========================================
from app.models.base import (
    BaseBlock,
    BaseStock,
    BaseBlockStockLnk,
    BaseIndustry,
)

# ==========================================
# 快照数据模型 (raw_*)
# ==========================================
from app.models.raw import (
    RawMinStock,
    RawDayStock,
    RawMinBlock,
    RawDayBlock,
)

# ==========================================
# 分析数据模型 (analysis_*)
# ==========================================
from app.models.analysis import (
    AnalysisBlockStockResonance,
    AnalysisStockStrength,
)

# ==========================================
# 特殊股票池模型 (special_*)
# ==========================================
from app.models.special import (
    SpecialZt,
    SpecialZrzt,
    SpecialZb,
    SpecialDt,
)

# ==========================================
# 系统配置模型 (sys_*)
# ==========================================
from app.models.system import MarketStateDate

# ==========================================
# 消息源模型 (messagesrc_*)
# ==========================================
from app.models.messagesrc import MessageSrcCLSTelegram

# 统一导出
__all__ = [
    # Base
    "BaseBlock",
    "BaseStock",
    "BaseBlockStockLnk",
    "BaseIndustry",
    # Raw
    "RawMinStock",
    "RawDayStock",
    "RawMinBlock",
    "RawDayBlock",
    # Analysis
    "AnalysisBlockStockResonance",
    "AnalysisStockStrength",
    # Special
    "SpecialZt",
    "SpecialZrzt",
    "SpecialZb",
    "SpecialDt",
    # System
    "MarketStateDate",
    # MessageSrc
    "MessageSrcCLSTelegram",
]
