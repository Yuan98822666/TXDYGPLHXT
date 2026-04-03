# -*- coding: utf-8 -*-
"""
采集调度器

功能：启动时读取配置，按策略自动执行采集任务
- 快照采集(raw_min_*)：按配置的时间段执行
- 特殊股票池(special_*)：按配置的时间段执行
- 日K采集(raw_day_*)：收盘后执行一次
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime, time as dt_time, date
from typing import Dict, List, Optional
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config" / "collection_schedule.yaml"


class CollectorScheduler:
    """采集调度器"""

    _instance: Optional["CollectorScheduler"] = None
    _running: bool = False
    _thread: Optional[threading.Thread] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.config: Dict = {}
        self.last_run_times: Dict[str, float] = {}
        self.is_trading_day: bool = True

    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if not CONFIG_FILE.exists():
                logger.error(f"配置文件不存在: {CONFIG_FILE}")
                return False

            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)

            logger.info("调度器配置加载成功")
            return True
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return False

    def is_trading_time(self) -> bool:
        """判断当前是否在交易时间内"""
        now = datetime.now()
        current_time = now.time()

        # 周末不采集
        if now.weekday() >= 5:
            return False

        # 9:25 - 11:30 早盘
        if dt_time(9, 25) <= current_time <= dt_time(11, 30):
            return True

        # 13:00 - 14:57 午盘
        if dt_time(13, 0) <= current_time <= dt_time(14, 57):
            return True

        return False

    def is_market_close_time(self) -> bool:
        """判断是否已收盘（15:00后）"""
        now = datetime.now()
        return now.time() >= dt_time(15, 0)

    def parse_schedule_time(self, time_str: str) -> dt_time:
        """解析时间字符串为time对象"""
        parts = time_str.split(":")
        return dt_time(int(parts[0]), int(parts[1]), int(parts[2]))

    def should_run_now(self, schedule: Dict) -> bool:
        """判断是否应该执行采集"""
        now = datetime.now()
        current_time = now.time()
        current_seconds = now.hour * 3600 + now.minute * 60 + now.second

        schedule_type = schedule.get("type")

        if schedule_type == "once":
            # 定点执行
            run_time = self.parse_schedule_time(schedule.get("time", "09:25:00"))
            schedule_seconds = run_time.hour * 3600 + run_time.minute * 60 + run_time.second

            # 允许5秒内的误差
            return abs(current_seconds - schedule_seconds) <= 5

        elif schedule_type == "interval":
            # 区间执行
            start_time = self.parse_schedule_time(schedule.get("start_time", "09:31:30"))
            end_time = self.parse_schedule_time(schedule.get("end_time", "11:30:00"))
            interval = schedule.get("interval_seconds", 30)

            start_seconds = start_time.hour * 3600 + start_time.minute * 60
            end_seconds = end_time.hour * 3600 + end_time.minute * 60

            # 检查是否在时间区间内
            if not (start_seconds <= current_seconds <= end_seconds):
                return False

            # 检查是否到了执行间隔
            schedule_key = f"{schedule.get('name', '')}_{interval}"
            last_run = self.last_run_times.get(schedule_key, 0)
            if current_seconds - last_run >= interval:
                self.last_run_times[schedule_key] = current_seconds
                return True

        return False

    def run_raw_collection(self):
        """执行快照采集"""
        try:
            from app.collectors.stock_raw_collector import StockRawCollector
            from app.collectors.block_raw_collector import BlockRawCollector

            logger.info("执行快照采集...")
            # 先跑板块（标记新增关注股），再跑股票（采集所有关注股）
            BlockRawCollector.collect()
            StockRawCollector.collect()
            logger.info("快照采集完成")
        except Exception as e:
            logger.error(f"快照采集失败: {e}")

    def run_special_pool_collection(self):
        """执行特殊股票池采集"""
        try:
            from app.collectors.special_pool_collector import SpecialPoolCollector

            logger.info("执行特殊股票池采集...")
            SpecialPoolCollector.collect_all()
            logger.info("特殊股票池采集完成")
        except Exception as e:
            logger.error(f"特殊股票池采集失败: {e}")

    def run_day_k_collection(self, action: str = "replace"):
        """
        执行日K采集
        
        参数:
            action: 操作类型
                - "append": 追加模式（09:27:00 早盘日K）
                - "replace": 删除后重新采集模式（15:05:00 收盘日K）
        """
        try:
            from app.collectors.day_collector import DayCollector

            logger.info(f"执行日K采集... (action={action})")
            DayCollector.collect_all(action=action)
            logger.info("日K采集完成")
        except Exception as e:
            logger.error(f"日K采集失败: {e}")

    def scheduler_loop(self):
        """调度器主循环"""
        logger.info("采集调度器启动")

        # 初始化：只在交易时间内执行采集（非交易时段跳过初始化采集）
        current_time = datetime.now().time()
        is_trading_hours = (
            dt_time(9, 25) <= current_time <= dt_time(11, 30) or
            dt_time(13, 0) <= current_time <= dt_time(15, 5)
        )
        
        if is_trading_hours:
            logger.info("交易时段启动，执行初始化采集...")
            try:
                self.run_raw_collection()
                self.run_special_pool_collection()
            except Exception as e:
                logger.error(f"初始化采集失败: {e}")
        else:
            logger.info("非交易时段启动，跳过初始化采集")

        day_k_collected = False

        while self._running:
            now = datetime.now()

            # 跳过非交易时间（但保留开盘竞价和收盘时段）
            current_time = now.time()
            if not (dt_time(9, 25) <= current_time <= dt_time(11, 30) or
                    dt_time(13, 0) <= current_time <= dt_time(15, 5)):
                time.sleep(10)
                continue

            # 检查快照采集
            raw_config = self.config.get("raw", {})
            if raw_config.get("enabled", True):
                schedules = raw_config.get("schedules", [])
                for schedule in schedules:
                    if self.should_run_now(schedule):
                        self.run_raw_collection()
                        break

            # 检查特殊股票池采集
            special_config = self.config.get("special_pool", {})
            if special_config.get("enabled", True):
                schedules = special_config.get("schedules", [])
                for schedule in schedules:
                    if self.should_run_now(schedule):
                        self.run_special_pool_collection()
                        break

            # 检查日K采集（收盘后只执行一次）
            if self.is_market_close_time() and not day_k_collected:
                day_k_config = self.config.get("day_k", {})
                if day_k_config.get("enabled", True):
                    schedules = day_k_config.get("schedules", [])
                    for schedule in schedules:
                        if schedule.get("action") == "replace" and self.should_run_now(schedule):
                            self.run_day_k_collection(action="replace")
                            day_k_collected = True
                            break

            # 检查早盘日K采集（09:27:00）
            day_k_config = self.config.get("day_k", {})
            if day_k_config.get("enabled", True) and not day_k_collected:
                schedules = day_k_config.get("schedules", [])
                for schedule in schedules:
                    if schedule.get("action") == "append" and self.should_run_now(schedule):
                        self.run_day_k_collection(action="append")
                        break

            # 新的一天，重置日K采集标记
            if current_time < dt_time(15, 0):
                day_k_collected = False

            time.sleep(1)

        logger.info("采集调度器停止")

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return

        if not self.load_config():
            logger.error("无法加载配置，调度器启动失败")
            return

        self._running = True
        self._thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("采集调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("采集调度器已停止")

    def reload(self):
        """重新加载配置"""
        self.load_config()
        logger.info("调度器配置已重新加载")


# 单例便捷函数
_scheduler: Optional[CollectorScheduler] = None


def get_scheduler() -> CollectorScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = CollectorScheduler()
    return _scheduler


def start_scheduler():
    """启动调度器"""
    get_scheduler().start()


def stop_scheduler():
    """停止调度器"""
    if _scheduler:
        _scheduler.stop()
