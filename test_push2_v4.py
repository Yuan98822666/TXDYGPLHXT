import json, time, random
from curl_cffi import requests as curl_requests

print('=== Test: curl_cffi Session + stock/get ===')
try:
    # 创建 Session（和 get_jsonp 一样）
    session = curl_requests.Session(impersonate='chrome120')
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
    })
    
    ts = int(time.time() * 1000)
    cb = f'jQuery{ts}'
    params = {
        "secid": "1.600519",
        "fields": "f43,f170",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "cb": cb,
        "_": ts + 1,
    }
    
    resp = session.get('https://push2.eastmoney.com/api/qt/stock/get', params=params, timeout=10)
    print('Status:', resp.status_code)
    print('Response:', resp.text[:300])
    
except Exception as e:
    print('FAIL:', str(e))
