#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社公司深度资讯模型
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Index
from app.db.base import Base

class MessageSrcCLSCompanyDepth(Base):
    """财联社公司深度资讯表"""
    
    __tablename__ = "messagesrc_cls_company_depth"
    
    article_id = Column(String(50), primary_key=True, comment="文章ID")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(String, nullable=True, comment="正文内容")
    publish_time = Column(DateTime, nullable=False, index=True, comment="发布时间")
    stock_codes = Column(JSON, default=list, comment="关联股票代码列表")
    stock_names = Column(JSON, default=list, comment="关联股票名称列表")
    raw_data = Column(JSON, nullable=True, comment="原始数据")
    created_time = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    def __repr__(self):
        return f"<CLSCompanyDepth({self.article_id}: {self.title[:30]}...)>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": getattr(self, 'id', None),
            "article_id": self.article_id,
            "title": self.title,
            "content": self.content,
            "publish_time": self.publish_time.strftime('%Y-%m-%d %H:%M:%S') if self.publish_time else None,
            "stock_codes": self.stock_codes,
            "stock_names": self.stock_names,
            "created_time": self.created_time.strftime('%Y-%m-%d %H:%M:%S') if self.created_time else None,
            "updated_time": self.updated_time.strftime('%Y-%m-%d %H:%M:%S') if self.updated_time else None,
        }
