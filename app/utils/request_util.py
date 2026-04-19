# -*- coding: utf-8 -*-
"""
东方财富统一请求工具

功能：
1. 自动注入 Cookie 和防反爬 Headers
2. 统一 JSONP 解析
3. 错误处理和重试
4. 所有请求参数统一从 request_conf.yaml 读取

使用方式：
    from app.utils.request_util import EastMoneyRequest

    # 板块列表
    blocks = EastMoneyRequest.get_blocks("concept")

    # 成分股
    data = EastMoneyRequest.get_block_stocks("BK0968", page=1)

    # 股票列表
    data = EastMoneyRequest.get_stocks(page=1)
"""
import time
import random
import json
import logging
from typing import Dict, Any, Optional, List
from curl_cffi.requests import Session

from app.utils.cookie_manager import get_cookies
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EastMoneyRequest:
    """东方财富统一请求工具"""

    _session: Optional[Session] = None

    # 防反爬 Headers
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
    }

    @classmethod
    def _get_session(cls) -> Session:
        """获取或创建 Session"""
        if cls._session is None:
            cls._session = Session(impersonate="chrome120")
            cls._session.headers.update(cls.HEADERS)
        return cls._session

    @classmethod
    def _get_endpoint(cls, key: str) -> Dict[str, Any]:
        """
        从 request_conf.yaml 读取指定接口配置

        参数:
            key: endpoints 下的 key 名，如 "board_concept"、"block_stocks"、"base_stocks"

        返回:
            配置字典（已合并 common 参数）
        """
        cfg = settings.request_config
        endpoint = cfg.endpoints[key].model_dump(exclude_none=True)
        common = cfg.common.model_dump()

        # common 参数作为默认值，endpoint 参数优先
        merged = {**common, **endpoint}
        return merged

    @classmethod
    def get_jsonp(cls, url: str, params: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
        """
        发送 GET 请求获取 JSONP 数据

        参数:
            url: API 接口 URL
            params: 请求参数（会自动添加 cb 和 _ 时间戳）
            timeout: 超时时间（秒）

        返回:
            解析后的 JSON 数据字典
        """
        session = cls._get_session()

        # 随机延迟
        time.sleep(random.uniform(0.1, 0.3))

        # 获取 Cookie
        cookies = get_cookies()

        # 生成动态回调名
        ts = int(time.time() * 1000)
        cb = params.get("cb", f"jQuery{ts}")
        params["cb"] = cb
        params.setdefault("_", ts + 1)

        try:
            resp = session.get(url, params=params, cookies=cookies, timeout=timeout)
            resp.raise_for_status()
            text = resp.text.strip()

            # 解析 JSONP
            if f"{cb}(" in text:
                json_str = text.split(f"{cb}(", 1)[1].rsplit(")", 1)[0]
                return json.loads(json_str)
            elif "(" in text and ")" in text:
                start = text.find("(")
                end = text.rfind(")")
                json_str = text[start + 1:end]
                return json.loads(json_str)
            else:
                return json.loads(text)

        except Exception as e:
            logger.error(f"请求失败: {url} - {e}")
            raise

    @classmethod
    def get_blocks(cls, board_type: str = "concept") -> list:
        """
        获取板块列表

        参数:
            board_type: "concept"（概念板块）或 "industry"（行业板块）

        返回:
            [{"code": "BK0968", "name": "固态电池", "type": "GN"}, ...]
        """
        key_map = {"concept": "board_concept", "industry": "board_industry"}
        type_map = {"concept": "GN", "industry": "HY"}

        yaml_key = key_map.get(board_type, "board_concept")
        block_type = type_map.get(board_type, "GN")
        cfg = cls._get_endpoint(yaml_key)
        url = cfg.pop("url")

        params = {
            "np":    cfg.get("np", "1"),
            "fltt":  cfg.get("fltt", "2"),
            "invt":  cfg.get("invt", "2"),
            "fs":    cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid":   cfg.get("fid"),
            "pz":    cfg.get("pz", "500"),
            "po":    cfg.get("po", "1"),
            "ut":    cfg.get("ut"),     # 来自 yaml common.ut
        }

        all_blocks = []
        page = 1

        while True:
            params["pn"] = str(page)
            try:
                data = cls.get_jsonp(url, dict(params))
                if data.get("rc") != 0:
                    break

                diff = data.get("data", {}).get("diff", [])
                if not diff:
                    break

                for item in diff:
                    code = item.get("f12")
                    name = item.get("f14")
                    if code and name:
                        all_blocks.append({
                            "code": code,
                            "name": name,
                            "type": block_type,
                        })

                if len(diff) < int(params["pz"]):
                    break
                page += 1
            except Exception as e:
                logger.error(f"获取板块列表失败: {e}")
                break

        return all_blocks

    @classmethod
    def get_block_stocks(cls, block_code: str, page: int = 1, page_size: int = 100) -> Optional[Dict]:
        """
        获取板块成分股

        参数:
            block_code: 板块代码（如 BK0968）
            page: 页码
            page_size: 每页数量

        返回:
            {"total": 总数, "codes": [股票代码列表], "data": [原始数据]}
        """
        cfg = cls._get_endpoint("block_stocks")
        url = cfg.pop("url")

        params = {
            "np":    cfg.get("np", "1"),
            "fltt":  cfg.get("fltt", "1"),
            "invt":  cfg.get("invt", "2"),
            "fs":    f"b:{block_code.lower()}+f:!50",   # 动态拼接
            "fields": cfg.get("fields", "f12"),
            "fid":   cfg.get("fid", "f3"),
            "pn":    str(page),
            "pz":    str(page_size),
            "po":    cfg.get("po", "1"),
            "dect":  cfg.get("dect", "1"),
            "ut":    cfg.get("ut"),                       # 来自 yaml common.ut
            "wbp2u": cfg.get("wbp2u"),                    # 来自 yaml block_stocks.wbp2u
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                total = data.get("data", {}).get("total", 0)
                codes = [item.get("f12") for item in diff if item.get("f12")]
                return {"total": total, "codes": codes, "data": diff}
        except Exception as e:
            logger.error(f"获取板块成分股失败: {block_code} - {e}")

        return None

    @classmethod
    def get_stocks(cls, page: int = 1, page_size: int = 100) -> Optional[Dict]:
        """
        获取股票列表

        参数:
            page: 页码
            page_size: 每页数量

        返回:
            {"total": 总数, "stocks": [{...}, ...]}
        """
        cfg = cls._get_endpoint("base_stocks")
        url = cfg.pop("url")

        params = {
            "np":    cfg.get("np", "1"),
            "fltt":  cfg.get("fltt", "2"),
            "invt":  cfg.get("invt", "2"),
            "fs":    cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid":   cfg.get("fid", "f12"),
            "pn":    str(page),
            "pz":    str(page_size),
            "po":    cfg.get("po", "1"),
            "ut":    cfg.get("ut"),     # 来自 yaml common.ut
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                total = data.get("data", {}).get("total", 0)
                return {"total": total, "stocks": diff}
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")

        return None

    # ==========================================
    # v0.2.0 新增：涨停池/炸板池/跌停池/快照接口
    # ==========================================

    @classmethod
    def get_zt_pool(cls) -> set:
        """
        获取涨停池股票代码集合

        返回:
            {"300750", "002460", ...}
        """
        cfg = cls._get_endpoint("zt_pool")
        url = cfg.pop("url")

        params = {
            "np": cfg.get("np", "1"),
            "fltt": cfg.get("fltt", "2"),
            "invt": cfg.get("invt", "2"),
            "fs": cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid": cfg.get("fid"),
            "po": cfg.get("po", "1"),
            "pz": cfg.get("pz", "500"),
            "ut": cfg.get("ut"),
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                return {item.get("f12") for item in diff if item.get("f12")}
        except Exception as e:
            logger.error(f"获取涨停池失败: {e}")

        return set()

    @classmethod
    def get_zb_pool(cls) -> set:
        """
        获取炸板池股票代码集合

        返回:
            {"300750", "002460", ...}
        """
        cfg = cls._get_endpoint("zb_pool")
        url = cfg.pop("url")

        params = {
            "np": cfg.get("np", "1"),
            "fltt": cfg.get("fltt", "2"),
            "invt": cfg.get("invt", "2"),
            "fs": cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid": cfg.get("fid"),
            "po": cfg.get("po", "1"),
            "pz": cfg.get("pz", "500"),
            "ut": cfg.get("ut"),
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                return {item.get("f12") for item in diff if item.get("f12")}
        except Exception as e:
            logger.error(f"获取炸板池失败: {e}")

        return set()

    @classmethod
    def get_dt_pool(cls) -> set:
        """
        获取跌停池股票代码集合

        返回:
            {"300750", "002460", ...}
        """
        cfg = cls._get_endpoint("dt_pool")
        url = cfg.pop("url")

        params = {
            "np": cfg.get("np", "1"),
            "fltt": cfg.get("fltt", "2"),
            "invt": cfg.get("invt", "2"),
            "fs": cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid": cfg.get("fid"),
            "po": cfg.get("po", "1"),
            "pz": cfg.get("pz", "500"),
            "ut": cfg.get("ut"),
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                return {item.get("f12") for item in diff if item.get("f12")}
        except Exception as e:
            logger.error(f"获取跌停池失败: {e}")

        return set()

    @classmethod
    def get_stock_raw(cls, secid: str) -> Optional[Dict]:
        """
        获取单只股票的快照数据（支持多域名切换）

        参数:
            secid: 东方财富格式标识，如 "0.000001"（平安银行）、"1.600519"（贵州茅台）

        返回:
            {
                "f43": 1005000,    # 最新价（分）
                "f44": 1012000,    # 最高价（分）
                ...
            }
        """
        import random
        import time as time_module

        ts = int(time_module.time() * 1000)
        cb = f'jQuery{random.randint(10000000000000000, 99999999999999999)}_{ts}'
        
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f51,f52,f60,f85,f116,f117,f137,f140,f143,f146,f149,f162,f167,f168,f169,f170,f171,f193,f194,f195,f196,f197",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "cb": cb,
            "_": ts + 1,
        }

        # 多域名列表（按优先级）
        # push2.eastmoney.com 为主域名，delay/his 为备用
        domains = [
            "push2.eastmoney.com",
            "push2delay.eastmoney.com",
            "push2his.eastmoney.com",
        ]

        cookies = get_cookies()
        last_error = None

        for domain in domains:
            session = cls._get_session()
            url = f"https://{domain}/api/qt/stock/get"
            
            try:
                logger.debug(f"尝试域名: {domain}")
                resp = session.get(url, params=params, cookies=cookies, timeout=3)  # 3秒超时，快速失败
                resp.raise_for_status()
                
                text = resp.text.strip()
                # 解析 JSONP
                if f"{cb}(" in text:
                    json_str = text.split(f"{cb}(", 1)[1].rsplit(")", 1)[0]
                    data = json.loads(json_str)
                else:
                    data = json.loads(text)
                
                if data and data.get("rc") == 0 and data.get("data"):
                    logger.debug(f"域名 {domain} 成功")
                    return data["data"]
                    
            except Exception as e:
                last_error = e
                logger.debug(f"域名 {domain} 失败: {str(e)[:60]}")
                # 重置 session 强制重建连接
                cls._session = None
        
        logger.error(f"获取股票快照失败: {secid} - 所有域名均失败")
        return None

    @classmethod
    def get_block_snapshot_raw(cls) -> list:
        """
        获取所有板块的快照数据（概念+行业+风格）

        返回:
            [
                {
                    "f12": "BK0968",
                    "f14": "固态电池",
                    "f2": 1000.5,   # 最新指数
                    "f3": 2.5,      # 涨跌幅
                    ...
                },
                ...
            ]
        """
        cfg = cls._get_endpoint("block_snapshot")
        url = cfg.get("url")

        params = {
            "pn": "1",  # 必须添加页码参数
            "np": cfg.get("np", "1"),
            "fltt": cfg.get("fltt", "1"),
            "invt": cfg.get("invt", "2"),
            "dect": cfg.get("dect", "1"),
            "wbp2u": cfg.get("wbp2u", "3951356261349626|0|1|0|web"),
            "fs": cfg.get("fs"),
            "fields": cfg.get("fields"),
            "fid": cfg.get("fid"),
            "po": cfg.get("po", "1"),
            "pz": cfg.get("pz", "1000"),
            "ut": cfg.get("ut"),
        }

        try:
            data = cls.get_jsonp(url, params)
            if data.get("rc") == 0:
                diff = data.get("data", {}).get("diff", [])
                return diff
        except Exception as e:
            logger.error(f"获取板块快照失败: {e}")

        return []

    @classmethod
    def get_block_snapshot_all(cls) -> list:
        """
        分页获取所有板块的快照数据（仅概念+行业，排除风格）

        说明：
            东方财富接口每次最多返回100条数据，需要分页获取全量
            只查询 GN（概念）和 HY（行业），排除 FG（风格）

        返回:
            [
                {
                    "f12": "BK0968",
                    "f14": "固态电池",
                    "f2": 1000.5,   # 最新指数
                    "f3": 888,      # 涨跌幅（需要除以100）
                    ...
                },
                ...
            ]
        """
        cfg = cls._get_endpoint("block_snapshot")
        url = cfg.get("url")

        # 只查询 GN（概念）和 HY（行业），排除 FG（风格）
        # m:90+t:3 = 概念板块
        # m:90+s:4 = 行业板块
        fs_list = ["m:90+t:3", "m:90+s:4"]

        all_data = []
        
        for fs in fs_list:
            base_params = {
                "np": cfg.get("np", "1"),
                "fltt": cfg.get("fltt", "1"),
                "invt": cfg.get("invt", "2"),
                "dect": cfg.get("dect", "1"),
                "wbp2u": cfg.get("wbp2u", "3951356261349626|0|1|0|web"),
                "fs": fs,
                "fields": cfg.get("fields"),
                "fid": cfg.get("fid"),
                "po": cfg.get("po", "1"),
                "pz": "100",
                "ut": cfg.get("ut"),
            }
            
            page = 1
            while True:
                params = {**base_params, "pn": str(page)}
                try:
                    data = cls.get_jsonp(url, params)
                    if data.get("rc") != 0:
                        break

                    diff = data.get("data", {}).get("diff", [])
                    if not diff:
                        break

                    all_data.extend(diff)
                    
                    if len(diff) < 100:
                        break
                        
                    page += 1
                except Exception as e:
                    logger.error(f"获取板块快照失败 (fs={fs}, page={page}): {e}")
                    break

        logger.info(f"分页获取板块快照: GN+HY共{len(all_data)}条")
        return all_data

    # ==========================================
    # 特殊股票池接口
    # ==========================================

    @classmethod
    def _get_special_pool(cls, pool_type: str, date_str: str) -> list:
        """
        获取特殊股票池数据（涨停/昨日涨停/强势股/炸板/跌停）

        参数:
            pool_type: 池类型 (zt/zrzt/qs/zb/dt)
            date_str: 日期字符串 (YYYYMMDD)
                - zrzt 用今天日期（getYesterdayZTPool(date=今天) = 今天这个交易日的"昨日涨停"）
                - 其他池用前一交易日日期（盘后数据更完整）

        返回:
            股票池数据列表
        """
        # 接口映射（URL + sort 参数）
        pool_config = {
            "zt": {
                "url": "https://push2ex.eastmoney.com/getTopicZTPool",
                "sort": "fbt:asc",
            },
            "zrzt": {
                "url": "https://push2ex.eastmoney.com/getYesterdayZTPool",
                "sort": "zs:desc",
            },
            "qs": {
                "url": "https://push2ex.eastmoney.com/getTopicQSPool",
                "sort": "zdp:desc",
            },
            "zb": {
                "url": "https://push2ex.eastmoney.com/getTopicZBPool",
                "sort": "fbt:asc",
            },
            "dt": {
                "url": "https://push2ex.eastmoney.com/getTopicDTPool",
                "sort": "fund:asc",
            },
        }

        cfg = pool_config.get(pool_type)
        if not cfg:
            logger.error(f"未知的股票池类型: {pool_type}")
            return []

        base_url = cfg["url"]
        base_params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "pagesize": "170",
            "sort": cfg["sort"],
            "date": date_str,
        }

        all_data = []
        page_index = 0

        while True:
            params = {
                **base_params,
                "Pageindex": str(page_index),
                "_": str(int(time.time() * 1000)),
            }
            try:
                data = cls.get_jsonp(base_url, params)
                if data.get("rc") != 0:
                    break

                pool = data.get("data", {}).get("pool", [])
                if not pool:
                    break

                all_data.extend(pool)

                # 如果返回少于 pagesize，说明是最后一页
                if len(pool) < 170:
                    break

                page_index += 1
            except Exception as e:
                logger.error(f"获取{pool_type}股票池失败 (page={page_index}): {e}")
                break

        logger.info(f"获取{pool_type}股票池: 共{len(all_data)}条, {page_index + 1}页")
        return all_data

    @classmethod
    def get_zt_pool(cls, date_str: str) -> list:
        """获取涨停池"""
        return cls._get_special_pool("zt", date_str)

    @classmethod
    def get_zrzt_pool(cls, date_str: str) -> list:
        """获取昨日涨停池"""
        return cls._get_special_pool("zrzt", date_str)

    @classmethod
    def get_qs_pool(cls, date_str: str) -> list:
        """获取强势股池"""
        return cls._get_special_pool("qs", date_str)

    @classmethod
    def get_zb_pool(cls, date_str: str) -> list:
        """获取炸板池"""
        return cls._get_special_pool("zb", date_str)

    @classmethod
    def get_dt_pool(cls, date_str: str) -> list:
        """获取跌停池"""
        return cls._get_special_pool("dt", date_str)


# 兼容旧代码的别名
eastmoney_client = type("EastMoneyClient", (), {
    "get_jsonp": staticmethod(EastMoneyRequest.get_jsonp)
})()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== 测试统一请求工具 ===\n")

    result = EastMoneyRequest.get_block_stocks("BK0968")
    if result:
        print(f"BK0968: {result['total']} 只, 前5只: {result['codes'][:5]}")

    blocks = EastMoneyRequest.get_blocks("concept")
    print(f"概念板块: {len(blocks)} 个")
