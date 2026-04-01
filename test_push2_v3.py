import json, time, random

# Test with curl_cffi
print('=== Test: curl_cffi ===')
try:
    from curl_cffi import requests
    ts = int(time.time()*1000)
    cb = f'jQuery{random.randint(int(1e16),int(1e17))}_{ts}'
    url = f'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&cb={cb}&_={ts+1}'
    resp = requests.get(url, impersonate='chrome120', timeout=10)
    print('Status:', resp.status_code)
    print('Response:', resp.text[:300])
except Exception as e:
    print('curl_cffi FAIL:', str(e)[:80])
