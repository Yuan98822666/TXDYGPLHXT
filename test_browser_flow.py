import time, json
from playwright.sync_api import sync_playwright

print('=== 方案: 模拟浏览器完整访问流程 ===')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # 有头模式，可以看到浏览器
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
    page = browser.new_page()
    
    # 设置视口大小（模拟真实浏览器）
    page.set_viewport_size({"width": 1920, "height": 1080})
    
    print('1. 访问东方财富首页...')
    try:
        page.goto('https://quote.eastmoney.com/', timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(5000)
        print('   首页加载成功, URL:', page.url)
    except Exception as e:
        print('   首页加载失败:', str(e)[:80])
        print('   继续尝试...')
    
    print('2. 尝试访问股票详情页...')
    try:
        page.goto('https://quote.eastmoney.com/sh600519.html', timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(5000)
        print('   详情页加载成功')
    except Exception as e:
        print('   详情页加载失败:', str(e)[:80])
    
    print('3. 尝试通过 fetch API 获取数据...')
    # 先建立连接，然后尝试 fetch
    result = page.evaluate('''
        async () => {
            try {
                // 先获取页面上的某个元素
                const title = document.title;
                
                // 尝试 fetch
                const resp = await fetch('https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b');
                const text = await resp.text();
                return {status: resp.status, data: text.substring(0, 200)};
            } catch (e) {
                return {error: e.message};
            }
        }
    ''')
    print('   Fetch 结果:', result)
    
    print('4. 尝试通过 JSONP 方式获取...')
    jsonp_result = page.evaluate('''
        () => {
            return new Promise((resolve) => {
                const callback = 'jQuery' + Date.now();
                const script = document.createElement('script');
                script.src = `https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&cb=${callback}`;
                window[callback] = (data) => {
                    resolve(data);
                    delete window[callback];
                    document.head.removeChild(script);
                };
                script.onerror = () => {
                    resolve({error: 'script load failed'});
                    delete window[callback];
                    if (document.head.contains(script)) document.head.removeChild(script);
                };
                document.head.appendChild(script);
                setTimeout(() => resolve({error: 'timeout'}), 10000);
            });
        }
    ''')
    print('   JSONP 结果:', str(jsonp_result)[:300])
    
    browser.close()

print()
print('=== 方案2: 直接获取页面数据 ===')
import requests

# 检查 requests 是否能获取东方财富页面
print('测试 requests 获取东方财富页面...')
try:
    resp = requests.get('https://quote.eastmoney.com/', timeout=15)
    print(f'HTTP Status: {resp.status_code}')
    print(f'Response length: {len(resp.text)}')
    # 尝试从页面提取股票数据
    if '600519' in resp.text or '贵州茅台' in resp.text:
        print('找到股票数据!')
except Exception as e:
    print('失败:', str(e)[:80])
