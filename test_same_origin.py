import time, json
from playwright.sync_api import sync_playwright

print('=== 方案: 同源访问 push2 API ===')

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    )
    page = browser.new_page()
    
    print('1. 访问东方财富首页...')
    page.goto('https://quote.eastmoney.com/', timeout=60000, wait_until='domcontentloaded')
    page.wait_for_timeout(5000)
    print('   首页加载成功, URL:', page.url)
    
    print('2. 尝试在同源上下文访问 push2 API...')
    # 东方财富可能在 push2 子域有安全设置
    # 让我们先检查当前页面的 CSP
    
    csp = page.evaluate('''() => {
        return {
            url: window.location.href,
            origin: window.location.origin,
            CSP: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content || 'none'
        };
    }''')
    print('   当前上下文:', csp)
    
    print('3. 尝试访问 push2 首页...')
    try:
        page.goto('https://push2.eastmoney.com/', timeout=30000, wait_until='domcontentloaded')
        print('   push2 首页加载成功! URL:', page.url)
        print('   页面标题:', page.title())
    except Exception as e:
        print('   push2 首页加载失败:', str(e)[:60])
    
    print('4. 尝试 iframe 方式...')
    # 尝试创建一个指向东方财富页面的 iframe
    try:
        iframe_result = page.evaluate('''async () => {
            return new Promise((resolve) => {
                const iframe = document.createElement('iframe');
                iframe.src = 'https://quote.eastmoney.com/sh600519.html';
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
                
                iframe.onload = () => {
                    try {
                        // 尝试从 iframe 获取数据
                        const iframeWindow = iframe.contentWindow;
                        const doc = iframe.contentDocument;
                        resolve({
                            success: true,
                            url: iframeWindow.location.href,
                            hasData: !!doc.querySelector('#price9, .current-price, [class*="price"]')
                        });
                    } catch (e) {
                        resolve({success: false, error: e.message});
                    }
                    document.body.removeChild(iframe);
                };
                iframe.onerror = () => resolve({success: false, error: 'iframe load failed'});
                setTimeout(() => resolve({error: 'timeout'}), 15000);
            });
        }''')
        print('   iframe 结果:', iframe_result)
    except Exception as e:
        print('   iframe 失败:', str(e)[:60])
    
    browser.close()

print()
print('=== 方案2: 使用 cookie 和完整浏览器上下文 ===')
import requests

# 尝试使用完整浏览器请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

print('测试1: 首页')
try:
    resp = requests.get('https://quote.eastmoney.com/', headers=headers, timeout=15)
    print(f'  Status: {resp.status_code}, Length: {len(resp.text)}')
except Exception as e:
    print(f'  失败: {str(e)[:60]}')

print('测试2: 股票详情页')
try:
    resp = requests.get('https://quote.eastmoney.com/sh600519.html', headers=headers, timeout=15)
    print(f'  Status: {resp.status_code}, Length: {len(resp.text)}')
    # 尝试提取价格数据
    if '600519' in resp.text or '贵州茅台' in resp.text:
        print('  找到股票数据!')
except Exception as e:
    print(f'  失败: {str(e)[:60]}')

print('测试3: push2 API')
try:
    resp = requests.get('https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43', headers=headers, timeout=15)
    print(f'  Status: {resp.status_code}, Length: {len(resp.text)}')
except Exception as e:
    print(f'  失败: {str(e)[:60]}')
