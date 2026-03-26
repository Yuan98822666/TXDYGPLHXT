# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import json, re, sys

sys.stdout.reconfigure(encoding='utf-8')

with sync_playwright() as p:
    print("连接本地 Chrome (port 9222)...")
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    print("连接成功！")

    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.new_page()

    captured = {"text": None}

    def on_response(response):
        if "push2.eastmoney.com/api/qt/clist/get" in response.url and "bk0968" in response.url:
            try:
                captured["text"] = response.text()
                print(f"拦截到响应，长度: {len(captured['text'])}")
            except Exception as e:
                print(f"读取响应失败: {e}")

    page.on("response", on_response)

    url = (
        "https://push2.eastmoney.com/api/qt/clist/get"
        "?fid=f3&po=1&pz=20&np=1&fltt=1&invt=2&dect=1"
        "&fs=b:bk0968+f:!50&fields=f12"
        "&ut=8dec03ba335b81bf4ebdf7b29ec27d15"
        "&wbp2u=3951356261349626|0|1|0|web"
        "&cb=jQuery1&pn=1"
    )

    print("请求接口...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        print(f"goto 异常(忽略): {e}")

    page.wait_for_timeout(3000)

    if captured["text"]:
        print(f"响应前200字符: {captured['text'][:200]}")
        match = re.search(r'jQuery1\((.*)\);?$', captured["text"], re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            diff = data.get("data", {}).get("diff", {})
            items = diff if isinstance(diff, list) else list(diff.values())
            codes = [item.get("f12") for item in items if item.get("f12")]
            print(f"SUCCESS! 获取到 {len(codes)} 只成分股: {codes[:5]}")
    else:
        content = page.content()
        print(f"页面内容前300字符: {content[:300]}")

    page.close()
    browser.close()
