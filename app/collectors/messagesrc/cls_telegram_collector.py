#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报采集器
支持分类: zc政策/gs公司/hy行业/sc市场
"""

import requests
import json
import re
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TelegramMessage:
    """电报消息数据类"""
    msg_id: str
    publish_time: datetime
    content: str
    title: Optional[str] = None
    category: Optional[str] = None
    is_important: bool = False
    has_image: bool = False
    image_urls: Optional[str] = None  # 分号隔开
    image_ocr_text: Optional[str] = None  # 分号隔开
    source_url: Optional[str] = None


class CLSTelegramCollector:
    """财联社电报采集器"""
    
    BASE_URL = "https://www.cls.cn"
    API_URL = "https://www.cls.cn/v3/telegraph"
    
    # 分类映射
    CATEGORIES = {
        'zc': '政策',
        'gs': '公司', 
        'hy': '行业',
        'sc': '市场'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.cls.cn/telegraph',
            'Origin': 'https://www.cls.cn'
        })
    
    def _generate_sign(self, params: Dict) -> str:
        """生成API签名"""
        # 财联社签名算法需要逆向JS获取
        # 这里使用固定sign（从浏览器复制）或尝试通用算法
        # 实际使用时需要从页面JS中提取真实算法
        sorted_params = sorted(params.items())
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        return hashlib.md5(sign_str.encode()).hexdigest()
    
    def _parse_message(self, item: Dict) -> TelegramMessage:
        """解析单条电报消息"""
        # 提取时间
        pub_time = item.get('time', '')
        if pub_time:
            # 格式: "20:30:17" -> 补充日期
            today = datetime.now().strftime('%Y-%m-%d')
            pub_time = datetime.strptime(f"{today} {pub_time}", '%Y-%m-%d %H:%M:%S')
        else:
            pub_time = datetime.now()
        
        # 提取内容，解析标题
        content = item.get('content', '')
        title = None
        
        # 匹配【标题】格式
        title_match = re.search(r'【([^】]+)】', content)
        if title_match:
            title = title_match.group(1)
        
        # 提取图片
        images = item.get('images', [])
        image_urls = ';'.join(images) if images else None
        
        return TelegramMessage(
            msg_id=item.get('id', str(int(time.time() * 1000))),
            publish_time=pub_time,
            content=content,
            title=title,
            is_important=item.get('is_important', False),
            has_image=len(images) > 0,
            image_urls=image_urls,
            source_url=item.get('share_url')
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
        params = {
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '8.4.6',
        }
        
        # 添加分类参数
        if category and category in self.CATEGORIES:
            params['category'] = self.CATEGORIES[category]
        
        # 尝试获取真实数据
        try:
            # 方法1: 直接请求API（需要正确sign）
            response = self.session.get(self.API_URL, params=params, timeout=10)
            data = response.json()
            
            if data.get('errno') == 0:
                items = data.get('data', {}).get('roll_data', [])
                return [self._parse_message(item) for item in items[:limit]]
            
        except Exception as e:
            print(f"API请求失败: {e}")
        
        # 方法2: 使用页面渲染后的数据（需要Playwright/Selenium）
        # TODO: 实现浏览器渲染抓取
        
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
        all_msgs = self.fetch_telegrams(category, limit=100)
        return [m for m in all_msgs if m.publish_time > since]


def main():
    """测试采集器"""
    collector = CLSTelegramCollector()
    
    # 测试获取电报
    print("正在获取财联社电报...")
    messages = collector.fetch_telegrams(limit=10)
    
    for msg in messages:
        print(f"\n[{msg.publish_time.strftime('%H:%M:%S')}] {'【重要】' if msg.is_important else ''}")
        if msg.title:
            print(f"标题: {msg.title}")
        print(f"内容: {msg.content[:100]}...")
        if msg.has_image:
            print(f"图片: {msg.image_urls}")


if __name__ == '__main__':
    main()
