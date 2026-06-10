#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报采集任务 V2

集成到 TaskManager 调度系统
支持：全量采集 / 增量采集 / 定时调度
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any

from app.collectors.messagesrc.cls_telegram_collector_v2 import CLSTelegramCollectorV2

logger = logging.getLogger(__name__)


class CLSTelegramTask:
    """财联社电报采集任务（V2）"""
    
    def __init__(self):
        self.collector = CLSTelegramCollectorV2()
        self.name = "财联社电报采集"
    
    def run(self) -> Dict[str, Any]:
        """
        执行采集任务（主入口）
        
        Returns:
            采集结果统计
        """
        logger.info(f"[{datetime.now()}] {self.name} 开始执行")
        
        try:
            result = self.collector.collect()
            logger.info(f"[{datetime.now()}] {self.name} 完成: {result}")
            return result
        except Exception as e:
            logger.error(f"[{datetime.now()}] {self.name} 失败: {e}")
            raise
    
    def run_full(self) -> Dict[str, Any]:
        """强制全量采集（24小时）"""
        logger.info(f"[{datetime.now()}] {self.name} 强制全量采集")
        
        # 临时修改采集逻辑为全量
        # 通过删除数据库最新记录来触发首次采集模式
        # 或者直接在 collector 中提供 force_full 参数
        
        # 这里使用简单方式：直接采集并保存（不检查时间）
        messages = self.collector.fetch_telegrams(limit=200)
        result = self.collector.save_to_db(messages)
        
        summary = {
            'mode': 'forced_full',
            'fetched': len(messages),
            'inserted': result['inserted'],
            'skipped': result['skipped'],
        }
        
        logger.info(f"[{datetime.now()}] 全量采集完成: {summary}")
        return summary


# 兼容旧版入口
def run_cls_telegram_collection():
    """运行财联社电报采集（供 TaskManager 调用）"""
    task = CLSTelegramTask()
    return task.run()


def main():
    """测试任务"""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    task = CLSTelegramTask()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'full':
        # 全量采集
        result = task.run_full()
    else:
        # 增量采集（默认）
        result = task.run()
    
    print("\n采集结果:")
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
