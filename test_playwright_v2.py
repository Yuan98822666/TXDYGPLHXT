import time, json
from playwright.sync_api import sync_playwright

print('=== Test 1: Edge headless ===')
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(
            headless=True,
            executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        )
        page = browser.new_page()
        page.goto('https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b', timeout=15000)
        print('Response:', page.content()[:300])
        browser.close()
    except Exception as e:
        print('Edge headless FAIL:', str(e)[:80])

print()
print('=== Test 2: Chrome headed (visible) ===')
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(
            headless=False,
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        )
        page = browser.new_page()
        page.goto('https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b', timeout=15000)
        page.wait_for_timeout(3000)
        print('Response:', page.content()[:500])
        browser.close()
    except Exception as e:
        print('Chrome headed FAIL:', str(e)[:80])

print()
print('=== Test 3: Direct API fetch via page context ===')
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(
            headless=True,
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        )
        page = browser.new_page()
        # 先访问东方财富建立上下文
        page.goto('https://quote.eastmoney.com/', timeout=15000)
        page.wait_for_timeout(2000)
        
        # 然后通过 fetch 获取数据
        result = page.evaluate('''
            fetch("https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b")
            .then(r => r.text())
            .then(d => d)
            .catch(e => "ERROR: " + e.message)
        ''')
        print('Fetch result:', result[:500] if result else 'None')
        browser.close()
    except Exception as e:
        print('Fetch FAIL:', str(e)[:80])
