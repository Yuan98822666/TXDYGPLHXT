# -*- coding: utf-8 -*-
"""
任务管理器

功能：
    - 统一管理所有采集任务（raw、special_pool、day_k）
    - 配置完全内存化，支持动态修改
    - 支持任务级别的开关控制
    - 支持手动执行单个任务
    - 轻量调度，节省系统资源

设计原则：
    - 高内聚：任务管理逻辑集中在此模块
    - 低耦合：通过函数引用解耦具体采集器
    - 内存化：配置和状态全部在内存中操作
"""
import threading
import logging
import time as time_module
from datetime import datetime, time as dt_time
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config" / "collection_schedule.yaml"


class TaskStatus(Enum):
    """任务状态枚举"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 执行中
    DISABLED = "disabled"   # 已禁用


@dataclass
class Schedule:
    """
    调度配置项
    
    属性：
        name: 调度名称（如"早盘连续竞价"）
        type: 类型（once=定点执行, interval=区间执行）
        time: 定点执行时间（type=once时使用）
        start_time: 区间开始时间
        end_time: 区间结束时间
        interval_seconds: 执行间隔（秒）
        action: 动作类型（append/replace，日K采集专用）
    """
    name: str
    type: str = "once"
    time: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    interval_seconds: int = 60
    action: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典（用于API返回）"""
        result = {"name": self.name, "type": self.type}
        if self.time:
            result["time"] = self.time
        if self.start_time:
            result["start_time"] = self.start_time
        if self.end_time:
            result["end_time"] = self.end_time
        if self.interval_seconds:
            result["interval_seconds"] = self.interval_seconds
        if self.action:
            result["action"] = self.action
        return result


@dataclass
class TaskInfo:
    """
    任务信息
    
    属性：
        name: 任务名称（raw、special_pool、day_k）
        display_name: 显示名称（中文）
        enabled: 是否启用
        status: 当前状态
        last_run_time: 上次执行时间
        last_run_status: 上次执行结果（success/failed/error_msg）
        schedules: 调度配置列表
        scope: 采集范围（如 stock、block）
        threads: 线程数配置
        delays: 延迟配置
    """
    name: str
    display_name: str
    enabled: bool = True
    status: TaskStatus = TaskStatus.IDLE
    last_run_time: Optional[datetime] = None
    last_run_status: str = "never"
    schedules: List[Schedule] = field(default_factory=list)
    scope: Dict[str, bool] = field(default_factory=dict)
    threads: Dict[str, int] = field(default_factory=dict)
    delays: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典（用于API返回）"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "enabled": self.enabled,
            "status": self.status.value,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_run_status": self.last_run_status,
            "schedules": [s.to_dict() for s in self.schedules],
            "scope": self.scope,
            "threads": self.threads,
            "delays": self.delays,
        }


class TaskManager:
    """
    任务管理器（单例）
    
    功能：
        - 管理所有采集任务的生命周期
        - 配置内存化，支持动态修改
        - 轻量调度线程，节省资源
    
    使用方式：
        manager = TaskManager.get_instance()
        manager.start()                    # 启动调度
        manager.enable_task("raw")          # 开启快照采集
        manager.run_task_once("special_pool")  # 手动执行特殊股票池
    """
    
    _instance: Optional["TaskManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self._initialized = True
        
        # 任务字典（内存）
        self.tasks: Dict[str, TaskInfo] = {}
        
        # 原始配置（内存，用于持久化）
        self.config: Dict = {}
        
        # 调度器状态
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()  # 任务执行锁（防止同一任务重复触发）
        
        # 上次执行时间记录（用于区间调度）
        self._last_interval_run: Dict[str, int] = {}
        
        # 执行函数映射
        self._execute_funcs: Dict[str, Callable] = {}
        
        # 加载配置
        self.load_config()
    
    # ==================== 配置管理 ====================
    
    def load_config(self) -> bool:
        """
        从文件加载配置到内存
        
        返回：
            True=成功, False=失败
        """
        try:
            if not CONFIG_FILE.exists():
                logger.error(f"配置文件不存在: {CONFIG_FILE}")
                return False
            
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
            
            # 解析任务配置
            self._parse_tasks_from_config()
            
            logger.info("任务配置加载成功")
            return True
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False
    
    def _parse_tasks_from_config(self):
        """从配置解析任务信息"""
        # 快照采集任务
        raw_config = self.config.get("raw", {})
        self.tasks["raw"] = TaskInfo(
            name="raw",
            display_name="快照采集",
            enabled=raw_config.get("enabled", True),
            schedules=self._parse_schedules(raw_config.get("schedules", [])),
            scope=raw_config.get("scope", {"stock": True, "block": True}),
            threads=raw_config.get("threads", {"stock": 30, "block": 1}),
            delays=raw_config.get("delays", {"min_ms": 100, "max_ms": 200}),
        )
        
        # 特殊股票池任务
        special_config = self.config.get("special_pool", {})
        self.tasks["special_pool"] = TaskInfo(
            name="special_pool",
            display_name="特殊股票池采集",
            enabled=special_config.get("enabled", True),
            schedules=self._parse_schedules(special_config.get("schedules", [])),
            scope=special_config.get("scope", {"zt": True, "zrzt": True, "zb": True, "dt": True}),
        )
        
        # 日K采集任务
        day_k_config = self.config.get("day_k", {})
        self.tasks["day_k"] = TaskInfo(
            name="day_k",
            display_name="日K采集",
            enabled=day_k_config.get("enabled", True),
            schedules=self._parse_schedules(day_k_config.get("schedules", [])),
            scope=day_k_config.get("scope", {"stock": True, "block": True}),
        )
        
        # 注册执行函数
        self._register_execute_funcs()
    
    def _parse_schedules(self, schedules_data: List[Dict]) -> List[Schedule]:
        """解析调度配置列表"""
        schedules = []
        for item in schedules_data:
            schedules.append(Schedule(
                name=item.get("name", ""),
                type=item.get("type", "once"),
                time=item.get("time"),
                start_time=item.get("start_time"),
                end_time=item.get("end_time"),
                interval_seconds=item.get("interval_seconds", 30),
                action=item.get("action"),
            ))
        return schedules
    
    def _register_execute_funcs(self):
        """注册任务执行函数（延迟导入避免循环依赖）"""
        self._execute_funcs = {
            "raw": self._execute_raw,
            "special_pool": self._execute_special_pool,
            "day_k": self._execute_day_k,
        }
    
    def save_config(self) -> bool:
        """
        保存内存配置到文件
        
        返回：
            True=成功, False=失败
        """
        try:
            # 同步任务状态到配置
            self._sync_tasks_to_config()
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info("配置已保存到文件")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def _sync_tasks_to_config(self):
        """同步任务状态到配置字典"""
        for task_name, task in self.tasks.items():
            config_key = task_name if task_name != "day_k" else "day_k"
            if config_key in self.config:
                self.config[config_key]["enabled"] = task.enabled
                self.config[config_key]["schedules"] = [s.to_dict() for s in task.schedules]
    
    # ==================== 任务执行 ====================
    
    def _execute_raw(self):
        """执行快照采集"""
        try:
            from app.collectors.stock_raw_collector import StockRawCollector
            from app.collectors.block_raw_collector import BlockRawCollector
            from app.collectors.factor_calculator import FactorCalculator
            from app.utils.batch_no import generate_batch_no
            
            logger.info("执行快照采集...")
            
            # 统一生成批次号，确保股票和板块数据使用相同的批次号
            raw_no, trade_date, snapshot_time = generate_batch_no()
            logger.info(f"统一批次号: {raw_no}, 交易日期: {trade_date}")
            
            # 先跑板块（标记新增关注股），再跑股票（使用统一批次号）
            BlockRawCollector.collect(raw_no=raw_no, trade_date=trade_date, snapshot_time=snapshot_time)
            StockRawCollector.collect(raw_no=raw_no, trade_date=trade_date, snapshot_time=snapshot_time)
            
            # 采集完成后自动触发因子计算
            logger.info(f"快照采集完成，开始计算因子...")
            result = FactorCalculator.calculate_for_raw_no(stock_raw_no=raw_no, block_raw_no=raw_no)
            logger.info(f"因子计算完成: {result}")
            
            return "success"
        except Exception as e:
            logger.error(f"快照采集失败: {e}")
            return f"failed: {str(e)}"
    
    def _execute_special_pool(self):
        """执行特殊股票池采集"""
        try:
            from app.collectors.special_pool_collector import SpecialPoolCollector
            
            logger.info("执行特殊股票池采集...")
            SpecialPoolCollector.collect_all()
            return "success"
        except Exception as e:
            logger.error(f"特殊股票池采集失败: {e}")
            return f"failed: {str(e)}"
    
    def _execute_day_k(self, action: str = "replace"):
        """
        执行日K采集
        
        参数：
            action: append（追加）或 replace（替换）
        """
        try:
            from app.collectors.day_collector import DayCollector
            
            logger.info(f"执行日K采集... (action={action})")
            DayCollector.collect_all(action=action)
            return "success"
        except Exception as e:
            logger.error(f"日K采集失败: {e}")
            return f"failed: {str(e)}"
    
    # ==================== 任务控制 ====================
    
    def get_all_tasks_status(self) -> Dict:
        """
        获取所有任务状态
        
        返回：
            {
                "scheduler_running": bool,
                "tasks": [TaskInfo.to_dict(), ...]
            }
        """
        return {
            "scheduler_running": self._running,
            "tasks": [task.to_dict() for task in self.tasks.values()],
        }
    
    def enable_task(self, task_name: str) -> bool:
        """
        开启单个任务
        
        参数：
            task_name: 任务名称（raw/special_pool/day_k）
        
        返回：
            True=成功, False=任务不存在
        """
        if task_name not in self.tasks:
            logger.warning(f"任务不存在: {task_name}")
            return False
        
        self.tasks[task_name].enabled = True
        logger.info(f"任务已开启: {task_name}")
        return True
    
    def disable_task(self, task_name: str) -> bool:
        """
        关闭单个任务
        
        参数：
            task_name: 任务名称
        
        返回：
            True=成功, False=任务不存在
        """
        if task_name not in self.tasks:
            logger.warning(f"任务不存在: {task_name}")
            return False
        
        self.tasks[task_name].enabled = False
        logger.info(f"任务已关闭: {task_name}")
        return True
    
    def enable_all_tasks(self):
        """开启所有任务"""
        for task in self.tasks.values():
            task.enabled = True
        logger.info("所有任务已开启")
    
    def disable_all_tasks(self):
        """关闭所有任务"""
        for task in self.tasks.values():
            task.enabled = False
        logger.info("所有任务已关闭")
    
    def run_task_once(self, task_name: str) -> str:
        """
        手动执行单个任务（立即执行，不受调度控制）
        
        参数：
            task_name: 任务名称
        
        返回：
            执行结果（success/failed:xxx）
        """
        if task_name not in self.tasks:
            return f"failed: task not found"
        
        task = self.tasks[task_name]
        task.status = TaskStatus.RUNNING
        
        try:
            # 执行任务
            if task_name == "day_k":
                # 日K默认用replace模式
                result = self._execute_funcs[task_name](action="replace")
            else:
                result = self._execute_funcs[task_name]()
            
            # 更新状态
            task.last_run_time = datetime.now()
            task.last_run_status = result
            task.status = TaskStatus.IDLE
            
            return result
        except Exception as e:
            task.status = TaskStatus.IDLE
            task.last_run_status = f"failed: {str(e)}"
            return f"failed: {str(e)}"
    
    # ==================== 调度配置管理 ====================
    
    def update_task_schedule(self, task_name: str, schedule_index: int, 
                             updates: Dict[str, Any]) -> bool:
        """
        更新任务的调度配置
        
        参数：
            task_name: 任务名称
            schedule_index: 调度项索引
            updates: 更新内容（如 {"interval_seconds": 60}）
        
        返回：
            True=成功, False=失败
        """
        if task_name not in self.tasks:
            return False
        
        task = self.tasks[task_name]
        if schedule_index >= len(task.schedules):
            return False
        
        schedule = task.schedules[schedule_index]
        for key, value in updates.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        logger.info(f"调度配置已更新: {task_name}[{schedule_index}]")
        return True
    
    def add_task_schedule(self, task_name: str, schedule_data: Dict) -> bool:
        """
        添加调度配置项
        
        参数：
            task_name: 任务名称
            schedule_data: 调度配置
        
        返回：
            True=成功, False=失败
        """
        if task_name not in self.tasks:
            return False
        
        new_schedule = Schedule(
            name=schedule_data.get("name", "新调度"),
            type=schedule_data.get("type", "once"),
            time=schedule_data.get("time"),
            start_time=schedule_data.get("start_time"),
            end_time=schedule_data.get("end_time"),
            interval_seconds=schedule_data.get("interval_seconds", 30),
            action=schedule_data.get("action"),
        )
        
        self.tasks[task_name].schedules.append(new_schedule)
        logger.info(f"调度配置已添加: {task_name}")
        return True
    
    def remove_task_schedule(self, task_name: str, schedule_index: int) -> bool:
        """
        删除调度配置项
        
        参数：
            task_name: 任务名称
            schedule_index: 调度项索引
        
        返回：
            True=成功, False=失败
        """
        if task_name not in self.tasks:
            return False
        
        task = self.tasks[task_name]
        if schedule_index >= len(task.schedules):
            return False
        
        task.schedules.pop(schedule_index)
        logger.info(f"调度配置已删除: {task_name}[{schedule_index}]")
        return True
    
    # ==================== 调度器控制 ====================
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("任务调度器已停止")
    
    def is_running(self) -> bool:
        """调度器是否在运行"""
        return self._running
    
    def _scheduler_loop(self):
        """
        调度器主循环
        
        设计：
            - 单线程控制循环，不阻塞等待任务
            - 任务通过线程池并发执行（避免互相等待）
            - 只在交易时段内检查任务
            - 同一任务正在执行时不会重复触发
        """
        logger.info("调度器主循环启动")
        
        # 初始化采集（如果在交易时段内启动）
        if self._is_trading_hours():
            logger.info("交易时段启动，执行初始化采集...")
            for task_name in ["raw", "special_pool"]:
                if self.tasks[task_name].enabled:
                    self._trigger_task_async(task_name)
        
        while self._running:
            now = datetime.now()
            current_time = now.time()
            
            # 非交易时段跳过（保留开盘竞价和收盘时段）
            if not self._is_active_hours():
                self._sleep(10)
                continue
            
            # 检查每个任务（尝试触发，不等待结果）
            for task_name, task in self.tasks.items():
                if not task.enabled:
                    continue
                
                # 检查任务是否正在执行中
                if task.status == TaskStatus.RUNNING:
                    continue
                
                # 检查调度配置
                for schedule in task.schedules:
                    if self._should_run(schedule, task_name):
                        self._trigger_task_async(task_name, schedule)
                        break
            
            self._sleep(1)
        
        logger.info("调度器主循环退出")
    
    def _trigger_task_async(self, task_name: str, schedule: Optional[Schedule] = None):
        """
        异步触发任务执行（不阻塞主循环）
        
        参数：
            task_name: 任务名称
            schedule: 调度配置（用于日K的 action 参数）
        """
        def _run():
            task = self.tasks.get(task_name)
            if not task:
                return
            
            task.status = TaskStatus.RUNNING
            task.last_run_time = datetime.now()
            
            try:
                if task_name == "day_k":
                    action = schedule.action if schedule else "replace"
                    result = self._execute_funcs[task_name](action=action)
                else:
                    result = self._execute_funcs[task_name]()
                
                task.last_run_status = result
            except Exception as e:
                logger.error(f"任务执行异常: {task_name} - {e}")
                task.last_run_status = f"failed: {str(e)}"
            finally:
                task.status = TaskStatus.IDLE
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
    
    def _is_trading_hours(self) -> bool:
        """是否在交易时段内"""
        now = datetime.now()
        t = now.time()
        
        # 周末
        if now.weekday() >= 5:
            return False
        
        # 9:25-11:30 或 13:00-15:05
        return (dt_time(9, 25) <= t <= dt_time(11, 30) or
                dt_time(13, 0) <= t <= dt_time(15, 5))
    
    def _is_active_hours(self) -> bool:
        """是否在活跃时段（需要检查任务）"""
        now = datetime.now()
        t = now.time()
        
        # 周末
        if now.weekday() >= 5:
            return False
        
        # 扩展时段：9:25-11:30 或 13:00-15:10
        return (dt_time(9, 25) <= t <= dt_time(11, 30) or
                dt_time(13, 0) <= t <= dt_time(15, 10))
    
    def _should_run(self, schedule: Schedule, task_name: str) -> bool:
        """
        判断是否应该执行
        
        参数：
            schedule: 调度配置
            task_name: 任务名称
        
        返回：
            True=应该执行, False=不执行
        """
        now = datetime.now()
        current_time = now.time()
        current_seconds = now.hour * 3600 + now.minute * 60 + now.second
        
        if schedule.type == "once":
            # 定点执行
            if not schedule.time:
                return False
            
            parts = schedule.time.split(":")
            run_time = dt_time(int(parts[0]), int(parts[1]), int(parts[2]))
            schedule_seconds = run_time.hour * 3600 + run_time.minute * 60 + run_time.second
            
            # 允许5秒误差
            return abs(current_seconds - schedule_seconds) <= 5
        
        elif schedule.type == "interval":
            # 区间执行
            if not schedule.start_time or not schedule.end_time:
                return False
            
            start_parts = schedule.start_time.split(":")
            end_parts = schedule.end_time.split(":")
            
            start_time = dt_time(int(start_parts[0]), int(start_parts[1]), int(start_parts[2]))
            end_time = dt_time(int(end_parts[0]), int(end_parts[1]), int(end_parts[2]))
            
            start_seconds = start_time.hour * 3600 + start_time.minute * 60 + start_time.second
            end_seconds = end_time.hour * 3600 + end_time.minute * 60 + end_time.second
            
            # 不在区间内
            if not (start_seconds <= current_seconds <= end_seconds):
                return False
            
            # 检查执行间隔
            interval_key = f"{task_name}_{schedule.name}"
            interval = schedule.interval_seconds or 30
            
            last_run = self._last_interval_run.get(interval_key, 0)
            if current_seconds - last_run >= interval:
                self._last_interval_run[interval_key] = current_seconds
                return True
        
        return False
    
    def _sleep(self, seconds: float):
        """休眠（可被中断）"""
        time_module.sleep(seconds)


# ==================== 便捷函数 ====================

def get_task_manager() -> TaskManager:
    """获取任务管理器单例"""
    return TaskManager()


def start_scheduler():
    """启动调度器"""
    get_task_manager().start()


def stop_scheduler():
    """停止调度器"""
    get_task_manager().stop()
