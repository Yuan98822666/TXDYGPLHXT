#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社公司深度资讯任务
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from app.collectors.messagesrc.cls_company_depth_collector import company_depth_collector
import logging

logger = logging.getLogger(__name__)

class CLSCompanyDepthTask:
    """财联社公司深度资讯采集任务"""
    
    def __init__(self):
        self.collector = company_depth_collector
        self.last_fetch_time: datetime = None
        
    def run(self, **kwargs) -> Dict[str, Any]:
        """
        执行采集任务
        
        Returns:
            {"success": bool, "fetched": int, "inserted": int, "message": str}
        """
        try:
            # 判断采集模式
            if not self.last_fetch_time:
                mode = "full"
                last_time = None
                logger.info("首次执行，使用全量模式")
            else:
                mode = "incremental"
                last_time = self.last_fetch_time
                logger.info(f"增量模式，上次采集时间: {last_time}")
            
            # 执行采集
            fetched, inserted = self.collector.fetch_articles(
                mode=mode,
                last_time=last_time
            )
            
            # 更新最后采集时间
            self.last_fetch_time = datetime.now()
            
            return {
                "success": True,
                "fetched": fetched,
                "inserted": inserted,
                "message": f"成功采集 {fetched} 条，新增 {inserted} 条"
            }
            
        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}")
            return {
                "success": False,
                "fetched": 0,
                "inserted": 0,
                "message": f"执行失败: {str(e)}"
            }
