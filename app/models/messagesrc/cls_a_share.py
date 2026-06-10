#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社 A股消息模型
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, DateTime, Index, JSON, BigInteger
from sqlalchemy.sql import func

from app.db.base import Base


class MessageSrcCLSAShare(Base):
    """财联社 A股消息表"""
    
    __tablename__ = 'messagesrc_cls_a_share'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    article_id = Column(String(50), nullable=False, unique=True, comment='财联社文章唯一ID')
    title = Column(String(500), nullable=False, comment='标题')
    content = Column(Text, nullable=True, comment='正文内容')
    summary = Column(Text, nullable=True, comment='摘要')
    publish_time = Column(DateTime, nullable=False, comment='发布时间')
    stock_codes = Column(JSON, nullable=True, comment='关联股票代码列表')
    stock_names = Column(JSON, nullable=True, comment='关联股票名称列表')
    source = Column(String(100), nullable=True, comment='来源')
    author = Column(String(100), nullable=True, comment='作者')
    reading_num = Column(BigInteger, default=0, comment='阅读数')
    share_num = Column(BigInteger, default=0, comment='分享数')
    image_url = Column(String(500), nullable=True, comment='封面图片URL')
    create_time = Column(DateTime, default=func.now(), comment='入库时间')
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_cls_a_share_publish_time', 'publish_time'),
        # 注意：JSON 字段不能创建 btree 索引，如需索引请使用 GIN
        # Index('idx_cls_a_share_stock_codes', 'stock_codes', postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<MessageSrcCLSAShare(id={self.id}, article_id={self.article_id}, title={self.title})>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'publish_time': self.publish_time.strftime('%Y-%m-%d %H:%M:%S') if self.publish_time else None,
            'stock_codes': self.stock_codes,
            'stock_names': self.stock_names,
            'source': self.source,
            'author': self.author,
            'reading_num': self.reading_num,
            'share_num': self.share_num,
            'image_url': self.image_url,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
        }
