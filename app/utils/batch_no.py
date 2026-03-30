# -*- coding: utf-8 -*-
"""
批次号生成工具

批次号格式：YYYYMMDDHHMMSS
用途：同一批次采集的股票快照和板块快照共用同一个批次号，
     便于数据关联分析和一致性校验。

交易日期规则：
- 如果今天是交易日，trade_date = 今天
- 如果今天不是交易日（周末/节假日），trade_date = 最近的交易日
"""
from datetime import datetime
from typing import Tuple

from app.utils.trade_calendar import get_trade_date_str, get_latest_trade_day


class BatchNoGenerator:
    """批次号生成器"""

    @staticmethod
    def generate() -> Tuple[str, str, datetime]:
        """
        生成批次号及相关时间信息

        返回:
            (raw_no, trade_date, snapshot_time)
            - raw_no: 批次号，格式 YYYYMMDDHHMMSS
            - trade_date: 交易日期，格式 YYYY-MM-DD（自动处理周末/节假日）
            - snapshot_time: 采集时间戳
        """
        now = datetime.now()
        raw_no = now.strftime("%Y%m%d%H%M%S")
        # 使用交易日工具获取正确的交易日期
        trade_date = get_trade_date_str()
        snapshot_time = now

        return raw_no, trade_date, snapshot_time

    @staticmethod
    def generate_with_timestamp(ts: datetime) -> Tuple[str, str, datetime]:
        """
        根据指定时间戳生成批次号

        参数:
            ts: 指定时间戳

        返回:
            (raw_no, trade_date, snapshot_time)
        """
        raw_no = ts.strftime("%Y%m%d%H%M%S")
        # 获取指定日期对应的交易日
        from datetime import date
        trade_date_obj = get_latest_trade_day(date(ts.year, ts.month, ts.day))
        trade_date = trade_date_obj.strftime("%Y-%m-%d")

        return raw_no, trade_date, ts

    @staticmethod
    def parse(raw_no: str) -> datetime:
        """
        解析批次号为时间戳

        参数:
            raw_no: 批次号，格式 YYYYMMDDHHMMSS

        返回:
            datetime 对象
        """
        return datetime.strptime(raw_no, "%Y%m%d%H%M%S")


# 便捷函数
def generate_batch_no() -> Tuple[str, str, datetime]:
    """生成批次号"""
    return BatchNoGenerator.generate()


if __name__ == "__main__":
    # 测试
    raw_no, trade_date, snapshot_time = generate_batch_no()
    print(f"批次号: {raw_no}")
    print(f"交易日期: {trade_date}")
    print(f"采集时间: {snapshot_time}")

    # 解析测试
    parsed = BatchNoGenerator.parse(raw_no)
    print(f"解析结果: {parsed}")
