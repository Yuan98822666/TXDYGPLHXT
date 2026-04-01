import time, json, subprocess

print('=== 方案: 连接到已有 Chrome 浏览器 ===')

# 方法1: 尝试 WebSocket CDP 连接
# Chrome 启动时加 --remote-debugging-port=9222 就可以连接

# 先检查 Chrome 是否以调试模式运行
print('1. 检查 Chrome 调试端口...')
import requests

try:
    resp = requests.get('http://localhost:9222/json/version', timeout=5)
    print('   Chrome 调试端口开放!')
    print('   版本信息:', resp.json())
except:
    print('   Chrome 调试端口未开放')
    print('   请手动启动 Chrome: chrome.exe --remote-debugging-port=9222')

# 方法2: 启动带调试端口的 Chrome
print()
print('2. 启动带调试端口的 Chrome...')
try:
    subprocess.Popen([
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        '--remote-debugging-port=9222',
        '--user-data-dir=C:/Users/Yuan9/AppData/Local/Google/Chrome/User Data/Default',
        'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43'
    ])
    print('   Chrome 已启动，请检查窗口')
except Exception as e:
    print('   启动失败:', str(e)[:60])

# 方法3: 尝试 Playwright CDP 连接
print()
print('3. 尝试 Playwright CDP 连接...')
try:
    from playwright.sync_api import sync_playwright
    
    # 尝试连接到 Chrome
    with sync_playwright() as p:
        # 连接到已有的 Chrome 实例
        browser = p.chromium.connect_over_cdp('ws://localhost:9222')
        print('   CDP 连接成功!')
        
        contexts = browser.contexts
        print(f'   找到 {len(contexts)} 个浏览器上下文')
        
        if contexts:
            page = contexts[0].new_page()
            try:
                response = page.goto('https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43', timeout=30000)
                print('   响应状态:', response.status if response else 'None')
                print('   内容:', page.content()[:300])
            except Exception as e:
                print('   访问失败:', str(e)[:80])
        
        browser.close()
except ImportError:
    print('   Playwright CDP 功能不可用')
except Exception as e:
    print('   CDP 连接失败:', str(e)[:80])
