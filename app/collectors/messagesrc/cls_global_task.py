#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社环球消息采集任务
"""

import logging
from datetime import datetime
from typing import Dict, Any

from app.collectors.messagesrc.cls_global_collector import global_collector
from app.events.bus import event_bus

logger = logging.getLogger(__name__)


class CLSGlobalTask:
    """财联社环球消息采集任务"""
    
    def __init__(self):
        self.name = "cls_global"
        self.display_name = "财联社环球采集"
        self.description = "采集财联社环球消息"
        self.schedule = "*/5 * * * *"  # 每5分钟
        self.enabled = True
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """执行采集任务"""
        logger.info("=" * 50)
        logger.info("开始执行财联社环球采集任务")
        logger.info("=" * 50)
        
        start_time = datetime.now()
        
        try:
            # 执行采集
            fetched, inserted = global_collector.fetch_articles(mode="incremental")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "status": "success",
                "fetched": fetched,
                "inserted": inserted,
                "duration": duration,
                "timestamp": end_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"任务完成: 获取 {fetched} 条, 插入 {inserted} 条, 耗时 {duration:.2f} 秒")
            
            # 发布事件
            if inserted > 0:
                event_bus.publish("global_collected", {
                    "count": inserted,
                    "timestamp": end_time.isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }


# 全局实例
cls_global_task = CLSGlobalTask()
