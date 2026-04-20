"""
文件路径：app/api/stock/stock_mark_api.py
作用说明：股票标记管理 API（增删改查）

功能清单：
- 查询关注股票列表（分页、搜索）
- 添加关注股票（单个/批量）
- 移除关注股票（单个/批量）
- 切换关注状态
- 按条件批量操作（板块、风险状态等）
- 统计信息
"""
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.base.base_stock import BaseStock

router = APIRouter(prefix="/stock/mark", tags=["股票标记管理"])


# ============== 请求/响应模型 ==============

class StockMarkResponse(BaseModel):
    """股票标记响应"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    secid: str = Field(..., description="东方财富标识")
    exchange: str = Field(..., description="交易所")
    stock_type: str = Field(..., description="板块类型")
    stock_risk: int = Field(..., description="风险状态")
    stock_imp: int = Field(..., description="关注标记")
    pdate_time: str = Field(..., description="更新时间")


class MarkStatsResponse(BaseModel):
    """标记统计响应"""
    total_stocks: int = Field(..., description="股票总数")
    marked_count: int = Field(..., description="已关注数")
    unmarked_count: int = Field(..., description="未关注数")
    risk_count: int = Field(..., description="风险股数")
    by_type: dict = Field(..., description="按板块类型统计")


class BatchMarkRequest(BaseModel):
    """批量标记请求"""
    codes: List[str] = Field(..., description="股票代码列表", min_length=1)
    imp: int = Field(1, description="标记值：1=关注, 0=取消")


class SearchParams(BaseModel):
    """搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词（代码/名称）")
    stock_type: Optional[str] = Field(None, description="板块类型")
    stock_risk: Optional[int] = Field(None, description="风险状态")
    stock_imp: Optional[int] = Field(None, description="关注状态")
    exchange: Optional[str] = Field(None, description="交易所")


# ============== API 端点 ==============

@router.get("/list", summary="查询股票列表")
def get_stock_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页数量"),
    keyword: Optional[str] = Query(None, description="关键词搜索（代码/名称）"),
    stock_type: Optional[str] = Query(None, description="板块类型筛选"),
    stock_risk: Optional[int] = Query(None, description="风险状态筛选"),
    stock_imp: Optional[int] = Query(None, description="关注状态筛选"),
    exchange: Optional[str] = Query(None, description="交易所筛选"),
    db: Session = Depends(get_db)
):
    """
    查询股票列表（支持分页、多条件筛选）
    
    - keyword: 模糊匹配股票代码或名称
    - stock_type: 板块类型（SH_ZB/SZ_ZB/KCB/CYB/BJS）
    - stock_risk: 风险状态（0=有风险, 1=正常）
    - stock_imp: 关注状态（0=未关注, 1=已关注）
    - exchange: 交易所（0=深京市, 1=沪市）
    """
    query = db.query(BaseStock)
    
    # 关键词搜索
    if keyword:
        query = query.filter(
            or_(
                BaseStock.stock_code.contains(keyword),
                BaseStock.stock_name.contains(keyword)
            )
        )
    
    # 条件筛选
    if stock_type:
        query = query.filter(BaseStock.stock_type == stock_type)
    if stock_risk is not None:
        query = query.filter(BaseStock.stock_risk == stock_risk)
    if stock_imp is not None:
        query = query.filter(BaseStock.stock_imp == stock_imp)
    if exchange:
        query = query.filter(BaseStock.exchange == exchange)
    
    # 统计总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    stocks = query.order_by(BaseStock.stock_imp.desc(), BaseStock.stock_code).offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "data": [
            {
                "code": s.stock_code,
                "name": s.stock_name,
                "secid": s.secid,
                "exchange": s.exchange,
                "stock_type": s.stock_type,
                "stock_risk": s.stock_risk,
                "stock_imp": s.stock_imp,
                "skip_until": s.skip_until.isoformat() if s.skip_until else None,
                "pdate_time": s.pdate_time.isoformat() if s.pdate_time else None
            }
            for s in stocks
        ]
    }


@router.get("/marked", summary="获取已关注股票列表")
def get_marked_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """获取所有已关注股票（stock_imp=1）"""
    query = db.query(BaseStock).filter(BaseStock.stock_imp == 1)
    total = query.count()
    
    offset = (page - 1) * page_size
    stocks = query.order_by(BaseStock.stock_code).offset(offset).limit(page_size).all()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "code": s.stock_code,
                "name": s.stock_name,
                "secid": s.secid,
                "exchange": s.exchange,
                "stock_type": s.stock_type,
                "stock_risk": s.stock_risk
            }
            for s in stocks
        ]
    }


@router.post("/add", summary="添加关注股票")
def add_mark(
    code: str = Body(..., embed=True, description="股票代码"),
    db: Session = Depends(get_db)
):
    """
    添加单只股票到关注列表
    
    - code: 股票代码（6位数字，如 000001）
    """
    stock = db.query(BaseStock).filter(BaseStock.stock_code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    
    if stock.stock_imp == 1:
        return {"success": True, "message": f"股票 {code} 已在关注列表中", "already_marked": True}
    
    stock.stock_imp = 1
    db.commit()
    
    return {
        "success": True,
        "message": f"股票 {code} ({stock.stock_name}) 已添加关注",
        "stock": {
            "code": stock.stock_code,
            "name": stock.stock_name,
            "secid": stock.secid
        }
    }


@router.post("/remove", summary="移除关注股票")
def remove_mark(
    code: str = Body(..., embed=True, description="股票代码"),
    skip_days: int = Body(0, embed=True, description="跳过采集天数（0=不跳过）"),
    db: Session = Depends(get_db)
):
    """
    移除单只股票的关注标记
    
    - code: 股票代码
    - skip_days: 跳过采集天数（如 3 表示三日内不再采集）
    """
    stock = db.query(BaseStock).filter(BaseStock.stock_code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    
    if stock.stock_imp == 0:
        return {"success": True, "message": f"股票 {code} 未在关注列表中", "already_unmarked": True}
    
    stock.stock_imp = 0
    
    # 设置跳过采集时间
    if skip_days > 0:
        from datetime import timedelta
        stock.skip_until = datetime.now(timezone.utc) + timedelta(days=skip_days)
    else:
        stock.skip_until = None
    
    db.commit()
    
    skip_msg = f"，{skip_days}日内不再采集" if skip_days > 0 else ""
    return {
        "success": True,
        "message": f"股票 {code} ({stock.stock_name}) 已移除关注{skip_msg}",
        "skip_until": stock.skip_until.isoformat() if stock.skip_until else None
    }


@router.post("/toggle", summary="切换关注状态")
def toggle_mark(
    code: str = Body(..., embed=True, description="股票代码"),
    db: Session = Depends(get_db)
):
    """切换股票的关注状态（关注↔取消）"""
    stock = db.query(BaseStock).filter(BaseStock.stock_code == code).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")
    
    new_imp = 1 - stock.stock_imp  # 切换
    stock.stock_imp = new_imp
    db.commit()
    
    return {
        "success": True,
        "code": stock.stock_code,
        "name": stock.stock_name,
        "stock_imp": new_imp,
        "action": "已添加关注" if new_imp == 1 else "已移除关注"
    }


@router.post("/batch/add", summary="批量添加关注")
def batch_add_mark(
    request: BatchMarkRequest,
    db: Session = Depends(get_db)
):
    """
    批量添加关注
    
    - codes: 股票代码列表
    """
    stocks = db.query(BaseStock).filter(BaseStock.stock_code.in_(request.codes)).all()
    
    if not stocks:
        raise HTTPException(status_code=404, detail="未找到任何匹配的股票")
    
    updated = 0
    for stock in stocks:
        if stock.stock_imp == 0:
            stock.stock_imp = 1
            updated += 1
    
    db.commit()
    
    return {
        "success": True,
        "requested": len(request.codes),
        "found": len(stocks),
        "updated": updated,
        "message": f"成功添加 {updated} 只股票到关注列表"
    }


@router.post("/batch/remove", summary="批量移除关注")
def batch_remove_mark(
    request: BatchMarkRequest,
    db: Session = Depends(get_db)
):
    """批量移除关注"""
    stocks = db.query(BaseStock).filter(BaseStock.stock_code.in_(request.codes)).all()
    
    if not stocks:
        raise HTTPException(status_code=404, detail="未找到任何匹配的股票")
    
    updated = 0
    for stock in stocks:
        if stock.stock_imp == 1:
            stock.stock_imp = 0
            updated += 1
    
    db.commit()
    
    return {
        "success": True,
        "requested": len(request.codes),
        "found": len(stocks),
        "updated": updated,
        "message": f"成功移除 {updated} 只股票的关注标记"
    }


@router.post("/batch/clear", summary="清空所有关注")
def clear_all_marks(db: Session = Depends(get_db)):
    """清空所有关注标记（谨慎操作）"""
    count = db.query(BaseStock).filter(BaseStock.stock_imp == 1).count()
    
    if count == 0:
        return {"success": True, "message": "关注列表已为空", "updated": 0}
    
    db.query(BaseStock).filter(BaseStock.stock_imp == 1).update({"stock_imp": 0})
    db.commit()
    
    return {
        "success": True,
        "message": f"已清空 {count} 只股票的关注标记",
        "updated": count
    }


@router.post("/batch/by-condition", summary="按条件批量标记")
def batch_mark_by_condition(
    stock_type: Optional[str] = Body(None, description="板块类型"),
    stock_risk: Optional[int] = Body(None, description="风险状态"),
    exchange: Optional[str] = Body(None, description="交易所"),
    imp: int = Body(1, description="标记值：1=关注, 0=取消"),
    db: Session = Depends(get_db)
):
    """
    按条件批量标记
    
    示例：
    - 标记所有科创板股票：stock_type=KCB, imp=1
    - 取消所有风险股关注：stock_risk=0, imp=0
    """
    query = db.query(BaseStock)
    
    conditions = []
    if stock_type:
        query = query.filter(BaseStock.stock_type == stock_type)
        conditions.append(f"板块类型={stock_type}")
    if stock_risk is not None:
        query = query.filter(BaseStock.stock_risk == stock_risk)
        conditions.append(f"风险状态={stock_risk}")
    if exchange:
        query = query.filter(BaseStock.exchange == exchange)
        conditions.append(f"交易所={exchange}")
    
    if not conditions:
        raise HTTPException(status_code=400, detail="请至少指定一个筛选条件")
    
    stocks = query.all()
    updated = 0
    for stock in stocks:
        if stock.stock_imp != imp:
            stock.stock_imp = imp
            updated += 1
    
    db.commit()
    
    return {
        "success": True,
        "conditions": conditions,
        "matched": len(stocks),
        "updated": updated,
        "action": "添加关注" if imp == 1 else "取消关注"
    }


@router.get("/stats", summary="获取标记统计")
def get_mark_stats(db: Session = Depends(get_db)):
    """获取股票标记统计信息"""
    total = db.query(BaseStock).count()
    marked = db.query(BaseStock).filter(BaseStock.stock_imp == 1).count()
    risk = db.query(BaseStock).filter(BaseStock.stock_risk == 0).count()
    
    # 按板块类型统计
    from sqlalchemy import func
    type_stats = db.query(
        BaseStock.stock_type,
        func.count(BaseStock.id).label("total"),
        func.sum(BaseStock.stock_imp).label("marked")
    ).group_by(BaseStock.stock_type).all()
    
    by_type = {}
    for t in type_stats:
        by_type[t.stock_type] = {
            "total": t.total,
            "marked": int(t.marked or 0)
        }
    
    return {
        "total_stocks": total,
        "marked_count": marked,
        "unmarked_count": total - marked,
        "risk_count": risk,
        "by_type": by_type
    }


@router.get("/search", summary="搜索股票")
def search_stocks(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: Session = Depends(get_db)
):
    """
    搜索股票（用于自动补全）
    
    支持代码或名称模糊匹配
    """
    stocks = db.query(BaseStock).filter(
        or_(
            BaseStock.stock_code.contains(q),
            BaseStock.stock_name.contains(q)
        )
    ).limit(limit).all()
    
    return {
        "query": q,
        "count": len(stocks),
        "data": [
            {
                "code": s.stock_code,
                "name": s.stock_name,
                "secid": s.secid,
                "stock_imp": s.stock_imp,
                "skip_until": s.skip_until.isoformat() if s.skip_until else None,
                "label": f"{s.stock_code} {s.stock_name}"
            }
            for s in stocks
        ]
    }
