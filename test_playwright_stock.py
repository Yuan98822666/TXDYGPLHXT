import time, json
from playwright.sync_api import sync_playwright

print('=== Test: Playwright 访问 stock/get ===')

url = 'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b'

with sync_playwright() as p:
    # 使用系统已安装的 Chrome
    browser = p.chromium.launch(
        headless=True,
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
    page = browser.new_page()
    
    print('Navigating to stock/get API...')
    try:
        response = page.goto(url, timeout=30000, wait_until='networkidle')
        print('Response status:', response.status if response else 'None')
        print('Response length:', len(page.content()))
        
        # 获取页面内容
        content = page.content()
        print('Content preview:', content[:500])
    except Exception as e:
        print('Navigation error:', str(e)[:100])
        
        # 尝试直接获取文本
        try:
            text = page.inner_text('body')
            print('Body text:', text[:500])
        except:
            pass
    
    browser.close()
    
print('Done!')
