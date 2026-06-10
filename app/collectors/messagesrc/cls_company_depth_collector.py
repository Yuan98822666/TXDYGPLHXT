#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社公司深度资讯采集器
API: https://www.cls.cn/v3/depth/home/assembled/1005
"""

import requests
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from app.config.cls_config import get_depth_params
import logging

logger = logging.getLogger(__name__)

# API配置
COMPANY_DEPTH_URL = "https://www.cls.cn/v3/depth/home/assembled/1005"

class CLSCompanyDepthCollector:
    """财联社公司深度资讯采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://www.cls.cn/depth?id=1005',
            'Origin': 'https://www.cls.cn',
            'Connection': 'keep-alive',
        })
        
    def fetch_articles(self, mode: str = "incremental", 
                      last_time: Optional[datetime] = None) -> Tuple[int, int]:
        """
        采集公司深度资讯
        
        Args:
            mode: "full"=全量, "incremental"=增量
            last_time: 增量模式下的最后采集时间
            
        Returns:
            (获取数量, 新增数量)
        """
        try:
            # 构建请求参数
            params = get_depth_params()
            
            logger.info(f"开始采集公司深度资讯, 模式: {mode}")
            
            response = self.session.get(
                COMPANY_DEPTH_URL,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"请求失败: HTTP {response.status_code}")
                return 0, 0
                
            data = response.json()
            
            if data.get("errno") != 0:
                logger.error(f"API错误: errno={data.get('errno')}, errmsg={data.get('errmsg')}")
                return 0, 0
            
            # 解析文章列表
            articles = self._parse_response(data)
            
            if not articles:
                logger.info("未获取到文章")
                return 0, 0
            
            logger.info(f"获取到 {len(articles)} 篇文章")
            
            # 根据模式过滤
            if mode == "incremental" and last_time:
                articles = [a for a in articles if a.get("publish_time", datetime.now()) > last_time]
                logger.info(f"增量过滤后剩余 {len(articles)} 篇")
            
            # 保存到数据库
            inserted = self._save_articles(articles)
            
            return len(articles), inserted
            
        except Exception as e:
            logger.error(f"采集失败: {str(e)}")
            return 0, 0
    
    def _parse_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析API响应"""
        articles = []
        
        if "data" not in data:
            return articles
            
        data_section = data["data"]
        
        # 1. 解析 depth_list
        if "depth_list" in data_section:
            for item in data_section["depth_list"]:
                if isinstance(item, dict):
                    article = self._parse_article_item(item)
                    if article:
                        articles.append(article)
        
        # 2. 解析 top_article
        if "top_article" in data_section and data_section["top_article"]:
            top = data_section["top_article"]
            if isinstance(top, dict):
                article = self._parse_article_item(top)
                if article:
                    articles.append(article)
            elif isinstance(top, list):
                for item in top:
                    if isinstance(item, dict):
                        article = self._parse_article_item(item)
                        if article:
                            articles.append(article)
        
        # 3. 解析 roll_bar (公司深度通常没有)
        if "roll_bar" in data_section:
            for item in data_section["roll_bar"]:
                if isinstance(item, dict) and "content" in item:
                    article = {
                        "article_id": f"roll_{item.get('id', int(datetime.now().timestamp()))}",
                        "title": item["content"][:100],
                        "content": item["content"],
                        "publish_time": self._parse_time(item.get("time")),
                        "stock_codes": [],
                        "stock_names": [],
                        "source": "roll_bar"
                    }
                    articles.append(article)
        
        return articles
    
    def _parse_article_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析单篇文章"""
        if not item:
            return None
            
        article_id = str(item.get("id", ""))
        if not article_id:
            return None
        
        # 提取股票代码
        content = item.get("content", "")
        stock_codes, stock_names = self._extract_stocks(content)
        
        return {
            "article_id": article_id,
            "title": item.get("title", ""),
            "content": content,
            "publish_time": self._parse_time(item.get("ctime")),
            "stock_codes": stock_codes,
            "stock_names": stock_names,
            "source": "depth_list"
        }
    
    def _extract_stocks(self, content: str) -> Tuple[List[str], List[str]]:
        """从内容中提取股票代码和名称"""
        if not content:
            return [], []
        
        # 匹配6位数字股票代码
        codes = re.findall(r'\b(\d{6})\b', content)
        
        # 过滤掉日期、时间等
        valid_codes = []
        for code in codes:
            # 排除日期格式 (如 2024年)
            if len(code) == 6 and code.isdigit():
                # 排除明显不是股票代码的数字
                if not (code.startswith("20") and len(code) == 6):
                    valid_codes.append(code)
        
        # 去重保持顺序
        seen = set()
        unique_codes = []
        for code in valid_codes:
            if code not in seen:
                seen.add(code)
                unique_codes.append(code)
        
        # 股票名称暂时无法从正文准确提取，留空
        return unique_codes, []
    
    def _parse_time(self, time_val) -> datetime:
        """解析时间字段"""
        if not time_val:
            return datetime.now()
        
        if isinstance(time_val, int):
            # 时间戳（秒或毫秒）
            if time_val > 1e10:  # 毫秒
                time_val = time_val / 1000
            return datetime.fromtimestamp(time_val)
        
        if isinstance(time_val, str):
            try:
                return datetime.strptime(time_val, "%Y-%m-%d %H:%M:%S")
            except:
                try:
                    return datetime.strptime(time_val, "%Y-%m-%d")
                except:
                    return datetime.now()
        
        return datetime.now()
    
    def _save_articles(self, articles: List[Dict[str, Any]]) -> int:
        """保存文章到数据库"""
        from app.db.session import get_db_context
        from app.models.messagesrc.cls_company_depth import MessageSrcCLSCompanyDepth
        import json
        
        inserted = 0
        
        with get_db_context() as db:
            for article in articles:
                try:
                    # 检查是否已存在
                    existing = db.query(MessageSrcCLSCompanyDepth).filter(
                        MessageSrcCLSCompanyDepth.article_id == article["article_id"]
                    ).first()
                    
                    if existing:
                        continue
                    
                    # 序列化 raw_data（处理 datetime）
                    raw_data = article.copy()
                    raw_data["publish_time"] = raw_data["publish_time"].strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 创建新记录
                    record = MessageSrcCLSCompanyDepth(
                        article_id=article["article_id"],
                        title=article["title"],
                        content=article["content"],
                        publish_time=article["publish_time"],
                        stock_codes=article["stock_codes"],
                        stock_names=article["stock_names"],
                        raw_data=raw_data
                    )
                    
                    db.add(record)
                    inserted += 1
                    
                except Exception as e:
                    logger.error(f"保存文章失败 {article.get('article_id')}: {str(e)}")
                    continue
            
            db.commit()
        
        logger.info(f"成功保存 {inserted} 篇新文章")
        return inserted


# 全局实例
company_depth_collector = CLSCompanyDepthCollector()
