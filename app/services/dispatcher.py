"""
文件名：dispatcher.py
作用说明：
    采集调度器模板
    管理所有采集器按顺序执行，生成统一快照批次（kz_no）
"""

import datetime
from app.services.collectors.kz_generator import KZGenerator

class Dispatcher:
    """
    类名：Dispatcher
    中文名：采集任务调度器

    职责：
        1. 注册采集器任务
        2. 按顺序执行采集器
        3. 为每次调度生成唯一快照批次号
        4. 统一管理日志和异常
    """

    def __init__(self, db_session):
        """
        初始化调度器

        参数：
            db_session: SQLAlchemy 会话
        """
        self.db = db_session
        self.tasks = []  # 存放采集器及参数的列表

    def register(self, collector_cls, **kwargs):
        """
        注册一个采集器任务

        参数：
            collector_cls: 采集器类
            kwargs: 传给采集器 collect 方法的参数
        """
        self.tasks.append((collector_cls, kwargs))

    def run(self):
        """
        执行注册的所有采集器任务
        """
        kz_no = KZGenerator.next_kz_no()
        print(f"[Dispatcher] 本次调度批次号 kz_no={kz_no}")

        for collector_cls, kwargs in self.tasks:
            try:
                collector = collector_cls(self.db)
                kwargs["kz_no"] = kz_no  # 统一批次号
                if "market_time" not in kwargs:
                    kwargs["market_time"] = datetime.datetime.now()

                print(f"[Dispatcher] 开始执行 {collector_cls.__name__}")
                count = collector.collect(**kwargs)
                print(f"[Dispatcher] {collector_cls.__name__} 成功写入 {count} 条记录")

            except Exception as e:
                print(f"[Dispatcher] {collector_cls.__name__} 执行异常: {e}")
                continue
