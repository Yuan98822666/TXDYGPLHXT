#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报消息模型
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, Index, JSON
from sqlalchemy.sql import func

from app.db.base import Base


class MessageSrcCLSTelegram(Base):
    """财联社电报消息表"""
    
    __tablename__ = 'messagesrc_cls_telegram'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='自增主键')
    msg_id = Column(String(50), nullable=False, unique=True, comment='财联社消息唯一ID')
    publish_time = Column(DateTime, nullable=False, comment='发布时间')
    content = Column(Text, nullable=False, comment='正文内容')
    title = Column(String(500), nullable=True, comment='标题（可选）')
    category = Column(String(20), nullable=True, comment='分类: zc政策/gs公司/hy行业/sc市场')
    subjects = Column(JSON, nullable=True, comment='原始分类标签列表')
    is_important = Column(Boolean, default=False, comment='是否重要（置顶或高等级）')
    has_image = Column(Boolean, default=False, comment='是否含图片')
    image_urls = Column(Text, nullable=True, comment='图片URL，多个用分号隔开')
    image_ocr_text = Column(Text, nullable=True, comment='图片OCR识别内容，多个用分号隔开')
    audio_urls = Column(Text, nullable=True, comment='音频URL，多个用分号隔开')
    source_url = Column(String(500), nullable=True, comment='原文链接')
    reading_num = Column(BigInteger, default=0, comment='阅读数')
    share_num = Column(BigInteger, default=0, comment='分享数')
    create_time = Column(DateTime, default=func.now(), comment='入库时间')
    update_time = Column(DateTime, default=func.now(), onupdate=func.now(), comment='更新时间')
    
    # 索引
    __table_args__ = (
        Index('idx_publish_time', 'publish_time'),
        Index('idx_category', 'category'),
        Index('idx_is_important', 'is_important'),
        Index('idx_msg_id', 'msg_id'),
    )
    
    def __repr__(self):
        return f"<MessageSrcCLSTelegram(id={self.id}, msg_id={self.msg_id}, title={self.title})>"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'msg_id': self.msg_id,
            'publish_time': self.publish_time.strftime('%Y-%m-%d %H:%M:%S') if self.publish_time else None,
            'content': self.content,
            'title': self.title,
            'category': self.category,
            'subjects': self.subjects,
            'is_important': self.is_important,
            'has_image': self.has_image,
            'image_urls': self.image_urls,
            'image_ocr_text': self.image_ocr_text,
            'audio_urls': self.audio_urls,
            'source_url': self.source_url,
            'reading_num': self.reading_num,
            'share_num': self.share_num,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
        }
