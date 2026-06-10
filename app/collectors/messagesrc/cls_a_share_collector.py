#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社 A股消息采集器

采集首页 A股消息板块（depth_a_share）
URL: https://www.cls.cn/v3/depth/home/assembled/1003

特性：
- 从配置文件读取参数
- 支持全量/增量采集
- 自动去重（基于文章ID）
- 关联股票代码提取
"""

import requests
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from app.config.cls_config import get_depth_params, get_cls_endpoint
from app.db.session import get_db_context

import logging

logger = logging.getLogger(__name__)


@dataclass
class AShareArticle:
    """A股消息文章数据类"""
    article_id: str
    title: str
    content: str
    publish_time: datetime
    summary: Optional[str] = None
    stock_codes: Optional[List[str]] = None
    stock_names: Optional[List[str]] = None
    source: Optional[str] = None
    author: Optional[str] = None
    reading_num: int = 0
    share_num: int = 0
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['publish_time'] = self.publish_time.strftime('%Y-%m-%d %H:%M:%S')
        data['stock_codes'] = self.stock_codes or []
        data['stock_names'] = self.stock_names or []
        return data


class CLSAShareCollector:
    """财联社 A股消息采集器"""
    
    # 股票代码提取正则（A股）
    STOCK_CODE_PATTERN = re.compile(r'\b(\d{6})\b')
    # 排除常见非股票6位数字
    EXCLUDE_CODES = {'100000', '200000', '300000', '600000', '000000'}
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.cls.cn/',
            'Origin': 'https://www.cls.cn',
        })
        self._init_session()
    
    def _init_session(self):
        """初始化会话（访问主页获取cookies）"""
        try:
            resp = self.session.get('https://www.cls.cn/', timeout=10)
            logger.info(f"Session init: status={resp.status_code}")
        except Exception as e:
            logger.warning(f"Session init failed: {e}")
    
    def fetch_articles(self, limit: int = 50) -> List[AShareArticle]:
        """
        获取A股消息列表
        
        Args:
            limit: 获取数量（默认50条）
        
        Returns:
            AShareArticle列表
        """
        # 构建请求参数（深度资讯接口需要 sign）
        params = get_depth_params()
        
        url = get_cls_endpoint('depth_a_share')
        
        logger.info(f"Fetching A-share articles from {url}")
        
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            
            if data.get('errno') != 0:
                logger.error(f"API error: {data.get('errmsg', 'Unknown')}")
                return []
            
            articles = self._parse_response(data)
            logger.info(f"Got {len(articles)} articles from API")
            return articles
            
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return []
    
    def _parse_response(self, data: Dict) -> List[AShareArticle]:
        """解析API响应"""
        articles = []
        
        if 'data' not in data or not isinstance(data['data'], dict):
            logger.warning("Invalid response structure: 'data' field missing")
            return articles
        
        # A股深度资讯接口返回的数据结构：
        # data.depth_list: 主要文章列表
        # data.top_article: 置顶文章
        # data.roll_bar: 滚动条（单条）
        
        items = []
        
        # 1. 主要文章列表
        if 'depth_list' in data['data'] and isinstance(data['data']['depth_list'], list):
            items.extend(data['data']['depth_list'])
            logger.info(f"Found {len(data['data']['depth_list'])} items in depth_list")
        
        # 2. 置顶文章
        if 'top_article' in data['data'] and isinstance(data['data']['top_article'], list):
            items.extend(data['data']['top_article'])
            logger.info(f"Found {len(data['data']['top_article'])} items in top_article")
        
        # 3. 滚动条（单条字典）
        if 'roll_bar' in data['data'] and isinstance(data['data']['roll_bar'], dict):
            items.append(data['data']['roll_bar'])
            logger.info("Found 1 item in roll_bar")
        
        for item in items:
            try:
                article = self._parse_article(item)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Parse article failed: {e}")
                continue
        
        return articles
    
    def _parse_article(self, item: Dict) -> Optional[AShareArticle]:
        """解析单条文章"""
        article_id = str(item.get('id', item.get('article_id', '')))
        if not article_id:
            return None
        
        title = item.get('title', '') or item.get('brief', '')
        content = item.get('content', '') or title
        
        # 解析时间
        pub_time = self._parse_time(item.get('ctime', item.get('publish_time', '')))
        
        # 提取股票代码
        stock_codes, stock_names = self._extract_stocks(title + ' ' + content)
        
        return AShareArticle(
            article_id=article_id,
            title=title,
            content=content,
            publish_time=pub_time,
            summary=item.get('summary', ''),
            stock_codes=stock_codes,
            stock_names=stock_names,
            source=item.get('source', '财联社'),
            author=item.get('author', ''),
            reading_num=int(item.get('reading_num', 0)),
            share_num=int(item.get('share_num', 0)),
            image_url=item.get('image', ''),
        )
    
    def _parse_time(self, time_val) -> datetime:
        """解析时间"""
        if isinstance(time_val, (int, float)):
            # 毫秒时间戳
            if time_val > 1e12:
                time_val = time_val / 1000
            return datetime.fromtimestamp(time_val)
        
        if isinstance(time_val, str):
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%d %H:%M',
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(time_val, fmt)
                except ValueError:
                    continue
        
        return datetime.now()
    
    def _extract_stocks(self, text: str) -> Tuple[List[str], List[str]]:
        """从文本中提取股票代码和名称"""
        codes = []
        names = []
        
        if not text:
            return codes, names
        
        # 提取6位数字（股票代码）
        matches = self.STOCK_CODE_PATTERN.findall(text)
        for code in matches:
            if code not in self.EXCLUDE_CODES:
                # 验证股票代码格式
                if self._is_valid_stock_code(code):
                    codes.append(code)
        
        # 去重保持顺序
        seen = set()
        unique_codes = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                unique_codes.append(c)
        
        return unique_codes, names
    
    def _is_valid_stock_code(self, code: str) -> bool:
        """验证股票代码格式"""
        if len(code) != 6 or not code.isdigit():
            return False
        
        # A股代码规则
        if code.startswith(('60', '68', '69')):  # 上海主板/科创板
            return True
        if code.startswith(('00', '30')):  # 深圳主板/创业板
            return True
        if code.startswith('8') or code.startswith('4'):  # 北交所/新三板
            return True
        
        return False
    
    def collect(self) -> Dict:
        """
        执行采集（主入口）
        
        策略：
        1. 首次运行：采集最近24小时数据
        2. 后续运行：采集前5分钟的数据
        
        Returns:
            采集结果统计
        """
        logger.info("=" * 50)
        logger.info("开始 A股消息采集")
        logger.info("=" * 50)
        
        start_time = time.time()
        
        # 获取数据库最新时间
        latest_time = self._get_latest_time()
        
        if latest_time:
            # 增量采集
            logger.info(f"数据库最新时间 {latest_time}，执行增量采集")
            articles = self.fetch_articles(limit=50)
            
            # 过滤：只保留新数据
            cutoff_time = latest_time - timedelta(minutes=1)  # 留1分钟重叠
            new_articles = [a for a in articles if a.publish_time > cutoff_time]
            logger.info(f"过滤后新文章: {len(new_articles)} 条")
        else:
            # 首次采集：获取最近24小时
            logger.info("数据库无数据，执行首次采集（最近24小时）")
            articles = self.fetch_articles(limit=200)
            
            # 过滤24小时内
            cutoff_time = datetime.now() - timedelta(hours=24)
            new_articles = [a for a in articles if a.publish_time > cutoff_time]
            logger.info(f"24小时内新文章: {len(new_articles)} 条")
        
        # 保存到数据库
        result = self.save_to_db(new_articles)
        
        elapsed = time.time() - start_time
        logger.info(f"采集完成: {result}, 耗时 {elapsed:.2f} 秒")
        
        return {
            'mode': 'incremental' if latest_time else 'full',
            'fetched': len(articles),
            'inserted': result['inserted'],
            'skipped': result['skipped'],
            'latest_time': latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else None,
            'elapsed_seconds': round(elapsed, 2),
        }
    
    def _get_latest_time(self) -> Optional[datetime]:
        """获取数据库最新文章时间"""
        try:
            with get_db_context() as db:
                # 动态导入避免循环依赖
                from app.models.messagesrc.cls_a_share import MessageSrcCLSAShare
                latest = db.query(MessageSrcCLSAShare).order_by(
                    MessageSrcCLSAShare.publish_time.desc()
                ).first()
                return latest.publish_time if latest else None
        except Exception as e:
            logger.warning(f"Get latest time failed: {e}")
            return None
    
    def save_to_db(self, articles: List[AShareArticle]) -> Dict:
        """
        保存文章到数据库
        
        Returns:
            {'inserted': int, 'skipped': int}
        """
        if not articles:
            return {'inserted': 0, 'skipped': 0}
        
        inserted = 0
        skipped = 0
        
        try:
            with get_db_context() as db:
                from app.models.messagesrc.cls_a_share import MessageSrcCLSAShare
                
                for article in articles:
                    # 检查是否已存在
                    existing = db.query(MessageSrcCLSAShare).filter(
                        MessageSrcCLSAShare.article_id == article.article_id
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # 创建记录
                    db_article = MessageSrcCLSAShare(
                        article_id=article.article_id,
                        title=article.title,
                        content=article.content,
                        summary=article.summary,
                        publish_time=article.publish_time,
                        stock_codes=article.stock_codes,
                        stock_names=article.stock_names,
                        source=article.source,
                        author=article.author,
                        reading_num=article.reading_num,
                        share_num=article.share_num,
                        image_url=article.image_url,
                    )
                    
                    db.add(db_article)
                    inserted += 1
                
                db.commit()
                logger.info(f"数据库保存完成: 新增 {inserted} 条, 跳过 {skipped} 条")
                
        except Exception as e:
            logger.error(f"Save to DB failed: {e}")
            raise
        
        return {'inserted': inserted, 'skipped': skipped}


def main():
    """测试采集器"""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    collector = CLSAShareCollector()
    
    # 测试获取文章
    print("\n测试获取文章列表...")
    articles = collector.fetch_articles(limit=10)
    print(f"获取到 {len(articles)} 条文章")
    
    for i, article in enumerate(articles[:3]):
        print(f"\n--- 文章 {i+1} ---")
        print(f"ID: {article.article_id}")
        print(f"标题: {article.title}")
        print(f"时间: {article.publish_time}")
        print(f"股票: {article.stock_codes}")
    
    # 测试完整采集流程
    print("\n\n测试完整采集流程...")
    result = collector.collect()
    print(f"\n采集结果:")
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
