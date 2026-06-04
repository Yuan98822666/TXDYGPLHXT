# -*- coding: utf-8 -*-

"""

文件路径：app/api/analysis/zt_potential_api.py

作用说明：涨停潜力分析API

功能清单：
- 获取涨停潜力排名列表
- 获取个股共振详情
- 获取个股强度排名

"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime
from app.db.session import get_db
from app.models.analysis.analysis_block_stock_resonance import AnalysisBlockStockResonance
from app.models.analysis.analysis_stock_strength import AnalysisStockStrength
from app.models.base.base_stock import BaseStock
from app.models.base.base_block import BaseBlock
from app.models.raw.raw_min_stock import RawMinStock

router = APIRouter(prefix="/analysis/zt-potential", tags=["涨停潜力分析"])

# ============== 响应模型 ==============

class ZTPotentialItem(BaseModel):
    """涨停潜力排名项"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    zt_potential_factor: float = Field(..., description="涨停潜力因子")
    attention_factor: float = Field(..., description="受重视程度因子")
    stock_zl_inflow: int = Field(..., description="个股主力净流入(元)")
    stock_ltsz: int = Field(..., description="个股流通市值(元)")
    is_leader: bool = Field(..., description="是否为某板块领涨股")
    is_money_leader: bool = Field(..., description="是否为某板块资金流入最多股")
    is_resonance: bool = Field(..., description="是否与板块共振")
    block_count: int = Field(..., description="涉及板块数")
    stock_spj: float = Field(..., description="最新价")
    stock_zdf: float = Field(..., description="涨跌幅")


class StockResonanceDetail(BaseModel):
    """个股共振详情"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    block_code: str = Field(..., description="板块代码")
    block_name: str = Field(..., description="板块名称")
    block_type: str = Field(..., description="板块类型(GN/HY)")
    is_leader: bool = Field(..., description="是否为领涨股")
    is_money_leader: bool = Field(..., description="是否为资金流入最多股")
    is_resonance: bool = Field(..., description="是否与板块共振")
    zt_potential_factor: float = Field(..., description="涨停潜力因子")
    attention_factor: float = Field(..., description="受重视程度因子")
    block_importance_factor: float = Field(..., description="板块受重视程度因子")


class StockStrengthItem(BaseModel):
    """个股强度排名项"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    strength_factor: int = Field(..., description="个股强度因子")
    leader_count: int = Field(..., description="领涨股次数")
    money_leader_count: int = Field(..., description="资金流入最多股次数")
    total_blocks: int = Field(..., description="涉及板块总数")

# ============== API 端点 ==============

@router.get("/ranking", summary="涨停潜力排名")
def get_zt_potential_ranking(
    query_date: Optional[date] = Query(None, description="查询日期，默认最新"),
    min_factor: Optional[float] = Query(None, description="最小涨停潜力因子筛选"),
    only_resonance: bool = Query(False, description="仅显示共振股票"),
    only_leader: bool = Query(False, description="仅显示领涨/资金流入最多股"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取涨停潜力排名列表
    按涨停潜力因子(zt_potential_factor)降序排列
    """
    # 确定查询日期
    if query_date is None:
        latest = db.query(AnalysisBlockStockResonance.trade_date).order_by(
            desc(AnalysisBlockStockResonance.trade_date)
        ).first()
        if not latest:
            raise HTTPException(status_code=404, detail="无数据")
        query_date = latest[0]

    # 构建查询
    query = db.query(
        AnalysisBlockStockResonance.stock_code,
        BaseStock.stock_name,
        func.max(AnalysisBlockStockResonance.zt_potential_factor).label("max_zt_factor"),
        func.max(AnalysisBlockStockResonance.attention_factor).label("max_attention_factor"),
        func.max(AnalysisBlockStockResonance.stock_zl_inflow).label("stock_zl_inflow"),
        func.max(AnalysisBlockStockResonance.stock_ltsz).label("stock_ltsz"),
        func.bool_or(AnalysisBlockStockResonance.is_leader).label("is_leader"),
        func.bool_or(AnalysisBlockStockResonance.is_money_leader).label("is_money_leader"),
        func.bool_or(AnalysisBlockStockResonance.is_resonance).label("is_resonance"),
        func.count(AnalysisBlockStockResonance.block_code).label("block_count"),
        func.max(RawMinStock.stock_spj).label("stock_spj"),
        func.max(RawMinStock.stock_zdf).label("stock_zdf")
    ).join(
        BaseStock, AnalysisBlockStockResonance.stock_code == BaseStock.stock_code
    ).outerjoin(
        RawMinStock,
        (AnalysisBlockStockResonance.stock_code == RawMinStock.stock_code) &
        (AnalysisBlockStockResonance.raw_no == RawMinStock.raw_no)
    ).filter(
        AnalysisBlockStockResonance.trade_date == query_date
    )

    # 筛选条件
    if min_factor is not None:
        query = query.having(func.max(AnalysisBlockStockResonance.zt_potential_factor) >= min_factor)

    if only_resonance:
        query = query.having(func.bool_or(AnalysisBlockStockResonance.is_resonance) == True)

    if only_leader:
        query = query.having(
            func.bool_or(AnalysisBlockStockResonance.is_leader) == True or
            func.bool_or(AnalysisBlockStockResonance.is_money_leader) == True
        )

    # 分组和排序
    query = query.group_by(
        AnalysisBlockStockResonance.stock_code,
        BaseStock.stock_name
    ).order_by(desc("max_zt_factor"))

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    return {
        "query_date": query_date.isoformat(),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "data": [
            {
                "stock_code": r.stock_code,
                "stock_name": r.stock_name,
                "zt_potential_factor": float(r.max_zt_factor) if r.max_zt_factor else 0,
                "attention_factor": float(r.max_attention_factor) if r.max_attention_factor else 0,
                "stock_zl_inflow": r.stock_zl_inflow,
                "stock_ltsz": r.stock_ltsz,
                "is_leader": r.is_leader,
                "is_money_leader": r.is_money_leader,
                "is_resonance": r.is_resonance,
                "block_count": r.block_count,
                "stock_spj": float(r.stock_spj) if r.stock_spj else 0,
                "stock_zdf": float(r.stock_zdf) if r.stock_zdf else 0
            }
            for r in results
        ]
    }


@router.get("/stock/{stock_code}/resonance", summary="个股共振详情")
def get_stock_resonance_detail(
    stock_code: str,
    query_date: Optional[date] = Query(None, description="查询日期，默认最新"),
    db: Session = Depends(get_db)
):
    """
    获取个股与板块的共振详情
    展示该股票在哪些板块中是领涨股/资金流入最多股/共振股
    """
    # 确定查询日期
    if query_date is None:
        latest = db.query(AnalysisBlockStockResonance.trade_date).order_by(
            desc(AnalysisBlockStockResonance.trade_date)
        ).first()
        if not latest:
            raise HTTPException(status_code=404, detail="无数据")
        query_date = latest[0]

    # 查询该股票的所有板块记录
    results = db.query(
        AnalysisBlockStockResonance,
        BaseBlock.block_name,
        BaseBlock.block_type
    ).join(
        BaseBlock, AnalysisBlockStockResonance.block_code == BaseBlock.block_code
    ).filter(
        AnalysisBlockStockResonance.stock_code == stock_code,
        AnalysisBlockStockResonance.trade_date == query_date
    ).all()

    if not results:
        raise HTTPException(status_code=404, detail=f"未找到股票 {stock_code} 在 {query_date} 的共振数据")

    # 获取股票名称
    stock = db.query(BaseStock).filter(BaseStock.stock_code == stock_code).first()
    stock_name = stock.stock_name if stock else stock_code

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "trade_date": query_date.isoformat(),
        "total_blocks": len(results),
        "resonance_details": [
            {
                "block_code": r.AnalysisBlockStockResonance.block_code,
                "block_name": r.block_name,
                "block_type": r.block_type,
                "is_leader": r.AnalysisBlockStockResonance.is_leader,
                "is_money_leader": r.AnalysisBlockStockResonance.is_money_leader,
                "is_resonance": r.AnalysisBlockStockResonance.is_resonance,
                "zt_potential_factor": float(r.AnalysisBlockStockResonance.zt_potential_factor),
                "attention_factor": float(r.AnalysisBlockStockResonance.attention_factor),
                "block_importance_factor": float(r.AnalysisBlockStockResonance.block_importance_factor)
            }
            for r in results
        ]
    }


@router.get("/strength-ranking", summary="个股强度排名")
def get_stock_strength_ranking(
    query_date: Optional[date] = Query(None, description="查询日期，默认最新"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    获取个股强度排名列表
    按个股强度因子(strength_factor)降序排列
    """
    # 确定查询日期
    if query_date is None:
        latest = db.query(AnalysisStockStrength.trade_date).order_by(
            desc(AnalysisStockStrength.trade_date)
        ).first()
        if not latest:
            raise HTTPException(status_code=404, detail="无数据")
        query_date = latest[0]

    # 构建查询
    query = db.query(
        AnalysisStockStrength,
        BaseStock.stock_name
    ).join(
        BaseStock, AnalysisStockStrength.stock_code == BaseStock.stock_code
    ).filter(
        AnalysisStockStrength.trade_date == query_date
    ).order_by(desc(AnalysisStockStrength.strength_factor))

    # 统计总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    return {
        "query_date": query_date.isoformat(),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "data": [
            {
                "stock_code": r.AnalysisStockStrength.stock_code,
                "stock_name": r.stock_name,
                "strength_factor": r.AnalysisStockStrength.strength_factor,
                "leader_count": r.AnalysisStockStrength.leader_count,
                "money_leader_count": r.AnalysisStockStrength.money_leader_count,
                "total_blocks": r.AnalysisStockStrength.total_blocks
            }
            for r in results
        ]
    }


@router.get("/stats", summary="涨停潜力统计")
def get_zt_potential_stats(
    query_date: Optional[date] = Query(None, description="查询日期，默认最新"),
    db: Session = Depends(get_db)
):
    """
    获取涨停潜力分析统计信息
    """
    # 确定查询日期
    if query_date is None:
        latest = db.query(AnalysisBlockStockResonance.trade_date).order_by(
            desc(AnalysisBlockStockResonance.trade_date)
        ).first()
        if not latest:
            raise HTTPException(status_code=404, detail="无数据")
        query_date = latest[0]

    # 统计涨停潜力因子分布
    factor_ranges = [
        (0, 30, "低潜力(0-30)"),
        (30, 60, "中潜力(30-60)"),
        (60, 80, "高潜力(60-80)"),
        (80, 100, "极高潜力(80-100)")
    ]

    stats = []
    for min_val, max_val, label in factor_ranges:
        count = db.query(AnalysisBlockStockResonance).filter(
            AnalysisBlockStockResonance.trade_date == query_date,
            AnalysisBlockStockResonance.zt_potential_factor >= min_val,
            AnalysisBlockStockResonance.zt_potential_factor < max_val
        ).distinct(AnalysisBlockStockResonance.stock_code).count()
        stats.append({"range": label, "count": count})

    # 统计共振股票数
    resonance_count = db.query(AnalysisBlockStockResonance).filter(
        AnalysisBlockStockResonance.trade_date == query_date,
        AnalysisBlockStockResonance.is_resonance == True
    ).distinct(AnalysisBlockStockResonance.stock_code).count()

    # 统计领涨股数
    leader_count = db.query(AnalysisBlockStockResonance).filter(
        AnalysisBlockStockResonance.trade_date == query_date,
        AnalysisBlockStockResonance.is_leader == True
    ).distinct(AnalysisBlockStockResonance.stock_code).count()

    return {
        "trade_date": query_date.isoformat(),
        "factor_distribution": stats,
        "resonance_stock_count": resonance_count,
        "leader_stock_count": leader_count,
        "total_analyzed": db.query(AnalysisBlockStockResonance).filter(
            AnalysisBlockStockResonance.trade_date == query_date
        ).distinct(AnalysisBlockStockResonance.stock_code).count()
    }
