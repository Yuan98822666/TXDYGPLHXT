# -*- coding: utf-8 -*-
"""
首页数据看板 API

提供首页所需的统计数据：
- 今日采集数量
- 关注股票数量
- 最近活动记录
- 涨停/跌停/炸板统计
- 热门板块
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

from app.db.session import get_db
from app.models.base.base_stock import BaseStock
from app.models.raw.raw_min_stock import RawMinStock
from app.models.special.special_zt import SpecialZt as SpecialZT
from app.models.special.special_dt import SpecialDt as SpecialDT
from app.models.special.special_zb import SpecialZb as SpecialZB
from app.models.messagesrc.cls_telegram import MessageSrcCLSTelegram as CLSTelegram

router = APIRouter(tags=["首页数据看板"])


@router.get("/stats", summary="获取首页统计数据")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    获取首页所有统计数据
    
    返回：
        - today_collection: 今日采集数量
        - watched_stocks: 关注股票数量
        - market_stats: 市场统计（涨停/跌停/炸板）
        - recent_activities: 最近活动记录
        - hot_blocks: 热门板块
    """
    try:
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        # 1. 今日采集数量（快照表今日记录数）
        today_collection = db.query(RawMinStock).filter(
            RawMinStock.trade_date == today
        ).count()
        
        # 2. 关注股票数量
        watched_count = db.query(BaseStock).filter(
            BaseStock.stock_imp == 1
        ).count()
        
        # 3. 市场统计 - 从特殊池表获取最新数据
        # 涨停数
        zt_count = db.query(SpecialZT).filter(
            SpecialZT.trade_date == today
        ).count()
        
        # 跌停数
        dt_count = db.query(SpecialDT).filter(
            SpecialDT.trade_date == today
        ).count()
        
        # 炸板数
        zb_count = db.query(SpecialZB).filter(
            SpecialZB.trade_date == today
        ).count()
        
        # 4. 最近活动 - 从任务执行日志或采集记录生成
        # 获取最新的快照采集时间
        latest_snapshot = db.query(RawMinStock).order_by(
            desc(RawMinStock.snapshot_time)
        ).first()
        
        # 获取最新的电报消息
        latest_telegram = db.query(CLSTelegram).order_by(
            desc(CLSTelegram.create_time)
        ).limit(3).all()
        
        activities = []
        
        # 添加快照采集活动
        if latest_snapshot:
            activities.append({
                "icon": "✓",
                "icon_color": "text-green-500",
                "title": "快照采集完成",
                "time": latest_snapshot.snapshot_time.strftime('%H:%M:%S') if latest_snapshot.snapshot_time else '-',
                "detail": f"采集 {today_collection} 条记录"
            })
        
        # 添加电报消息活动
        for tg in latest_telegram:
            activities.append({
                "icon": "📰",
                "icon_color": "text-blue-500",
                "title": tg.title or "财联社电报",
                "time": tg.publish_time.strftime('%H:%M:%S') if tg.publish_time else '-',
                "detail": tg.content[:50] + "..." if tg.content and len(tg.content) > 50 else (tg.content or "")
            })
        
        # 5. 热门板块 - 从板块快照获取涨幅最高的板块
        # 使用原生SQL查询板块数据
        hot_blocks = []
        try:
            result = db.execute(text("""
                SELECT block_code, block_name, block_zdf 
                FROM raw_min_block 
                WHERE trade_date = CURRENT_DATE
                ORDER BY block_zdf DESC 
                LIMIT 5
            """))
            for row in result:
                hot_blocks.append({
                    "name": row.block_name or row.block_code,
                    "change": f"+{row.block_zdf:.2f}%" if row.block_zdf and row.block_zdf > 0 else f"{row.block_zdf:.2f}%"
                })
        except Exception:
            # 如果表不存在或查询失败，返回空列表
            pass
        
        # 6. 主力净流入（从最新快照汇总）
        total_inflow = 0
        try:
            result = db.execute(text("""
                SELECT SUM(stock_zl_inflow) as total_inflow
                FROM raw_min_stock
                WHERE trade_date = CURRENT_DATE
            """))
            row = result.fetchone()
            if row and row.total_inflow:
                total_inflow = row.total_inflow
        except Exception:
            pass
        
        return {
            "status": "success",
            "data": {
                "today_collection": today_collection,
                "watched_stocks": watched_count,
                "market_stats": {
                    "zt_count": zt_count,
                    "dt_count": dt_count,
                    "zb_count": zb_count,
                    "total_inflow": total_inflow
                },
                "recent_activities": activities[:5],  # 最多5条
                "hot_blocks": hot_blocks
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取统计数据失败: {str(e)}",
            "data": {
                "today_collection": 0,
                "watched_stocks": 0,
                "market_stats": {"zt_count": 0, "dt_count": 0, "zb_count": 0, "total_inflow": 0},
                "recent_activities": [],
                "hot_blocks": []
            },
            "timestamp": datetime.now().isoformat()
        }


@router.get("/market-overview", summary="获取市场概览")
async def get_market_overview(db: Session = Depends(get_db)):
    """
    获取市场概览数据（用于数据看板页面）
    
    返回：
        - 大盘资金流向
        - 关注股票列表
        - 板块热点
    """
    try:
        today = date.today()
        
        # 1. 关注股票列表（前10只）
        watched_stocks = db.query(BaseStock).filter(
            BaseStock.stock_imp == 1
        ).limit(10).all()
        
        stocks_data = []
        for s in watched_stocks:
            stocks_data.append({
                "stock_code": s.stock_code,
                "stock_name": s.stock_name,
                "stock_type": s.stock_type,
                "stock_imp": s.stock_imp
            })
        
        # 2. 板块热点（涨幅前8）
        hot_blocks = []
        try:
            result = db.execute(text("""
                SELECT block_code, block_name, block_zdf,
                       block_leader_stock_name, block_money_stock_name
                FROM raw_min_block 
                WHERE trade_date = CURRENT_DATE
                ORDER BY block_zdf DESC 
                LIMIT 8
            """))
            for row in result:
                hot_blocks.append({
                    "block_code": row.block_code,
                    "block_name": row.block_name or row.block_code,
                    "leader_stock_name": row.block_leader_stock_name,
                    "money_stock_name": row.block_money_stock_name
                })
        except Exception:
            pass
        
        # 3. 资金流向统计
        flow_stats = {
            "main_inflow": 0,
            "super_large_inflow": 0,
            "large_inflow": 0,
            "medium_small_inflow": 0
        }
        
        try:
            result = db.execute(text("""
                SELECT 
                    SUM(stock_zl_inflow) as main_inflow,
                    SUM(stock_cdd_inflow) as super_large,
                    SUM(stock_dd_inflow) as large,
                    SUM(stock_zd_inflow + stock_xd_inflow) as medium_small
                FROM raw_min_stock
                WHERE trade_date = CURRENT_DATE
            """))
            row = result.fetchone()
            if row:
                flow_stats = {
                    "main_inflow": row.main_inflow or 0,
                    "super_large_inflow": row.super_large or 0,
                    "large_inflow": row.large or 0,
                    "medium_small_inflow": row.medium_small or 0
                }
        except Exception:
            pass
        
        return {
            "status": "success",
            "data": {
                "watched_stocks": stocks_data,
                "hot_blocks": hot_blocks,
                "flow_stats": flow_stats
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取市场概览失败: {str(e)}",
            "data": {
                "watched_stocks": [],
                "hot_blocks": [],
                "flow_stats": {
                    "main_inflow": 0,
                    "super_large_inflow": 0,
                    "large_inflow": 0,
                    "medium_small_inflow": 0
                }
            },
            "timestamp": datetime.now().isoformat()
        }
