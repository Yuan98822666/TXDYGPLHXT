#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财联社电报采集器 V2

特性：
- 从配置文件读取 token/uid 等参数
- 支持全量采集（24小时）和增量采集（前1分钟）
- 自动去重（基于 msg_id）
- 分类识别（政策/公司/行业/市场）

采集策略：
1. 首次采集：从数据库最新时间到当前（最多24小时）
2. 后续采集：每分钟采集前1分钟的数据
"""

import requests
import json
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from app.config.cls_config import get_telegram_params, TELEGRAM_URL
from app.db.session import get_db_context
from app.models.messagesrc.cls_telegram import MessageSrcCLSTelegram

import logging

logger = logging.getLogger(__name__)


@dataclass
class TelegramMessage:
    """电报消息数据类"""
    msg_id: str
    publish_time: datetime
    content: str
    title: Optional[str] = None
    category: Optional[str] = None  # zc/gs/hy/sc
    subjects: Optional[List[str]] = None
    is_important: bool = False
    has_image: bool = False
    image_urls: Optional[str] = None
    image_ocr_text: Optional[str] = None
    audio_urls: Optional[str] = None
    source_url: Optional[str] = None
    reading_num: int = 0
    share_num: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['publish_time'] = self.publish_time.strftime('%Y-%m-%d %H:%M:%S')
        return data


class CLSTelegramCollectorV2:
    """财联社电报采集器 V2"""
    
    # 分类映射（用于识别）
    CATEGORIES = {
        'zc': ['政策', '宏观', '监管', '央行', '国务院', '证监会', '财政部', '发改委'],
        'gs': ['公司', '公告', '业绩', 'A股公告速递', '个股'],
        'hy': ['行业', '产业', '汽车', '科技', '医药', '房地产', '新能源', '半导体'],
        'sc': ['市场', '环球市场', '期货', '美股', '港股', '大盘', '指数'],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0 Edg/120.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://www.cls.cn/telegraph',
            'Origin': 'https://www.cls.cn',
            'Connection': 'keep-alive',
        })
        self._init_session()
    
    def _init_session(self):
        """初始化session，获取cookies"""
        try:
            resp = self.session.get('https://www.cls.cn/telegraph', timeout=10)
            logger.info(f"Session init: status={resp.status_code}")
        except Exception as e:
            logger.warning(f"Session init warning: {e}")
    
    def _generate_sign(self, params: Dict[str, str]) -> str:
        """
        生成 sign 参数
        
        财联社 sign 生成规则（推测）：
        1. 将参数按 key 排序
        2. 拼接成 key=value&key=value 格式
        3. 加上固定盐值
        4. MD5 加密
        
        注意：实际 sign 可能需要从浏览器获取，这里提供基础实现
        """
        # 如果配置中有固定 sign，直接使用
        # 否则尝试动态生成（可能不准确）
        sorted_params = sorted(params.items())
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        # 添加盐值（需要根据实际情况调整）
        sign_str += "&salt=cls_api_salt"
        return hashlib.md5(sign_str.encode()).hexdigest()
    
    def _detect_category(self, subjects: List[str], content: str) -> Optional[str]:
        """根据分类标签和内容自动识别分类"""
        text_to_check = ' '.join(subjects) + ' ' + content[:100]
        
        for cat_code, keywords in self.CATEGORIES.items():
            for keyword in keywords:
                if keyword in text_to_check:
                    return cat_code
        
        return None
    
    def _parse_message(self, item: Dict) -> Optional[TelegramMessage]:
        """解析单条电报消息"""
        try:
            # 提取时间戳（ctime 是 Unix 时间戳）
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
        except Exception as e:
            logger.error(f"解析消息失败: {e}, item={item}")
            return None
    
    def fetch_telegrams(self, limit: int = 50) -> List[TelegramMessage]:
        """
        获取电报列表
        
        Args:
            limit: 获取数量（API默认返回20条）
        
        Returns:
            电报消息列表
        """
        # 从配置文件获取参数
        params = get_telegram_params()
        
        try:
            logger.info(f"Fetching from {TELEGRAM_URL} with params {params}")
            response = self.session.get(TELEGRAM_URL, params=params, timeout=10)
            logger.info(f"Response status: {response.status_code}")
            
            data = response.json()
            logger.info(f"Response errno: {data.get('errno')}")
            
            if data.get('errno') == 0:
                items = data.get('data', {}).get('roll_data', [])
                logger.info(f"Got {len(items)} items from API")
                
                messages = []
                for item in items:
                    msg = self._parse_message(item)
                    if msg:
                        messages.append(msg)
                
                return messages[:limit]
            else:
                logger.error(f"API Error: {data.get('msg', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    def get_db_latest_time(self) -> Optional[datetime]:
        """获取数据库中最新的电报时间"""
        try:
            with get_db_context() as db:
                latest = db.query(MessageSrcCLSTelegram).order_by(
                    MessageSrcCLSTelegram.publish_time.desc()
                ).first()
                if latest:
                    return latest.publish_time
        except Exception as e:
            logger.error(f"查询数据库最新时间失败: {e}")
        return None
    
    def get_messages_to_collect(self) -> Tuple[List[TelegramMessage], str]:
        """
        确定需要采集的消息范围
        
        Returns:
            (消息列表, 采集模式描述)
            采集模式: 'full' 全量(24h) / 'incremental' 增量(1min) / 'first_run' 首次
        """
        latest_time = self.get_db_latest_time()
        now = datetime.now()
        
        if latest_time is None:
            # 首次运行：采集最近24小时
            logger.info("首次运行，采集最近24小时数据")
            since = now - timedelta(hours=24)
            mode = 'first_run'
        elif (now - latest_time) > timedelta(hours=24):
            # 超过24小时：采集最近24小时
            logger.info(f"数据库最新时间 {latest_time} 超过24小时，采集最近24小时")
            since = now - timedelta(hours=24)
            mode = 'full'
        else:
            # 24小时内：采集前1分钟的数据
            logger.info(f"数据库最新时间 {latest_time}，采集增量数据（前1分钟）")
            since = latest_time - timedelta(minutes=1)
            mode = 'incremental'
        
        # 获取所有电报
        all_messages = self.fetch_telegrams(limit=200)
        
        # 过滤时间范围
        filtered = [m for m in all_messages if m.publish_time > since]
        
        logger.info(f"采集模式: {mode}, 时间范围: {since} ~ {now}, 获取 {len(filtered)} 条")
        return filtered, mode
    
    def save_to_db(self, messages: List[TelegramMessage]) -> Dict[str, int]:
        """
        保存消息到数据库
        
        Returns:
            {'inserted': 插入数, 'skipped': 跳过数}
        """
        if not messages:
            return {'inserted': 0, 'skipped': 0}
        
        inserted = 0
        skipped = 0
        
        try:
            with get_db_context() as db:
                for msg in messages:
                    # 检查是否已存在
                    existing = db.query(MessageSrcCLSTelegram).filter(
                        MessageSrcCLSTelegram.msg_id == msg.msg_id
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # 创建新记录
                    record = MessageSrcCLSTelegram(
                        msg_id=msg.msg_id,
                        publish_time=msg.publish_time,
                        content=msg.content,
                        title=msg.title,
                        category=msg.category,
                        subjects=msg.subjects,
                        is_important=msg.is_important,
                        has_image=msg.has_image,
                        image_urls=msg.image_urls,
                        audio_urls=msg.audio_urls,
                        source_url=msg.source_url,
                        reading_num=msg.reading_num,
                        share_num=msg.share_num,
                    )
                    db.add(record)
                    inserted += 1
                
                db.commit()
                logger.info(f"数据库保存完成: 插入 {inserted} 条, 跳过 {skipped} 条")
                
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
            import traceback
            traceback.print_exc()
        
        return {'inserted': inserted, 'skipped': skipped}
    
    def collect(self) -> Dict[str, any]:
        """
        执行采集（主入口）
        
        Returns:
            {
                'mode': 采集模式,
                'fetched': 获取数量,
                'inserted': 插入数量,
                'skipped': 跳过数量,
                'latest_time': 最新时间
            }
        """
        logger.info("=" * 50)
        logger.info("开始财联社电报采集")
        logger.info("=" * 50)
        
        start_time = time.time()
        
        # 1. 确定采集范围
        messages, mode = self.get_messages_to_collect()
        
        # 2. 保存到数据库
        result = self.save_to_db(messages)
        
        elapsed = time.time() - start_time
        
        # 获取最新时间
        latest_time = self.get_db_latest_time()
        
        summary = {
            'mode': mode,
            'fetched': len(messages),
            'inserted': result['inserted'],
            'skipped': result['skipped'],
            'latest_time': latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else None,
            'elapsed_seconds': round(elapsed, 2),
        }
        
        logger.info(f"采集完成: {summary}")
        return summary


# 兼容旧版接口
CLSTelegramCollector = CLSTelegramCollectorV2


if __name__ == "__main__":
    # 测试采集
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    collector = CLSTelegramCollectorV2()
    result = collector.collect()
    print("\n采集结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
