#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社头条消息API
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.messagesrc import MessageSrcCLSHeadline


router = APIRouter(prefix="/api/messagesrc/cls/headline", tags=["财联社头条消息"])


class HeadlineMessageResponse(BaseModel):
    """头条消息响应模型"""
    id: int
    article_id: str
    title: str
    content: str
    publish_time: str
    stock_codes: Optional[list]
    stock_names: Optional[list]
    created_time: str
    updated_time: str
    
    class Config:
        from_attributes = True


@router.get("/list", response_model=List[HeadlineMessageResponse])
async def list_headline_messages(
    limit: int = Query(50, ge=1, le=200, description="数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取头条消息列表
    """
    query = db.query(MessageSrcCLSHeadline)
    query = query.order_by(MessageSrcCLSHeadline.publish_time.desc())
    messages = query.offset(offset).limit(limit).all()
    return [msg.to_dict() for msg in messages]


@router.get("/latest")
async def latest_headline_messages(
    minutes: int = Query(30, ge=1, le=1440, description="最近多少分钟"),
    db: Session = Depends(get_db)
):
    """
    获取最近时间的头条消息
    """
    since = datetime.now() - timedelta(minutes=minutes)
    messages = db.query(MessageSrcCLSHeadline).filter(
        MessageSrcCLSHeadline.publish_time >= since
    ).order_by(MessageSrcCLSHeadline.publish_time.desc()).all()
    
    return {
        "count": len(messages),
        "messages": [msg.to_dict() for msg in messages]
    }


@router.get("/count")
async def count_headline_messages(
    db: Session = Depends(get_db)
):
    """
    获取头条消息总数
    """
    count = db.query(MessageSrcCLSHeadline).count()
    return {"count": count}
