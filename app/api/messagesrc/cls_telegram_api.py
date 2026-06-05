#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报API
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.messagesrc import MessageSrcCLSTelegram


router = APIRouter(prefix="/api/messagesrc/cls/telegram", tags=["财联社电报"])


class TelegramMessageResponse(BaseModel):
    """电报消息响应模型"""
    id: int
    msg_id: str
    publish_time: str
    content: str
    title: Optional[str]
    category: Optional[str]
    subjects: Optional[List[str]]
    is_important: bool
    has_image: bool
    image_urls: Optional[str]
    image_ocr_text: Optional[str]
    audio_urls: Optional[str]
    source_url: Optional[str]
    reading_num: int
    share_num: int
    
    class Config:
        from_attributes = True


@router.get("/list", response_model=List[TelegramMessageResponse])
async def list_telegrams(
    category: Optional[str] = Query(None, description="分类: zc/gs/hy/sc"),
    is_important: Optional[bool] = Query(None, description="是否重要"),
    limit: int = Query(50, ge=1, le=200, description="数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """
    获取电报列表
    """
    query = db.query(MessageSrcCLSTelegram)
    
    if category:
        query = query.filter(MessageSrcCLSTelegram.category == category)
    
    if is_important is not None:
        query = query.filter(MessageSrcCLSTelegram.is_important == is_important)
    
    # 按发布时间倒序
    query = query.order_by(MessageSrcCLSTelegram.publish_time.desc())
    
    messages = query.offset(offset).limit(limit).all()
    
    return [msg.to_dict() for msg in messages]


@router.get("/latest", response_model=List[TelegramMessageResponse])
async def latest_telegrams(
    minutes: int = Query(30, ge=1, le=1440, description="最近多少分钟"),
    category: Optional[str] = Query(None, description="分类: zc/gs/hy/sc"),
    db: Session = Depends(get_db)
):
    """
    获取最近时间的电报
    """
    since = datetime.now() - timedelta(minutes=minutes)
    
    query = db.query(MessageSrcCLSTelegram).filter(
        MessageSrcCLSTelegram.publish_time >= since
    )
    
    if category:
        query = query.filter(MessageSrcCLSTelegram.category == category)
    
    query = query.order_by(MessageSrcCLSTelegram.publish_time.desc())
    
    messages = query.all()
    
    return [msg.to_dict() for msg in messages]


@router.get("/{msg_id}", response_model=TelegramMessageResponse)
async def get_telegram(
    msg_id: str,
    db: Session = Depends(get_db)
):
    """
    获取单条电报详情
    """
    message = db.query(MessageSrcCLSTelegram).filter(
        MessageSrcCLSTelegram.msg_id == msg_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")
    
    return message.to_dict()


@router.post("/collect")
async def trigger_collection(
    category: Optional[str] = Query(None, description="分类: zc/gs/hy/sc"),
    full: bool = Query(False, description="是否全量采集"),
):
    """
    触发采集任务（异步执行）
    """
    # TODO: 集成到任务调度器
    from app.collectors.messagesrc.cls_telegram_task import CLSTelegramTask
    
    task = CLSTelegramTask(enable_ocr=False)
    
    if full:
        count = task.run_full_collection(category=category)
    else:
        count = task.run_incremental_collection(minutes=5, category=category)
    
    return {"success": True, "collected": count}
