#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社头条消息采集器
API: https://www.cls.cn/v3/depth/home/assembled/1000
"""

import logging
import requests
from datetime import datetime
from typing import List, Dict, Any

from app.config.cls_config import get_depth_params

logger = logging.getLogger(__name__)


class CLSHeadlineCollector:
    """财联社头条消息采集器"""
    
    def __init__(self):
        self.base_url = "https://www.cls.cn/v3/depth/home/assembled/1000"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.cls.cn/depth?id=1000',
        }
    
    def fetch_articles(self, mode: str = "incremental") -> tuple:
        """
        采集头条消息
        
        Args:
            mode: "full" 全量(24h), "incremental" 增量(最近)
            
        Returns:
            (获取数量, 插入数量)
        """
        try:
            params = get_depth_params()
            
            logger.info(f"开始采集头条消息 [mode={mode}]")
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("errno") != 0:
                logger.error(f"API返回错误: {data.get('errmsg')}")
                return 0, 0
            
            articles = self._parse_response(data)
            logger.info(f"解析到 {len(articles)} 条头条消息")
            
            # 增量模式：过滤已采集的
            if mode == "incremental":
                last_time = self._get_last_article_time()
                if last_time:
                    articles = [a for a in articles if a.get("publish_time", datetime.now()) > last_time]
                    logger.info(f"增量过滤后剩余 {len(articles)} 条")
            
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
        
        return articles
    
    def _parse_article_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """解析单条文章"""
        try:
            article_id = str(item.get("id", ""))
            if not article_id:
                return None
            
            title = item.get("title", "")
            brief = item.get("brief", "")
            content = brief  # 头条消息通常只有摘要
            
            # 解析时间
            ctime = item.get("ctime")
            publish_time = self._parse_time(ctime)
            
            # 提取股票代码
            stock_codes, stock_names = self._extract_stocks(content)
            
            return {
                "article_id": article_id,
                "title": title,
                "content": content,
                "publish_time": publish_time,
                "stock_codes": stock_codes,
                "stock_names": stock_names,
                "raw_data": item
            }
            
        except Exception as e:
            logger.warning(f"解析文章失败: {str(e)}")
            return None
    
    def _extract_stocks(self, text: str) -> tuple:
        """从文本中提取股票代码"""
        if not text:
            return [], []
        
        import re
        
        # 匹配股票代码模式
        patterns = [
            r'(\d{6})',  # 6位数字
            r'([\u4e00-\u9fa5]{2,4})\s*\((\d{6})\)',  # 名称(代码)
        ]
        
        codes = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    codes.append(match[1] if len(match) > 1 else match[0])
                else:
                    codes.append(match)
        
        # 过滤有效代码
        valid_codes = []
        for code in codes:
            if len(code) == 6 and code.isdigit():
                # 排除创业板、科创板、北交所
                if not (code.startswith("300") or code.startswith("688") or code.startswith("8") or code.startswith("4")):
                    valid_codes.append(code)
        
        # 去重
        seen = set()
        unique_codes = []
        for code in valid_codes:
            if code not in seen:
                seen.add(code)
                unique_codes.append(code)
        
        return unique_codes, []
    
    def _parse_time(self, time_val) -> datetime:
        """解析时间字段"""
        if not time_val:
            return datetime.now()
        
        if isinstance(time_val, int):
            if time_val > 1e10:
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
        from app.models.messagesrc.cls_headline import MessageSrcCLSHeadline
        
        inserted = 0
        
        with get_db_context() as db:
            for article in articles:
                try:
                    # 检查是否已存在
                    existing = db.query(MessageSrcCLSHeadline).filter(
                        MessageSrcCLSHeadline.article_id == article["article_id"]
                    ).first()
                    
                    if existing:
                        continue
                    
                    # 序列化 raw_data
                    raw_data = article["raw_data"].copy()
                    if "publish_time" in raw_data and isinstance(raw_data["publish_time"], datetime):
                        raw_data["publish_time"] = raw_data["publish_time"].strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 创建新记录
                    record = MessageSrcCLSHeadline(
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
        
        logger.info(f"成功保存 {inserted} 条新头条消息")
        return inserted
    
    def _get_last_article_time(self) -> datetime:
        """获取最新文章时间"""
        from app.db.session import get_db_context
        from app.models.messagesrc.cls_headline import MessageSrcCLSHeadline
        
        with get_db_context() as db:
            latest = db.query(MessageSrcCLSHeadline).order_by(
                MessageSrcCLSHeadline.publish_time.desc()
            ).first()
            
            if latest:
                return latest.publish_time
        
        return None


# 全局实例
headline_collector = CLSHeadlineCollector()
