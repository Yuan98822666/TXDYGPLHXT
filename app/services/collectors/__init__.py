"""
文件名：stock_snapshot_collector.py
作用说明：
    个股原始行情快照采集器。

    用于在某一市场时间点，
    针对“已被板块点名的股票”，
    采集其真实的行情、成交、资金等原始事实，
    并写入 RawStockSnapshotEvent 表。

所属层级：
    services 层 - collectors 子系统

设计原则：
    1. 只采集被点名股票
    2. 不推断，不加工
    3. 所有字段均保持接口原始语义
"""

import datetime
from typing import Dict

from app.models.raw.raw_stock_snapshot_event import RawStockSnapshotEvent


class StockSnapshotCollector:
    """
    个股原始快照采集器（点名股票）
    """

    def __init__(self, db_session):
        """
        初始化采集器

        参数：
            db_session:
                数据库会话
        """
        self.db = db_session

    # =========================================================
    # 外部入口
    # =========================================================
    def collect(
        self,
        kz_no: int,
        market_time: datetime.datetime,
        stock_code: str,
        exchange: str,
    ):
        """
        执行单只股票的原始快照采集

        参数：
            kz_no:
                快照批次号
            market_time:
                市场时间
            stock_code:
                股票代码
            exchange:
                交易所 SH / SZ
        """

        # 1️⃣ 行情数据
        snapshot_data = self._fetch_stock_snapshot(
            stock_code=stock_code,
            exchange=exchange
        )

        # 2️⃣ 资金数据
        fund_data = self._fetch_stock_fund(
            stock_code=stock_code,
            exchange=exchange
        )

        # 3️⃣ 合并数据
        merged = self._merge_snapshot(snapshot_data, fund_data)

        # 4️⃣ 解析并生成 ORM
        event = self._parse_stock(
            merged_data=merged,
            kz_no=kz_no,
            market_time=market_time
        )

        if event:
            self._persist(event)
            self.db.commit()

    # =========================================================
    # 数据获取（接口层，暂不实现）
    # =========================================================
    def _fetch_stock_snapshot(self, stock_code: str, exchange: str) -> Dict:
        """
        获取个股行情快照

        返回：
            dict：行情接口原始 JSON
        """
        # TODO: 调用 东方财富 个股行情接口
        return {}

    def _fetch_stock_fund(self, stock_code: str, exchange: str) -> Dict:
        """
        获取个股资金流向数据

        返回：
            dict：资金接口原始 JSON
        """
        # TODO: 调用 东方财富 个股资金接口
        return {}

    # =========================================================
    # 数据合并
    # =========================================================
    def _merge_snapshot(self, snapshot: Dict, fund: Dict) -> Dict:
        """
        合并行情与资金数据

        说明：
            - 不做冲突处理
            - 后写字段覆盖前写字段

        返回：
            dict：合并后的原始数据
        """
        merged = {}
        if snapshot:
            merged.update(snapshot)
        if fund:
            merged.update(fund)
        return merged

    # =========================================================
    # 数据解析
    # =========================================================
    def _parse_stock(
        self,
        merged_data: Dict,
        kz_no: int,
        market_time: datetime.datetime
    ) -> RawStockSnapshotEvent:
        """
        解析合并后的个股数据，生成 ORM 实例
        """

        try:
            event = RawStockSnapshotEvent(
                kz_no=kz_no,

                # ---------- 股票身份 ----------
                stock_code=merged_data.get("f57"),
                stock_name=merged_data.get("f58"),

                # ---------- 行情 ----------
                dqjg=merged_data.get("f43"),
                zde=merged_data.get("f169"),
                ztjg=merged_data.get("f51"),
                zdf=merged_data.get("f170"),
                cjl=merged_data.get("f47"),
                cje=merged_data.get("f48"),
                hsl=merged_data.get("f168"),
                zf=merged_data.get("f92"),

                # ---------- 资金 ----------
                zl_inflow=merged_data.get("f137"),
                cd_inflow=merged_data.get("f140"),
                dd_inflow=merged_data.get("f143"),
                zd_inflow=merged_data.get("f146"),
                xd_inflow=merged_data.get("f149"),

                zl_jzb=merged_data.get("f193"),
                cd_jzb=merged_data.get("f194"),
                dd_jzb=merged_data.get("f195"),
                zd_jzb=merged_data.get("f196"),
                xd_jzb=merged_data.get("f197"),

                # ---------- 规模 ----------
                total_market_cap=merged_data.get("f116"),
                circulating_market_cap=merged_data.get("f117"),
                pe=merged_data.get("f162"),
                pb=merged_data.get("f167"),

                # ---------- 时间 ----------
                market_time=market_time,
                fetch_time=datetime.datetime.utcnow(),
            )
            return event

        except Exception:
            # TODO: 统一日志
            return None

    # =========================================================
    # 数据持久化
    # =========================================================
    def _persist(self, event: RawStockSnapshotEvent):
        """
        写入数据库
        """
        self.db.add(event)
