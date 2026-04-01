import time, json, os
from playwright.sync_api import sync_playwright

# 浏览器配置文件目录
BROWSER_PROFILE_DIR = r"E:\Python Project\TXDYGPLHXT\browser_profile"

print('=== 方案: 使用持久化浏览器配置 ===')
print(f'浏览器配置目录: {BROWSER_PROFILE_DIR}')

with sync_playwright() as p:
    # 创建持久化上下文（保存 cookies 和 session）
    print('1. 创建/加载浏览器上下文...')
    
    if not os.path.exists(BROWSER_PROFILE_DIR):
        os.makedirs(BROWSER_PROFILE_DIR)
        print('   新建配置目录')
    
    # 第一次运行时会打开浏览器让你登录
    # 之后会自动使用保存的 session
    context = p.chromium.launch_persistent_context(
        user_data_dir=BROWSER_PROFILE_DIR,
        headless=False,  # 需要看到浏览器来验证
        executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        viewport={"width": 1920, "height": 1080},
        args=['--disable-blink-features=AutomationControlled']
    )
    
    page = context.new_page()
    
    print('2. 访问东方财富首页...')
    try:
        page.goto('https://quote.eastmoney.com/', timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(5000)
        print('   首页加载成功!')
    except Exception as e:
        print('   首页加载失败:', str(e)[:80])
    
    print('3. 尝试访问 stock/get API...')
    try:
        response = page.goto('https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b', timeout=30000)
        print('   响应状态:', response.status if response else 'None')
        content = page.content()
        print('   内容:', content[:500])
    except Exception as e:
        print('   访问失败:', str(e)[:80])
    
    # 保存 cookies
    print('4. 保存浏览器上下文...')
    cookies = context.cookies()
    with open(r'E:\Python Project\TXDYGPLHXT\browser_cookies.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f'   已保存 {len(cookies)} 个 cookies')
    
    # 关闭浏览器
    context.close()

print()
print('=== 下次运行时加载保存的 cookies ===')
