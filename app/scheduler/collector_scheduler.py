# -*- coding: utf-8 -*-
"""
【已废弃】采集调度器 - CollectorScheduler

⚠️ 警告：此调度器已废弃，请使用 TaskManager (task_manager.py)

废弃原因：
- TaskManager 提供更灵活的内存化配置
- TaskManager 支持动态修改配置无需重启
- TaskManager 有更好的任务隔离和错误处理

保留此文件仅用于：
1. 向后兼容（如果仍有代码引用）
2. 参考旧版实现逻辑

迁移指南：
- 使用 TaskManager 替代所有 CollectorScheduler 的功能
- API 层已统一使用 TaskManager
- 配置文件从 YAML 迁移到内存化配置
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CollectorScheduler:
    """
    【已废弃】采集调度器
    
    请使用 TaskManager 替代
    """
    
    _instance: Optional["CollectorScheduler"] = None
    _deprecated_warned: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not CollectorScheduler._deprecated_warned:
            logger.warning(
                "CollectorScheduler 已废弃，请使用 TaskManager。"
                "此警告仅显示一次。"
            )
            CollectorScheduler._deprecated_warned = True
        self.config: Dict = {}

    def load_config(self) -> bool:
        """【废弃】加载配置"""
        logger.warning("CollectorScheduler.load_config() 已废弃")
        return False

    def start(self):
        """【废弃】启动调度器"""
        logger.error(
            "CollectorScheduler.start() 已废弃，"
            "请使用 TaskManager.start_all_tasks()"
        )
        raise RuntimeError(
            "CollectorScheduler 已废弃，请迁移到 TaskManager。"
            "参见: app/scheduler/task_manager.py"
        )

    def stop(self):
        """【废弃】停止调度器"""
        logger.warning("CollectorScheduler.stop() 已废弃")

    def reload(self):
        """【废弃】重新加载配置"""
        logger.warning("CollectorScheduler.reload() 已废弃")


# 便捷函数 - 全部废弃
def get_scheduler():
    """【废弃】获取调度器单例"""
    logger.warning("get_scheduler() 已废弃，请使用 TaskManager")
    return CollectorScheduler()


def start_scheduler():
    """【废弃】启动调度器"""
    logger.error("start_scheduler() 已废弃，请使用 TaskManager.start_all_tasks()")
    raise RuntimeError("请迁移到 TaskManager")


def stop_scheduler():
    """【废弃】停止调度器"""
    logger.warning("stop_scheduler() 已废弃")
