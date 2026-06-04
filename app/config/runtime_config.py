# -*- coding: utf-8 -*-
"""
运行时配置管理模块

功能：
    - 管理采集器运行时配置（线程数、批次大小等）
    - 支持内存中修改，无需重启服务
    - 提供API接口供前端管理

设计要点：
    - 配置存储在内存中，服务重启后从.env重新加载
    - 修改即时生效，下次采集任务会使用新配置
    - 提供配置验证，防止设置不合理值
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from app.config.settings import settings

logger = logging.getLogger(__name__)


class CollectorConfig(BaseModel):
    """采集器运行时配置"""
    
    # 股票采集器配置
    stock_max_workers: int = Field(default=5, ge=1, le=20, description="股票采集器线程数")
    stock_batch_size: int = Field(default=100, ge=10, le=500, description="股票采集器每批数量")
    stock_batch_delay: float = Field(default=2.0, ge=0.1, le=10.0, description="股票采集器批次间隔(秒)")
    
    # 数据库连接池配置
    db_pool_size: int = Field(default=20, ge=5, le=100, description="数据库连接池大小")
    db_max_overflow: int = Field(default=40, ge=0, le=100, description="数据库连接池溢出")
    
    # HTTP超时配置
    http_timeout_default: int = Field(default=15, ge=5, le=60, description="HTTP默认超时(秒)")
    http_timeout_fast: int = Field(default=3, ge=1, le=30, description="HTTP快速超时(秒)")
    
    @field_validator('stock_max_workers')
    @classmethod
    def validate_workers(cls, v: int, info) -> int:
        """验证线程数不超过连接池大小"""
        # 获取db_pool_size的值，如果还没设置则使用默认值
        db_pool = info.data.get('db_pool_size', 20)
        if v > db_pool:
            raise ValueError(f"线程数({v})不能超过连接池大小({db_pool})")
        if v > db_pool // 2:
            logger.warning(f"线程数({v})超过连接池大小({db_pool})的50%，可能导致连接不足")
        return v


class RuntimeConfigManager:
    """
    运行时配置管理器（单例）
    
    使用方式：
        from app.config.runtime_config import get_runtime_config
        config = get_runtime_config()
        
        # 获取配置
        workers = config.get_stock_max_workers()
        
        # 更新配置
        config.update_config({"stock_max_workers": 8})
    """
    
    _instance: Optional['RuntimeConfigManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if RuntimeConfigManager._initialized:
            return
        
        # 从settings加载初始配置
        self._config = CollectorConfig(
            stock_max_workers=settings.STOCK_COLLECTOR_MAX_WORKERS,
            stock_batch_size=settings.STOCK_COLLECTOR_BATCH_SIZE,
            stock_batch_delay=settings.STOCK_COLLECTOR_BATCH_DELAY,
            db_pool_size=settings.DB_POOL_SIZE,
            db_max_overflow=settings.DB_MAX_OVERFLOW,
            http_timeout_default=settings.HTTP_TIMEOUT_DEFAULT,
            http_timeout_fast=settings.HTTP_TIMEOUT_FAST,
        )
        
        RuntimeConfigManager._initialized = True
        logger.info(f"运行时配置管理器初始化完成: {self._config.model_dump()}")
    
    def get_config(self) -> CollectorConfig:
        """获取当前配置"""
        return self._config
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return self._config.model_dump()
    
    def update_config(self, updates: Dict[str, Any]) -> tuple[bool, str]:
        """
        更新配置
        
        Args:
            updates: 要更新的配置项字典
            
        Returns:
            (success, message): 是否成功及提示信息
        """
        try:
            # 创建新配置进行验证
            current_data = self._config.model_dump()
            current_data.update(updates)
            new_config = CollectorConfig(**current_data)
            
            # 验证通过，更新配置
            self._config = new_config
            
            # 记录变更
            changed = [f"{k}={v}" for k, v in updates.items()]
            logger.info(f"运行时配置已更新: {', '.join(changed)}")
            
            return True, f"配置已更新: {', '.join(changed)}"
            
        except ValueError as e:
            logger.error(f"配置更新失败: {e}")
            return False, f"配置验证失败: {e}"
        except Exception as e:
            logger.error(f"配置更新失败: {e}")
            return False, f"更新失败: {e}"
    
    def reset_to_default(self) -> None:
        """重置为默认值（从.env重新加载）"""
        self._config = CollectorConfig(
            stock_max_workers=settings.STOCK_COLLECTOR_MAX_WORKERS,
            stock_batch_size=settings.STOCK_COLLECTOR_BATCH_SIZE,
            stock_batch_delay=settings.STOCK_COLLECTOR_BATCH_DELAY,
            db_pool_size=settings.DB_POOL_SIZE,
            db_max_overflow=settings.DB_MAX_OVERFLOW,
            http_timeout_default=settings.HTTP_TIMEOUT_DEFAULT,
            http_timeout_fast=settings.HTTP_TIMEOUT_FAST,
        )
        logger.info("运行时配置已重置为默认值")
    
    # ========== 便捷方法 ==========
    
    def get_stock_max_workers(self) -> int:
        return self._config.stock_max_workers
    
    def get_stock_batch_size(self) -> int:
        return self._config.stock_batch_size
    
    def get_stock_batch_delay(self) -> float:
        return self._config.stock_batch_delay
    
    def get_db_pool_size(self) -> int:
        return self._config.db_pool_size
    
    def get_db_max_overflow(self) -> int:
        return self._config.db_max_overflow
    
    def get_http_timeout_default(self) -> int:
        return self._config.http_timeout_default
    
    def get_http_timeout_fast(self) -> int:
        return self._config.http_timeout_fast


# 全局实例
def get_runtime_config() -> RuntimeConfigManager:
    """获取运行时配置管理器实例"""
    return RuntimeConfigManager()
