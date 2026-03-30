# -*- coding: utf-8 -*-
"""
采集频率配置加载器

用途：从 YAML 配置文件加载采集频率，支持运行时修改
"""
import os
import yaml
import logging
from typing import Dict, List, Optional
from datetime import time as dt_time
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config" / "collection_schedule.yaml"


class ScheduleConfig:
    """采集频率配置类"""

    _config: Optional[Dict] = None
    _last_load: float = 0

    @classmethod
    def reload(cls) -> Dict:
        """重新加载配置"""
        cls._config = None
        return cls.load()

    @classmethod
    def load(cls, force: bool = False) -> Dict:
        """
        加载配置

        参数:
            force: 是否强制重新加载

        返回:
            配置字典
        """
        import time

        if cls._config and not force:
            return cls._config

        if not CONFIG_FILE.exists():
            logger.error(f"配置文件不存在: {CONFIG_FILE}")
            return {}

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cls._config = yaml.safe_load(f)
                cls._last_load = time.time()
                logger.info(f"配置文件加载成功: {CONFIG_FILE}")
                return cls._config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    @classmethod
    def get(cls, key: str, default=None):
        """获取配置项"""
        config = cls.load()
        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    @classmethod
    def get_raw_config(cls) -> Dict:
        """获取快照采集配置"""
        return cls.get("snapshot", {})

    @classmethod
    def get_day_k_config(cls) -> Dict:
        """获取日K采集配置"""
        return cls.get("day_k", {})

    @classmethod
    def get_special_pool_config(cls) -> Dict:
        """获取特殊股票池配置"""
        return cls.get("special_pool", {})

    @classmethod
    def get_base_config(cls) -> Dict:
        """获取基础数据采集配置"""
        return cls.get("base", {})

    @classmethod
    def get_anti_ban_config(cls) -> Dict:
        """获取防封禁配置"""
        return cls.get("anti_ban", {})

    @classmethod
    def get_threads(cls, collector_type: str) -> int:
        """获取线程数配置"""
        threads = cls.get(f"raw.threads.{collector_type}", 1)
        return threads

    @classmethod
    def get_delay_range(cls) -> tuple:
        """获取延时范围 (min_ms, max_ms)"""
        delays = cls.get("raw.delays", {})
        return delays.get("min_ms", 100), delays.get("max_ms", 200)

    @classmethod
    def is_enabled(cls, collector_type: str) -> bool:
        """检查采集器是否启用"""
        return cls.get(f"{collector_type}.enabled", False)

    @classmethod
    def get_collect_time(cls, collector_type: str) -> str:
        """获取采集时间"""
        return cls.get(f"{collector_type}.collect_time", "15:00:00")

    @classmethod
    def get_raw_schedules(cls) -> List[Dict]:
        """获取快照采集时间段配置"""
        return cls.get("raw.schedules", [])

    @classmethod
    def update(cls, key: str, value) -> bool:
        """
        更新配置项

        参数:
            key: 配置键（如 "raw.threads.stock"）
            value: 配置值

        返回:
            是否更新成功
        """
        config = cls.load()
        keys = key.split(".")
        
        # 遍历到最后一层
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            cls.reload()
            logger.info(f"配置已更新: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False


# 便捷函数
def get_config() -> Dict:
    """获取完整配置"""
    return ScheduleConfig.load()


def get_threads(collector_type: str) -> int:
    """获取线程数"""
    return ScheduleConfig.get_threads(collector_type)


def get_delay_range() -> tuple:
    """获取延时范围"""
    return ScheduleConfig.get_delay_range()


if __name__ == "__main__":
    # 测试
    import json

    config = ScheduleConfig.load()
    print("=== 采集频率配置 ===")
    print(json.dumps(config, ensure_ascii=False, indent=2))
