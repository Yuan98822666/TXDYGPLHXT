#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报采集任务
支持定时采集和增量发现
"""

import time
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.messagesrc import MessageSrcCLSTelegram
from .cls_telegram_collector import CLSTelegramCollector, TelegramMessage


class CLSTelegramTask:
    """财联社电报采集任务"""
    
    def __init__(self, enable_ocr: bool = False, ocr_engine: str = 'paddle'):
        """
        初始化任务
        
        Args:
            enable_ocr: 是否启用图片OCR
            ocr_engine: OCR引擎类型
        """
        self.collector = CLSTelegramCollector()
        self.enable_ocr = enable_ocr
        self.ocr_engine = ocr_engine
        self.ocr = None  # 延迟初始化
    
    def _save_messages(self, db: Session, messages: List[TelegramMessage]) -> int:
        """
        保存消息到数据库
        
        Args:
            db: 数据库会话
            messages: 消息列表
        
        Returns:
            保存数量
        """
        saved_count = 0
        
        for msg in messages:
            # 检查是否已存在
            existing = db.query(MessageSrcCLSTelegram).filter(
                MessageSrcCLSTelegram.msg_id == msg.msg_id
            ).first()
            
            if existing:
                continue
            
            # OCR识别图片（延迟导入避免依赖问题）
            image_ocr_text = None
            if self.enable_ocr and msg.has_image and msg.image_urls:
                try:
                    if self.ocr is None:
                        from .image_ocr import ImageOCR
                        self.ocr = ImageOCR(engine=self.ocr_engine)
                    image_urls = msg.image_urls.split(';')
                    image_ocr_text = self.ocr.recognize_multiple(image_urls)
                except Exception as e:
                    print(f"OCR failed for msg {msg.msg_id}: {e}")
            
            # 创建数据库记录
            db_msg = MessageSrcCLSTelegram(
                msg_id=msg.msg_id,
                publish_time=msg.publish_time,
                content=msg.content,
                title=msg.title,
                category=msg.category,
                subjects=msg.subjects,
                is_important=msg.is_important,
                has_image=msg.has_image,
                image_urls=msg.image_urls,
                image_ocr_text=image_ocr_text,
                audio_urls=msg.audio_urls,
                source_url=msg.source_url,
                reading_num=msg.reading_num,
                share_num=msg.share_num,
            )
            
            db.add(db_msg)
            saved_count += 1
        
        db.commit()
        return saved_count
    
    def run_full_collection(self, category: str = None) -> int:
        """
        全量采集
        
        Args:
            category: 分类过滤
        
        Returns:
            采集数量
        """
        print(f"[{datetime.now()}] 开始全量采集...")
        
        # 获取电报
        messages = self.collector.fetch_telegrams(category=category, limit=100)
        print(f"获取到 {len(messages)} 条电报")
        
        if not messages:
            return 0
        
        # 保存到数据库
        db = SessionLocal()
        try:
            saved = self._save_messages(db, messages)
            print(f"保存了 {saved} 条新电报")
            return saved
        finally:
            db.close()
    
    def run_incremental_collection(self, minutes: int = 5, category: str = None) -> int:
        """
        增量采集
        
        Args:
            minutes: 采集最近多少分钟的消息
            category: 分类过滤
        
        Returns:
            采集数量
        """
        since = datetime.now() - timedelta(minutes=minutes)
        print(f"[{datetime.now()}] 开始增量采集（最近{minutes}分钟）...")
        
        # 发现新消息
        messages = self.collector.discover_new(since=since, category=category)
        print(f"发现 {len(messages)} 条新电报")
        
        if not messages:
            return 0
        
        # 保存到数据库
        db = SessionLocal()
        try:
            saved = self._save_messages(db, messages)
            print(f"保存了 {saved} 条新电报")
            return saved
        finally:
            db.close()
    
    def run_continuous(self, interval: int = 60, category: str = None):
        """
        持续运行采集
        
        Args:
            interval: 采集间隔（秒）
            category: 分类过滤
        """
        print(f"[{datetime.now()}] 启动持续采集，间隔{interval}秒")
        
        while True:
            try:
                self.run_incremental_collection(minutes=2, category=category)
            except Exception as e:
                print(f"采集失败: {e}")
            
            time.sleep(interval)


def main():
    """测试任务"""
    import sys
    
    task = CLSTelegramTask(enable_ocr=False)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        # 全量采集
        task.run_full_collection()
    elif len(sys.argv) > 1 and sys.argv[1] == 'continuous':
        # 持续采集
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        task.run_continuous(interval=interval)
    else:
        # 增量采集（默认）
        task.run_incremental_collection(minutes=5)


if __name__ == '__main__':
    main()
