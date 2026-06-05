#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片OCR识别工具
支持PaddleOCR、百度OCR、腾讯OCR等多种引擎
"""

import os
import io
import base64
from typing import List, Optional
from dataclasses import dataclass

import requests
from PIL import Image


@dataclass
class OCResult:
    """OCR识别结果"""
    text: str
    confidence: float
    bbox: Optional[List[List[int]]] = None


class ImageOCR:
    """图片OCR识别器"""
    
    def __init__(self, engine: str = 'paddle', **kwargs):
        """
        初始化OCR引擎
        
        Args:
            engine: OCR引擎类型 ('paddle', 'baidu', 'tencent', 'easyocr')
            **kwargs: 引擎特定配置
        """
        self.engine = engine
        self.config = kwargs
        self._ocr = None
        
    def _init_paddle(self):
        """初始化PaddleOCR"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    show_log=False,
                    **self.config
                )
            except ImportError:
                raise ImportError("PaddleOCR not installed. Run: pip install paddleocr")
        return self._ocr
    
    def _init_easyocr(self):
        """初始化EasyOCR"""
        if self._ocr is None:
            try:
                import easyocr
                self._ocr = easyocr.Reader(['ch_sim', 'en'], **self.config)
            except ImportError:
                raise ImportError("EasyOCR not installed. Run: pip install easyocr")
        return self._ocr
    
    def recognize_paddle(self, image_url: str) -> List[OCResult]:
        """使用PaddleOCR识别"""
        ocr = self._init_paddle()
        
        # 下载图片
        response = requests.get(image_url, timeout=10)
        image_bytes = response.content
        
        # 保存临时文件（PaddleOCR需要文件路径）
        temp_path = f'/tmp/ocr_temp_{hash(image_url)}.jpg'
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)
        
        try:
            result = ocr.ocr(temp_path, cls=True)
            
            results = []
            if result and result[0]:
                for line in result[0]:
                    bbox = line[0]
                    text = line[1][0]
                    confidence = line[1][1]
                    results.append(OCResult(text=text, confidence=confidence, bbox=bbox))
            
            return results
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def recognize_easyocr(self, image_url: str) -> List[OCResult]:
        """使用EasyOCR识别"""
        reader = self._init_easyocr()
        
        # 下载图片
        response = requests.get(image_url, timeout=10)
        image = Image.open(io.BytesIO(response.content))
        
        # 识别
        result = reader.readtext(image)
        
        results = []
        for detection in result:
            bbox = detection[0]
            text = detection[1]
            confidence = detection[2]
            results.append(OCResult(text=text, confidence=confidence, bbox=bbox))
        
        return results
    
    def recognize(self, image_url: str) -> str:
        """
        识别图片中的文字
        
        Args:
            image_url: 图片URL
        
        Returns:
            识别出的文字，多个段落用空格分隔
        """
        if self.engine == 'paddle':
            results = self.recognize_paddle(image_url)
        elif self.engine == 'easyocr':
            results = self.recognize_easyocr(image_url)
        else:
            raise ValueError(f"Unsupported engine: {self.engine}")
        
        # 合并识别结果
        texts = [r.text for r in results if r.confidence > 0.5]
        return ' '.join(texts)
    
    def recognize_multiple(self, image_urls: List[str]) -> str:
        """
        识别多张图片
        
        Args:
            image_urls: 图片URL列表
        
        Returns:
            识别结果，用分号隔开
        """
        results = []
        for url in image_urls:
            try:
                text = self.recognize(url)
                if text.strip():
                    results.append(text)
            except Exception as e:
                print(f"OCR failed for {url}: {e}")
                results.append("")
        
        return ';'.join(results)


def main():
    """测试OCR"""
    # 测试图片
    test_url = "https://example.com/test.jpg"
    
    ocr = ImageOCR(engine='paddle')
    try:
        text = ocr.recognize(test_url)
        print(f"识别结果: {text}")
    except Exception as e:
        print(f"识别失败: {e}")


if __name__ == '__main__':
    main()
