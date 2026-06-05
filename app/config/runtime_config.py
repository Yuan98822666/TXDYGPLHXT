# -*- coding: utf-8 -*-
"""
运行时配置模块

支持动态修改配置项，无需重启服务
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class RuntimeConfig:
    """运行时配置"""
    # 数据库连接池
    db_pool_size: int = 20
    db_max_overflow: int = 40
    
    # 股票采集器配置（与前端字段名保持一致）
    stock_max_workers: int = 5
    stock_batch_size: int = 100
    stock_batch_delay: float = 2.0
    
    # HTTP超时配置
    http_timeout_default: int = 15
    http_timeout_fast: int = 3
    
    def update(self, **kwargs) -> bool:
        """更新配置项"""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def reset_to_defaults(self):
        """重置为默认值"""
        self.db_pool_size = 20
        self.db_max_overflow = 40
        self.stock_max_workers = 5
        self.stock_batch_size = 100
        self.stock_batch_delay = 2.0
        self.http_timeout_default = 15
        self.http_timeout_fast = 3
    
    # Getter methods for collector config
    def get_stock_max_workers(self) -> int:
        return self.stock_max_workers
    
    def get_stock_batch_size(self) -> int:
        return self.stock_batch_size
    
    def get_stock_batch_delay(self) -> float:
        return self.stock_batch_delay


# 全局运行时配置实例
runtime_config = RuntimeConfig()


def get_runtime_config() -> RuntimeConfig:
    """获取运行时配置实例"""
    return runtime_config
