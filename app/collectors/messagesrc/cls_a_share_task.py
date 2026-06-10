#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社 A股消息采集任务

集成到 TaskManager 调度系统
"""

import logging
from typing import Dict, Any

from app.collectors.messagesrc.cls_a_share_collector import CLSAShareCollector

logger = logging.getLogger(__name__)


class CLSAShareTask:
    """财联社 A股消息采集任务"""
    
    def __init__(self):
        self.collector = CLSAShareCollector()
    
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        执行采集任务
        
        Returns:
            {
                'success': bool,
                'fetched': int,
                'inserted': int,
                'skipped': int,
                'message': str
            }
        """
        try:
            result = self.collector.collect()
            
            return {
                'success': True,
                'fetched': result.get('fetched', 0),
                'inserted': result.get('inserted', 0),
                'skipped': result.get('skipped', 0),
                'message': f"A股消息采集完成: 获取 {result.get('fetched', 0)} 条, 新增 {result.get('inserted', 0)} 条"
            }
            
        except Exception as e:
            logger.error(f"A股消息采集任务失败: {e}")
            return {
                'success': False,
                'fetched': 0,
                'inserted': 0,
                'skipped': 0,
                'message': f"采集失败: {str(e)}"
            }


# 任务实例（供 TaskManager 使用）
cls_a_share_task = CLSAShareTask()
