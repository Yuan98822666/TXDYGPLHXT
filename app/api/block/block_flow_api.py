# -*- coding: utf-8 -*-
"""
板块资金走向 API

提供板块实时统计、时间序列数据、股票列表等接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from datetime import date, datetime, timedelta
from typing import Literal, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.raw.raw_min_block import RawMinBlock
from app.models.raw.raw_min_stock import RawMinStock
from app.models.base.base_block import BaseBlock
from app.models.base.base_stock import BaseStock
from app.models.base.base_block_stock_lnk import BaseBlockStockLnk

router = APIRouter(tags=["板块资金流向"])


# ============ 数据模型 ============

class BlockTop5Item(BaseModel):
    code: str
    name: str
    inflow: float  # 单位：万
    speed: float   # 单位：万/分钟


class BlockTypeStats(BaseModel):
    total: int
    active: int
    top5: list[BlockTop5Item]


class BlockStatsResponse(BaseModel):
    date: date
    concept: BlockTypeStats
    industry: BlockTypeStats


class BlockSeriesItem(BaseModel):
    code: str
    name: str
    type: Literal["GN", "HY"]
    current_flow: float  # 单位：万
    series: list[float]  # 单位：万
    speed: float         # 单位：万/分钟


class BlockTimeSeriesResponse(BaseModel):
    date: date
    time_labels: list[str]
    blocks: list[BlockSeriesItem]


class StockItem(BaseModel):
    stock_code: str
    stock_name: str
    price: float
    change_percent: float
    zl_inflow: float  # 单位：万
    blocks: list[str]


class BlockStocksResponse(BaseModel):
    total: int
    stocks: list[StockItem]


# ============ 辅助函数 ============

def get_trade_date() -> date:
    """获取当前交易日期（简化版，实际应判断节假日）"""
    now = datetime.now()
    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
        # 开盘前，返回上一交易日
        return now.date() - timedelta(days=1)
    return now.date()


def generate_trade_time_labels() -> list[str]:
    """生成固定的交易时间轴（9:30-11:30, 13:00-15:00）"""
    labels = []
    
    # 上午 9:30-11:30
    for hour in range(9, 12):
        start_min = 30 if hour == 9 else 0
        end_min = 60 if hour < 11 else 31
        for minute in range(start_min, end_min):
            labels.append(f"{hour:02d}:{minute:02d}")
    
    # 下午 13:00-15:00
    for hour in range(13, 16):
        end_min = 60 if hour < 15 else 1
        for minute in range(0, end_min):
            labels.append(f"{hour:02d}:{minute:02d}")
    
    return labels


def yuan_to_wan(yuan: float) -> float:
    """元转万"""
    return round(yuan / 10000, 2) if yuan else 0.0


# ============ API 接口 ============

@router.get("/stats", response_model=BlockStatsResponse)
def get_block_stats(
    query_date: Optional[date] = Query(None, description="查询日期，默认今日"),
    db: Session = Depends(get_db)
):
    """
    获取板块实时统计数据
    
    - 概念/行业板块总数和活跃数
    - Top5 板块（按主力净流入排序）
    """
    trade_date = query_date or get_trade_date()
    
    # 获取该日期最新的批次号
    latest_raw = db.query(RawMinBlock).filter(
        RawMinBlock.trade_date == trade_date
    ).order_by(desc(RawMinBlock.raw_no)).first()
    
    if not latest_raw:
        return BlockStatsResponse(
            date=trade_date,
            concept=BlockTypeStats(total=0, active=0, top5=[]),
            industry=BlockTypeStats(total=0, active=0, top5=[])
        )
    
    latest_raw_no = latest_raw.raw_no
    
    # 获取所有板块基础信息
    base_blocks = db.query(BaseBlock).all()
    base_block_map = {b.block_code: b for b in base_blocks}
    
    # 获取最新快照数据
    snapshots = db.query(RawMinBlock).filter(
        RawMinBlock.trade_date == trade_date,
        RawMinBlock.raw_no == latest_raw_no
    ).all()
    
    # 分类统计
    gn_blocks = []
    hy_blocks = []
    
    for snap in snapshots:
        base = base_block_map.get(snap.block_code)
        if not base:
            continue
        
        inflow = yuan_to_wan(float(snap.block_zl_inflow or 0))
        
        # 计算增速（当前 - 上一分钟）
        prev_snap = db.query(RawMinBlock).filter(
            RawMinBlock.block_code == snap.block_code,
            RawMinBlock.trade_date == trade_date,
            RawMinBlock.raw_no < latest_raw_no
        ).order_by(desc(RawMinBlock.raw_no)).first()
        
        speed = inflow - yuan_to_wan(float(prev_snap.block_zl_inflow or 0)) if prev_snap else 0
        
        item = BlockTop5Item(
            code=snap.block_code,
            name=snap.block_name or base.block_name,
            inflow=inflow,
            speed=round(speed, 2)
        )
        
        if base.block_type == "GN":
            gn_blocks.append((item, inflow > 0))
        elif base.block_type == "HY":
            hy_blocks.append((item, inflow > 0))
    
    # 排序取 Top5
    gn_sorted = sorted([b[0] for b in gn_blocks], key=lambda x: x.inflow, reverse=True)
    hy_sorted = sorted([b[0] for b in hy_blocks], key=lambda x: x.inflow, reverse=True)
    
    return BlockStatsResponse(
        date=trade_date,
        concept=BlockTypeStats(
            total=len(gn_blocks),
            active=sum(1 for _, active in gn_blocks if active),
            top5=gn_sorted[:5]
        ),
        industry=BlockTypeStats(
            total=len(hy_blocks),
            active=sum(1 for _, active in hy_blocks if active),
            top5=hy_sorted[:5]
        )
    )


@router.get("/timeseries", response_model=BlockTimeSeriesResponse)
def get_block_timeseries(
    block_type: Literal["GN", "HY"] = Query(..., description="板块类型：GN=概念, HY=行业"),
    query_date: Optional[date] = Query(None, description="查询日期，默认今日"),
    db: Session = Depends(get_db)
):
    """
    获取板块时间序列数据
    
    - 返回指定类型所有板块的分时数据
    - 用于绘制双折线图
    """
    trade_date = query_date or get_trade_date()
    
    # 获取该类型所有板块
    base_blocks = db.query(BaseBlock).filter(
        BaseBlock.block_type == block_type
    ).all()
    
    if not base_blocks:
        return BlockTimeSeriesResponse(
            date=trade_date,
            time_labels=[],
            blocks=[]
        )
    
    block_codes = [b.block_code for b in base_blocks]
    block_map = {b.block_code: b for b in base_blocks}
    
    # 获取该日期所有时间点的数据
    snapshots = db.query(RawMinBlock).filter(
        RawMinBlock.trade_date == trade_date,
        RawMinBlock.block_code.in_(block_codes)
    ).order_by(asc(RawMinBlock.snapshot_time)).all()
    
    # 生成固定的完整时间轴
    time_labels = generate_trade_time_labels()
    time_labels_set = set(time_labels)
    
    # 按板块分组
    block_series: dict[str, dict[str, float]] = {}
    
    for snap in snapshots:
        code = snap.block_code
        time_str = snap.snapshot_time.strftime("%H:%M")
        
        # 只保留在固定时间轴内的数据
        if time_str not in time_labels_set:
            continue
        
        if code not in block_series:
            block_series[code] = {}
        
        inflow = yuan_to_wan(float(snap.block_zl_inflow or 0))
        block_series[code][time_str] = inflow
    
    # 构建返回数据
    result_blocks = []
    for code, series_dict in block_series.items():
        base = block_map.get(code)
        if not base:
            continue
        
        # 补齐缺失时间点（使用固定时间轴）
        full_series = [series_dict.get(t, 0.0) for t in time_labels]
        
        # 计算当前流入和增速（使用最后一个非零值或最后一个值）
        # 找到最后一个有效数据点
        last_valid_idx = len(full_series) - 1
        while last_valid_idx >= 0 and full_series[last_valid_idx] == 0.0:
            last_valid_idx -= 1
        
        current_flow = full_series[last_valid_idx] if last_valid_idx >= 0 else 0.0
        
        # 计算增速：最后一个有效值 - 前一个有效值
        prev_valid_idx = last_valid_idx - 1
        while prev_valid_idx >= 0 and full_series[prev_valid_idx] == 0.0:
            prev_valid_idx -= 1
        
        speed = (full_series[last_valid_idx] - full_series[prev_valid_idx]) if last_valid_idx > prev_valid_idx >= 0 else 0.0
        
        result_blocks.append(BlockSeriesItem(
            code=code,
            name=base.block_name,
            type=block_type,
            current_flow=round(current_flow, 2),
            series=[round(v, 2) for v in full_series],
            speed=round(speed, 2)
        ))
    
    return BlockTimeSeriesResponse(
        date=trade_date,
        time_labels=time_labels,
        blocks=result_blocks
    )


@router.get("/stocks", response_model=BlockStocksResponse)
def get_block_stocks(
    query_date: Optional[date] = Query(None, description="查询日期，默认今日"),
    block_name: Optional[str] = Query(None, description="板块名称筛选"),
    sort_by: Literal["flow", "change", "code"] = Query("flow", description="排序方式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词（代码/名称）"),
    db: Session = Depends(get_db)
):
    """
    获取板块关联股票列表
    
    - 支持按板块筛选（传入板块名称，返回该板块成分股）
    - 支持搜索股票代码/名称
    - 支持多种排序方式
    """
    trade_date = query_date or get_trade_date()
    
    # 获取该日期最新的批次号（从股票分钟表）
    latest_raw = db.query(RawMinStock).filter(
        RawMinStock.trade_date == trade_date
    ).order_by(desc(RawMinStock.raw_no)).first()
    
    if not latest_raw:
        return BlockStocksResponse(total=0, stocks=[])
    
    latest_raw_no = latest_raw.raw_no
    
    # 构建股票基础查询
    stock_query = db.query(BaseStock)
    
    # 如果指定了板块名称，筛选该板块的成分股
    if block_name:
        # 先找到匹配的板块代码
        matched_blocks = db.query(BaseBlock).filter(
            BaseBlock.block_name.contains(block_name)
        ).all()
        
        if not matched_blocks:
            return BlockStocksResponse(total=0, stocks=[])
        
        block_codes = [b.block_code for b in matched_blocks]
        
        # 查找这些板块的成分股
        lnk_query = db.query(BaseBlockStockLnk.stock_code).filter(
            BaseBlockStockLnk.block_code.in_(block_codes)
        ).distinct()
        
        stock_codes = [row[0] for row in lnk_query.all()]
        
        if not stock_codes:
            return BlockStocksResponse(total=0, stocks=[])
        
        stock_query = stock_query.filter(BaseStock.stock_code.in_(stock_codes))
    
    # 搜索筛选
    if search:
        search_pattern = f"%{search}%"
        stock_query = stock_query.filter(
            (BaseStock.stock_code.contains(search)) |
            (BaseStock.stock_name.contains(search))
        )
    
    # 获取所有匹配的股票
    stocks = stock_query.all()
    
    if not stocks:
        return BlockStocksResponse(total=0, stocks=[])
    
    stock_codes = [s.stock_code for s in stocks]
    stock_map = {s.stock_code: s for s in stocks}
    
    # 获取这些股票的最新分钟数据（价格、涨跌幅、主力净流入）
    stock_snapshots = db.query(RawMinStock).filter(
        RawMinStock.trade_date == trade_date,
        RawMinStock.raw_no == latest_raw_no,
        RawMinStock.stock_code.in_(stock_codes)
    ).all()
    
    # 获取每个股票所属的板块列表
    stock_blocks = db.query(
        BaseBlockStockLnk.stock_code,
        BaseBlockStockLnk.block_name
    ).filter(
        BaseBlockStockLnk.stock_code.in_(stock_codes)
    ).all()
    
    # 按股票分组板块
    stock_block_map: dict[str, list[str]] = {}
    for stock_code, blk_name in stock_blocks:
        if stock_code not in stock_block_map:
            stock_block_map[stock_code] = []
        stock_block_map[stock_code].append(blk_name)
    
    # 构建返回数据
    result_stocks = []
    for snap in stock_snapshots:
        stock = stock_map.get(snap.stock_code)
        if not stock:
            continue
        
        result_stocks.append(StockItem(
            stock_code=snap.stock_code,
            stock_name=stock.stock_name,
            price=float(snap.stock_spj or 0),
            change_percent=float(snap.stock_zdf or 0),
            zl_inflow=float(snap.stock_zl_inflow or 0),
            blocks=stock_block_map.get(snap.stock_code, [])
        ))
    
    # 排序
    if sort_by == "flow":
        result_stocks.sort(key=lambda x: x.zl_inflow, reverse=True)
    elif sort_by == "change":
        result_stocks.sort(key=lambda x: x.change_percent, reverse=True)
    elif sort_by == "code":
        result_stocks.sort(key=lambda x: x.stock_code)
    
    # 分页
    total = len(result_stocks)
    start = (page - 1) * size
    end = start + size
    paged_stocks = result_stocks[start:end]
    
    return BlockStocksResponse(
        total=total,
        stocks=paged_stocks
    )
