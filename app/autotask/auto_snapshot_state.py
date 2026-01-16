"""
模块: auto_snapshot_state.py
功能: 管理自动采集任务的开关状态。
说明: 使用单例模式在内存中保存状态，支持运行时动态开启/关闭采集任务。

设计目标：
- 线程安全：在异步环境下保证状态读写的原子性
- 单例模式：全局唯一状态实例，避免状态分散
- 内存存储：轻量级实现，重启后恢复默认值
- 简单接口：提供清晰的状态查询和切换方法

适用场景：
- 临时调试：运行时关闭自动采集进行手动测试
- 维护模式：系统维护期间暂停自动任务
- 应急控制：出现问题时快速停止自动采集

局限性：
- 状态不持久化：服务重启后恢复默认开启状态
- 如需持久化：需要扩展为数据库存储方案
"""

import asyncio


class AutoSnapshotState:
    """
    状态管理器类（单例模式）。

    属性:
        _instance: 类的唯一实例（单例实现）
        _lock (asyncio.Lock): 异步锁，保证在协程并发下的状态读写安全
        _enabled (bool): 布尔值，表示任务是否开启（默认True）

    逻辑说明:
        __new__ 方法确保全局只有一个实例存在
        使用异步锁保护 _enabled 变量的读写操作
        所有公共方法都是异步的，适配 async/await 环境
    """

    _instance = None
    _lock: asyncio.Lock
    _enabled: bool

    def __new__(cls):
        """
        单例模式实现

        逻辑流程：
            1. 检查类变量 _instance 是否已存在
            2. 不存在则创建新实例并初始化属性
            3. 存在则直接返回已有实例

        初始化内容：
            - 创建异步锁 _lock
            - 设置默认状态 _enabled = True（默认开启）
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
            cls._instance._enabled = True  # 默认开启
        return cls._instance

    async def is_enabled(self) -> bool:
        """
        获取当前状态（异步安全）

        返回:
            bool: True 表示开启，False 表示关闭

        并发安全：
            - 使用异步锁保护状态读取
            - 防止在状态切换过程中读取到中间状态
        """
        async with self._lock:
            return self._enabled

    async def toggle(self) -> bool:
        """
        切换状态（开变关，关变开）（异步安全）

        返回:
            bool: 切换后的新状态

        并发安全：
            - 使用异步锁保护状态修改
            - 保证切换操作的原子性
            - 多个并发切换请求会串行执行
        """
        async with self._lock:
            self._enabled = not self._enabled
            return self._enabled


# 全局状态实例（单例）
# 整个应用使用同一个状态管理器实例
auto_snapshot_state = AutoSnapshotState()