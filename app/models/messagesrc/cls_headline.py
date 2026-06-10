#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社头条消息模型
"""

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text
from app.db.base import Base
from datetime import datetime


class MessageSrcCLSHeadline(Base):
    """财联社头条消息"""
    __tablename__ = "messagesrc_cls_headline"
    __table_args__ = {"comment": "财联社头条消息"}
    
    article_id = Column(String(50), primary_key=True, comment="文章ID")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, comment="内容/摘要")
    publish_time = Column(DateTime, nullable=False, comment="发布时间")
    stock_codes = Column(JSON, default=list, comment="关联股票代码")
    stock_names = Column(JSON, default=list, comment="关联股票名称")
    raw_data = Column(JSON, comment="原始数据")
    created_time = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
