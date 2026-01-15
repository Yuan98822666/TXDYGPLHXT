"""
自动快照运行时状态管理（内存中，重启重置为开启）。
"""

import asyncio


class AutoSnapshotState:
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
        async with self._lock:
            return self._enabled

    async def toggle(self) -> bool:
        async with self._lock:
            self._enabled = not self._enabled
            return self._enabled


auto_snapshot_state = AutoSnapshotState()