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
    
    def _generate_sign(self, params: Dict) -> str:
        """
        生成API签名
        财联社的sign算法需要从页面JS中提取
        目前使用固定值（需要定期从浏览器更新）
        """
        # TODO: 实现真实的sign算法
        # 临时返回空，让API返回错误提示
        return ''
    
    def _parse_message(self, item: Dict) -> TelegramMessage:
        """解析单条电报消息"""
        # 提取时间
        pub_time_str = item.get('time', '')
        if pub_time_str:
            # 格式: "20:30:17" -> 补充日期
            today = datetime.now().strftime('%Y-%m-%d')
            try:
                pub_time = datetime.strptime(f"{today} {pub_time_str}", '%Y-%m-%d %H:%M:%S')
            except:
                pub_time = datetime.now()
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
            msg_id=str(item.get('id', int(time.time() * 1000))),
            publish_time=pub_time,
            content=content,
            title=title,
            is_important=item.get('is_important', False) or item.get('is_red', False),
            has_image=len(images) > 0,
            image_urls=image_urls,
            source_url=item.get('share_url', item.get('url'))
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
        
        try:
            response = self.session.get(self.API_URL, params=params, timeout=10)
            data = response.json()
            
            if data.get('errno') == 0:
                items = data.get('data', {}).get('roll_data', [])
                return [self._parse_message(item) for item in items[:limit]]
            else:
                # API返回错误，可能需要更新sign
                print(f"API Error: {data.get('msg', 'Unknown error')}")
                
        except Exception as e:
            print(f"Request failed: {e}")
        
        return []
    
    def fetch_with_browser(self, category: str = None, limit: int = 50) -> List[TelegramMessage]:
        """
        使用浏览器渲染获取数据（当API不可用时）
        需要安装playwright: pip install playwright && playwright install
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # 访问电报页面
                url = f'{self.BASE_URL}/telegraph'
                if category:
                    url += f'?category={self.CATEGORIES.get(category, "")}'
                
                page.goto(url, wait_until='networkidle')
                
                # 等待数据加载
                page.wait_for_selector('.telegraph-list, .roll-item, [class*="telegraph"]', timeout=10000)
                
                # 提取数据
                items = page.evaluate('''() => {
                    const items = [];
                    // 尝试多种可能的选择器
                    const selectors = [
                        '.telegraph-list .item',
                        '.roll-item',
                        '[class*="telegraph"] [class*="item"]',
                        '.content-item'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            elements.forEach(el => {
                                const timeEl = el.querySelector('.time, [class*="time"]');
                                const contentEl = el.querySelector('.content, [class*="content"]');
                                
                                if (contentEl) {
                                    items.push({
                                        time: timeEl ? timeEl.textContent.trim() : '',
                                        content: contentEl.textContent.trim(),
                                        html: contentEl.innerHTML
                                    });
                                }
                            });
                            break;
                        }
                    }
                    return items;
                }''')
                
                browser.close()
                
                # 解析提取的数据
                messages = []
                for item in items[:limit]:
                    msg = self._parse_message({
                        'id': int(time.time() * 1000),
                        'time': item.get('time'),
                        'content': item.get('content'),
                    })
                    messages.append(msg)
                
                return messages
                
        except ImportError:
            print("Playwright not installed. Run: pip install playwright && playwright install")
            return []
        except Exception as e:
            print(f"Browser fetch failed: {e}")
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
        if not all_msgs:
            # 尝试浏览器方式
            all_msgs = self.fetch_with_browser(category, limit=100)
        return [m for m in all_msgs if m.publish_time > since]


def main():
    """测试采集器"""
    collector = CLSTelegramCollector()
    
    # 测试获取电报
    print("正在获取财联社电报...")
    messages = collector.fetch_telegrams(limit=10)
    
    if not messages:
        print("API方式失败，尝试浏览器方式...")
        messages = collector.fetch_with_browser(limit=10)
    
    for msg in messages:
        print(f"\n[{msg.publish_time.strftime('%H:%M:%S')}] {'【重要】' if msg.is_important else ''}")
        if msg.title:
            print(f"标题: {msg.title}")
        print(f"内容: {msg.content[:100]}...")
        if msg.has_image:
            print(f"图片: {msg.image_urls}")


if __name__ == '__main__':
    main()
