# -*- coding: utf-8 -*-
"""
股票数据计算工具类

提供各种派生指标的实时计算，统一入口，方便日后扩展。
每个方法接收原始数据字典/模型，返回计算后的值。
"""
from typing import Optional, Dict, Any


class StockCalculator:
    """
    股票快照数据计算工具

    计算公式：
    - 实际换手率 = 成交量(手) / 流通股(股) × 100
      东方财富成交量单位为"手"（1手=100股），流通股为"股"，换算后：cjl(手)×100 / ltg(股) × 100
      简化：cjl × 10000 / ltg
    """

    @classmethod
    def calc_sjhsl(cls, cjl: Optional[Any], ltg: Optional[Any]) -> Optional[float]:
        """
        计算实际换手率（%）

        参数:
            cjl: 成交量（手），东方财富 f47 字段
            ltg: 流通股（股），东方财富 f85 字段

        返回:
            实际换手率（%），如 5.23
            成交量或流通股为 None / 0 时返回 None
        """
        if cjl is None or ltg is None:
            return None
        try:
            cjl_val = float(cjl)
            ltg_val = float(ltg)
            if ltg_val == 0:
                return None
            return cjl_val * 10000 / ltg_val
        except (TypeError, ValueError):
            return None

    @classmethod
    def calc_ztzt(cls, spj: Optional[Any], zgj: Optional[Any], ztj: Optional[Any],
                  dtj: Optional[Any]) -> int:
        """
        判断涨停状态

        返回:
            0 = 正常
            1 = 涨停（现价 = 涨停价）
            2 = 炸板（曾涨停，但现价 ≠ 涨停价）
            3 = 跌停（现价 = 跌停价）
        """
        if spj is None or ztj is None:
            return 0
        try:
            spj_val = float(spj)
            ztj_val = float(ztj)
            # 涨停：现价 = 涨停价（东方财富原始数据单位为"分"，即0.01元，误差1分以内视为相等）
            if abs(spj_val - ztj_val) <= 1:
                return 1
            # 炸板：最高价 = 涨停价，但现价 ≠ 涨停价
            if zgj is not None:
                zgj_val = float(zgj)
                if abs(zgj_val - ztj_val) <= 1 and abs(spj_val - ztj_val) > 1:
                    return 2
            # 跌停
            if dtj is not None:
                dtj_val = float(dtj)
                if abs(spj_val - dtj_val) <= 1:
                    return 3
        except (TypeError, ValueError):
            pass
        return 0

    @classmethod
    def calc_inflow_zb(cls, zl: Optional[Any], total: Optional[Any]) -> Optional[float]:
        """
        计算资金流向占比（%）

        参数:
            zl: 净流入金额（元）
            total: 成交额（元）

        返回:
            占比（%），如 -3.25
        """
        if zl is None or total is None:
            return None
        try:
            zl_val = float(zl)
            total_val = float(total)
            if total_val == 0:
                return None
            return zl_val / total_val * 100
        except (TypeError, ValueError):
            return None
