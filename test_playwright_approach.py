import time, json
from playwright.sync_api import sync_playwright

print('=== 方案: 通过浏览器访问股票页面获取实时数据 ===')

with sync_playwright() as p:
    # 使用 headed 模式，用户可以看到浏览器
    browser = p.chromium.launch(
        headless=False,  # 有头模式，可以看到浏览器
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        args=['--disable-blink-features=AutomationControlled']  # 隐藏自动化特征
    )
    page = browser.new_page()
    
    print('1. 访问东方财富股票页面...')
    page.goto('https://quote.eastmoney.com/a指数列表.html', timeout=60000)
    page.wait_for_timeout(5000)
    print('   页面标题:', page.title())
    
    print('2. 尝试获取页面中的实时数据...')
    # 尝试多种方式获取数据
    
    # 方式1: 获取表格内容
    try:
        rows = page.query_selector_all('table tr')
        print(f'   找到 {len(rows)} 行数据')
        if rows:
            # 获取表头
            headers = page.query_selector_all('table thead th')
            header_text = [h.inner_text() for h in headers[:10]]
            print('   表头:', header_text)
            # 获取前几行数据
            for row in rows[:3]:
                cells = row.query_selector_all('td')
                cell_text = [c.inner_text()[:20] for c in cells[:8]]
                print('   行:', cell_text)
    except Exception as e:
        print('   表格获取失败:', str(e)[:60])
    
    # 等待用户操作
    print()
    print('提示: 如果看到浏览器窗口，请在页面加载完成后关闭浏览器')
    print('或者让我继续尝试其他方法...')
    
    browser.close()

print()
print('=== 方案2: 通过请求头欺骗 ===')
# 尝试更完整的浏览器请求头
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
}

print('测试直接 HTTP 请求...')
try:
    resp = requests.get('https://quote.eastmoney.com/a指数列表.html', headers=headers, timeout=15)
    print(f'HTTP Status: {resp.status_code}')
    print(f'Response length: {len(resp.text)}')
    print('Content preview:', resp.text[:500])
except Exception as e:
    print('HTTP 请求失败:', str(e)[:80])
