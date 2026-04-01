import time, json
from playwright.sync_api import sync_playwright

print('=== Test: Playwright 访问股票详情页 ===')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
    page = browser.new_page()
    
    # 先访问东方财富首页建立连接
    print('1. 访问东方财富首页...')
    try:
        page.goto('https://quote.eastmoney.com/sh600519.html', timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)  # 等待页面加载
        print('   首页加载成功')
    except Exception as e:
        print('   首页失败:', str(e)[:60])
    
    # 尝试通过 API 获取数据
    print('2. 访问 stock/get API...')
    api_url = 'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b'
    try:
        response = page.evaluate(f'''
            fetch("{api_url}").then(r => r.text()).then(d => {{ window.__api_data = d; }})
        ''')
        page.wait_for_timeout(2000)
        api_data = page.evaluate('window.__api_data')
        print('   API 数据:', api_data[:200] if api_data else 'None')
    except Exception as e:
        print('   API fetch 失败:', str(e)[:60])
    
    # 从页面 DOM 中提取数据
    print('3. 从页面提取数据...')
    try:
        # 尝试获取当前价格
        price = page.inner_text('span[data-id="f43"]')
        print('   价格:', price)
    except:
        pass
    
    # 获取页面 URL
    print('4. 当前页面:', page.url)
    
    browser.close()
    
print('Done!')
