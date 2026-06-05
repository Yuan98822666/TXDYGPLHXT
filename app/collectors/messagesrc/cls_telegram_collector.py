#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报采集器
支持分类: zc政策/gs公司/hy行业/sc市场

API端点: https://www.cls.cn/api/cache?name=telegraph
"""

import requests
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class TelegramMessage:
    """电报消息数据类"""
    msg_id: str
    publish_time: datetime
    content: str
    title: Optional[str] = None
    category: Optional[str] = None  # zc/gs/hy/sc
    subjects: Optional[List[str]] = None  # 原始分类列表
    is_important: bool = False
    has_image: bool = False
    image_urls: Optional[str] = None  # 分号隔开
    image_ocr_text: Optional[str] = None  # 分号隔开
    audio_urls: Optional[str] = None  # 分号隔开
    source_url: Optional[str] = None
    reading_num: int = 0
    share_num: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['publish_time'] = self.publish_time.strftime('%Y-%m-%d %H:%M:%S')
        return data


class CLSTelegramCollector:
    """财联社电报采集器"""
    
    BASE_URL = "https://www.cls.cn"
    API_URL = "https://www.cls.cn/api/cache"
    
    # 分类映射（用于识别）
    CATEGORIES = {
        'zc': ['政策', '宏观', '监管', '央行', '国务院', '证监会'],
        'gs': ['公司', '公告', '业绩', 'A股公告速递'],
        'hy': ['行业', '产业', '汽车', '科技', '医药', '房地产'],
        'sc': ['市场', '环球市场', '期货', '美股', '港股'],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0 Edg/120.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.cls.cn/telegraph',
            'Origin': 'https://www.cls.cn',
            'Connection': 'keep-alive',
        })
        # 访问主页获取必要的cookies
        self._init_session()
    
    def _init_session(self):
        """初始化session，获取cookies"""
        try:
            self.session.get(f'{self.BASE_URL}/telegraph', timeout=10)
        except:
            pass
    
    def _detect_category(self, subjects: List[str], content: str) -> Optional[str]:
        """
        根据分类标签和内容自动识别分类
        
        Args:
            subjects: 原始分类列表
            content: 内容文本
        
        Returns:
            分类代码 zc/gs/hy/sc 或 None
        """
        text_to_check = ' '.join(subjects) + ' ' + content[:100]
        
        for cat_code, keywords in self.CATEGORIES.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return cat_code
        
        return None
    
    def _parse_message(self, item: Dict) -> TelegramMessage:
        """解析单条电报消息"""
        # 提取时间戳
        ctime = item.get('ctime')
        if ctime:
            pub_time = datetime.fromtimestamp(ctime)
        else:
            pub_time = datetime.now()
        
        # 提取内容
        content = item.get('content', '')
        title = item.get('title', '')
        
        # 如果title为空，尝试从content中提取【标题】
        if not title:
            title_match = re.search(r'【([^】]+)】', content)
            if title_match:
                title = title_match.group(1)
        
        # 提取图片
        images = item.get('images')
        image_urls = None
        has_image = False
        if images and isinstance(images, list) and len(images) > 0:
            image_urls = ';'.join(images)
            has_image = True
        
        # 提取音频
        audio_urls_list = item.get('audio_url', [])
        audio_urls = ';'.join(audio_urls_list) if audio_urls_list else None
        
        # 提取分类
        subjects_data = item.get('subjects', [])
        subjects = [s.get('subject_name', '') for s in subjects_data] if subjects_data else []
        
        # 自动识别分类
        category = self._detect_category(subjects, content)
        
        # 判断是否重要（根据level或is_top）
        level = item.get('level', 'C')
        is_important = item.get('is_top', 0) == 1 or level in ['A', 'S']
        
        # 构建source_url
        msg_id = str(item.get('id', ''))
        source_url = f"https://www.cls.cn/detail/{msg_id}" if msg_id else None
        
        return TelegramMessage(
            msg_id=msg_id,
            publish_time=pub_time,
            content=content,
            title=title if title else None,
            category=category,
            subjects=subjects if subjects else None,
            is_important=is_important,
            has_image=has_image,
            image_urls=image_urls,
            audio_urls=audio_urls,
            source_url=source_url,
            reading_num=item.get('reading_num', 0),
            share_num=item.get('share_num', 0),
        )
    
    def fetch_telegrams(self, category: str = None, limit: int = 50) -> List[TelegramMessage]:
        """
        获取电报列表
        
        Args:
            category: 分类代码 zc/gs/hy/sc
            limit: 获取数量
        
        Returns:
            电报消息列表
        """
        params = {'name': 'telegraph'}
        
        try:
            response = self.session.get(self.API_URL, params=params, timeout=10)
            data = response.json()
            
            if data.get('errno') == 0:
                items = data.get('data', {}).get('roll_data', [])
                messages = [self._parse_message(item) for item in items]
                
                # 按分类过滤
                if category:
                    messages = [m for m in messages if m.category == category]
                
                return messages[:limit]
            else:
                print(f"API Error: {data.get('msg', 'Unknown error')}")
                
        except Exception as e:
            print(f"Request failed: {e}")
        
        return []
    
    def discover_new(self, since: datetime, category: str = None) -> List[TelegramMessage]:
        """
        发现新消息
        
        Args:
            since: 从此时间之后的消息
            category: 分类过滤
        
        Returns:
            新消息列表
        """
        all_msgs = self.fetch_telegrams(category, limit=200)
        return [m for m in all_msgs if m.publish_time > since]
    
    def save_to_db(self, messages: List[TelegramMessage], db_connection=None):
        """
        保存消息到数据库
        
        Args:
            messages: 消息列表
            db_connection: 数据库连接（可选）
        """
        # TODO: 实现数据库保存逻辑
        # 需要导入SQLAlchemy或其他ORM
        pass


def main():
    """测试采集器"""
    collector = CLSTelegramCollector()
    
    # 测试获取电报
    print("正在获取财联社电报...\n")
    messages = collector.fetch_telegrams(limit=10)
    
    for msg in messages:
        print(f"[{msg.publish_time.strftime('%H:%M:%S')}] {'【重要】' if msg.is_important else ''}")
        if msg.title:
            print(f"标题: {msg.title}")
        print(f"内容: {msg.content[:100]}...")
        if msg.category:
            print(f"分类: {msg.category}")
        if msg.subjects:
            print(f"标签: {msg.subjects}")
        if msg.has_image:
            print(f"图片: {msg.image_urls}")
        print(f"阅读: {msg.reading_num}  分享: {msg.share_num}")
        print('-' * 50)


if __name__ == '__main__':
    main()
