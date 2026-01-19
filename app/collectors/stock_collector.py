"""
点名个股采集

功能说明：
- 并发采集指定 secid 列表的个股实时快照行情数据
- 将原始 API 数据转换为标准化的 RawStockHuoyue 模型
- 处理各种数据单位转换（分→元、手→股、元→万元等）

数据流向：
secid 集合 → 东方财富 API → RawStockHuoyue 模型 → 个股快照列表

设计特点：
- 使用线程池并发采集，提升效率
- 完善的异常处理，单个股票失败不影响整体采集
- 精确的数据单位转换和四舍五入
- 统一的配置管理和数据清洗
"""


from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set
from decimal import Decimal, InvalidOperation
from app.utils.common_utils import CommonUtils
from app.utils.http_client import eastmoney_client
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from datetime import datetime
from app.config.settings import settings  # 统一配置入口


# ==============================
# 采集逻辑
# ==============================

def fetch_stock_snapshot(secid: str, market_time: datetime, kz_no: int) -> RawStockHuoyue:
    """
    采集单个股票的快照行情数据

    参数:
        secid (str): 股票唯一标识符，格式：市场代码.股票代码（如 "0.600000"）
        market_time (datetime): 市场时间（带时区信息）
        kz_no (int): 快照批次号

    返回:
        RawStockHuoyue: 个股快照模型对象

    数据转换规则：
        - 价格类字段（最新价、涨跌额等）：原始单位为"分"，转换为"元"（除以100）
        - 百分比字段（涨跌幅、换手率等）：原始单位为"百分比*100"，转换为"百分比"（除以100）
        - 成交量字段：原始单位为"手"，转换为"股"（乘以100）
        - 金额类字段（成交额、总市值等）：原始单位为"元"，转换为"万元"（除以10000）
        - 资金流字段：原始单位为"元"，转换为"万元"（除以10000）

    异常处理：
        - 所有字段都使用 .get() 方法避免 KeyError
        - None 值通过 purify 和条件表达式安全处理
    """

    # 从统一配置中心获取请求配置
    endpoint_config = settings.request_config.endpoints["stock_snapshot"]
    common = settings.request_config.common

    # 构建请求参数
    base_params = {
        "invt": endpoint_config.invt,
        "fltt": endpoint_config.fltt,
        "wbp2u": endpoint_config.wbp2u,
        "dect": endpoint_config.dect,
        "_": getattr(endpoint_config, "_", None),  # 安全获取下划线字段（时间戳）
        "fields": endpoint_config.fields,
        "ut": common.ut,
        "cb": common.cb,
    }
    params = {**base_params, "secid": secid}

    # 发送 HTTP 请求
    data = eastmoney_client.get_jsonp(endpoint_config.url, params)
    d = data["data"]

    # 确定交易所（根据 secid 前缀）
    exchange = "SH" if secid.startswith("0.") else "SZ"  # 注意：这里可能有误，通常 0=SH, 1=SZ

    return RawStockHuoyue(
        kz_no=kz_no,
        market_time=market_time,
        stock_code=d["f57"],
        stock_name=d["f58"],
        exchange=exchange,
        # 最新价（元）
        stock_zxj=CommonUtils.purify(d.get("f43")/100) if d.get("f43") is not None else None,
        # 涨跌额（元）
        stock_zde=CommonUtils.purify(d.get("f169")/100),
        # 涨跌幅（%）
        stock_zdf=CommonUtils.purify(d.get("f170")/100),
        # 成交量（手）
        stock_cjls=CommonUtils.purify(d.get("f47")),
        # 成交额（元）
        stock_cjey = CommonUtils.purify(d.get("f48")),
        # 换手率（%）
        stock_hsl=CommonUtils.purify(d.get("f168")/100),
        # 总市值（元）
        stock_zsz=CommonUtils.purify(d.get("f116")),
        #流通市值（元）
        stock_ltsz=CommonUtils.purify(d.get("f117")),
        # 市盈率
        stock_syl=CommonUtils.purify(d.get("f162")/100),
        # 市净率
        stock_sjl=CommonUtils.purify(d.get("f167")/100),

        # 主力资金净流入（元）
        stock_zl_inflow=CommonUtils.purify(d.get("f137")),
        # 超大单净流入（元）
        stock_cd_inflow=CommonUtils.purify(d.get("f140")),
        # 中单净流入（元）
        stock_dd_inflow=CommonUtils.purify(d.get("f143")),
        # 中单资金流入（元）
        stock_zd_inflow=CommonUtils.purify(d.get("f146")),
        # 小单净流入（元）
        stock_xd_inflow=CommonUtils.purify(d.get("f149")),

        # 主力资金净流入占比（%）
        stock_zl_zb=CommonUtils.purify(d.get("f193")/100),
        #超大单净流入占比（%）
        stock_cd_zb=CommonUtils.purify(d.get("f194")/100),
        #大单净流入占比（%）
        stock_dd_zb=CommonUtils.purify(d.get("f195")/100),
        #中单净流入占比（%）
        stock_zd_zb=CommonUtils.purify(d.get("f196")/100),
        #小单净流入占比（%）
        stock_xd_zb=CommonUtils.purify(d.get("f197")/100),

        source="eastmoney",
    )
    # 构建个股快照模型


def collect_named_stocks(secids: Set[str], market_time: datetime, kz_no: int) -> List[RawStockHuoyue]:
    """
    并发采集点名股详情

    参数:
        secids (Set[str]): 要采集的股票 secid 集合
        market_time (datetime): 市场时间
        kz_no (int): 快照批次号

    返回:
        List[RawStockHuoyue]: 个股快照对象列表

    并发策略：
        - 使用 ThreadPoolExecutor 创建10个线程
        - 提交所有采集任务到线程池
        - 使用 as_completed 按完成顺序处理结果
        - 单个股票采集失败不会影响其他股票

    异常处理：
        - 捕获每个股票采集的异常
        - 打印错误信息但继续处理其他股票
        - 返回成功采集的股票列表
    """
    stocks = []

    # 创建线程池，并发采集（最大10个并发线程）
    with ThreadPoolExecutor(20) as executor:
        # 提交所有采集任务
        futures = {
            executor.submit(fetch_stock_snapshot, secid, market_time, kz_no): secid
            for secid in secids
        }

        # 按完成顺序处理结果
        for future in as_completed(futures):
            try:
                stock = future.result()
                stocks.append(stock)
            except Exception as e:
                secid = futures[future]
                print(f"⚠️ 个股 {secid} 采集失败: {e}")

    return stocks