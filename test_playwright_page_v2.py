import time, json
from playwright.sync_api import sync_playwright

print('=== Test: 从股票页面提取数据 ===')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
    page = browser.new_page()
    
    # 访问股票详情页
    print('1. 访问股票详情页...')
    try:
        page.goto('https://quote.eastmoney.com/sh600519.html', timeout=30000, wait_until='networkidle')
        page.wait_for_timeout(3000)
        print('   页面加载成功')
        print('   URL:', page.url)
    except Exception as e:
        print('   页面加载失败:', str(e)[:80])
        browser.close()
        exit(1)
    
    # 尝试从页面 DOM 获取数据
    print('2. 从 DOM 提取数据...')
    
    # 方法1: 通过 JavaScript 获取东方财富页面上的数据
    data = page.evaluate('''
        () => {
            // 尝试获取东方财富的数据
            const em = window.eastmoney || {};
            const quote = window.quote || {};
            
            // 尝试从全局变量获取
            const globalData = {
                price: document.querySelector('#price9')?.innerText,
                name: document.querySelector('.stockName')?.innerText,
                code: document.querySelector('#code')?.innerText,
                // 尝试其他选择器
                price2: document.querySelector('[data-v-1f34b1d4]')?.innerText,
            };
            
            return JSON.stringify(globalData);
        }
    ''')
    print('   全局数据:', data[:300])
    
    # 方法2: 尝试获取页面上的价格元素
    print('3. 查找价格元素...')
    selectors = [
        '#price9',
        '.stock-price',
        '.current-price',
        '[class*="price"]',
        'span[data-id]',
    ]
    for sel in selectors:
        try:
            elements = page.query_selector_all(sel)
            if elements:
                print(f'   {sel}: found {len(elements)} elements')
                for el in elements[:3]:
                    text = el.inner_text()
                    if text:
                        print(f'      - {text[:50]}')
        except:
            pass
    
    # 方法3: 获取完整的 body 文本
    print('4. 页面文本内容（前500字符）:')
    try:
        body = page.inner_text('body')
        print(body[:500])
    except Exception as e:
        print('   失败:', str(e)[:80])
    
    browser.close()

print()
print('Done!')
