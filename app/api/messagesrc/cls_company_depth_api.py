#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社公司深度API
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.messagesrc import MessageSrcCLSCompanyDepth


router = APIRouter(prefix="/api/messagesrc/cls/company-depth", tags=["财联社公司深度"])


class CompanyDepthResponse(BaseModel):
    """公司深度响应模型"""
    article_id: str
    title: str
    content: Optional[str]
    publish_time: str
    stock_codes: Optional[list]
    stock_names: Optional[list]
    created_time: Optional[str]
    updated_time: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/list", response_model=List[CompanyDepthResponse])
async def list_company_depth(
    limit: int = Query(50, ge=1, le=200, description="数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取公司深度列表
    """
    query = db.query(MessageSrcCLSCompanyDepth)
    query = query.order_by(MessageSrcCLSCompanyDepth.publish_time.desc())
    messages = query.offset(offset).limit(limit).all()
    return [msg.to_dict() for msg in messages]


@router.get("/latest")
async def latest_company_depth(
    minutes: int = Query(30, ge=1, le=1440, description="最近多少分钟"),
    db: Session = Depends(get_db)
):
    """
    获取最近时间的公司深度
    """
    since = datetime.now() - timedelta(minutes=minutes)
    messages = db.query(MessageSrcCLSCompanyDepth).filter(
        MessageSrcCLSCompanyDepth.publish_time >= since
    ).order_by(MessageSrcCLSCompanyDepth.publish_time.desc()).all()
    
    return {
        "count": len(messages),
        "messages": [msg.to_dict() for msg in messages]
    }


@router.get("/count")
async def count_company_depth(
    db: Session = Depends(get_db)
):
    """
    获取公司深度总数
    """
    count = db.query(MessageSrcCLSCompanyDepth).count()
    return {"count": count}
