"""
模块: auto_snapshot_state.py
功能: 管理自动采集任务的开关状态。
说明: 使用单例模式在内存中保存状态，支持运行时动态开启/关闭采集任务。
"""

import asyncio


class AutoSnapshotState:
    """
     状态管理器类（单例模式）。

     属性:
         _instance: 类的唯一实例。
         _lock (asyncio.Lock): 异步锁，保证在协程并发下的状态读写安全。
         _enabled (bool): 布尔值，表示任务是否开启。

     逻辑说明:
         __new__ 方法确保全局只有一个实例存在。
         使用异步锁保护 _enabled 变量的读写操作。
     """
    _instance = None
    _lock: asyncio.Lock
    _enabled: bool

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
            cls._instance._enabled = True  # 默认开启
        return cls._instance

    async def is_enabled(self) -> bool:
        """
        获取当前状态。

        返回:
            bool: True 表示开启，False 表示关闭。
        """

        async with self._lock:
            return self._enabled

    async def toggle(self) -> bool:
        """
        切换状态（开变关，关变开）。

        返回:
            bool: 切换后的新状态。
        """

        async with self._lock:
            self._enabled = not self._enabled
            return self._enabled

# 全局状态实例
auto_snapshot_state = AutoSnapshotState()