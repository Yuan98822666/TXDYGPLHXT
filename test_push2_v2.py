import requests, json, time, random

ts = int(time.time()*1000)
cb = f'jQuery{random.randint(int(1e16),int(1e17))}_{ts}'

# Test without Accept-Encoding
print('=== Test 1: No Accept-Encoding ===')
url = f'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&cb={cb}&_={ts+1}'
Headers1 = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
}
try:
    resp = requests.get(url, headers=Headers1, timeout=10)
    print('Status:', resp.status_code)
    print('Response:', resp.text[:200])
except Exception as e:
    print('FAIL:', str(e)[:80])

# Test with minimal headers
print()
print('=== Test 2: Minimal headers ===')
ts = int(time.time()*1000)
cb = f'jQuery{random.randint(int(1e16),int(1e17))}_{ts}'
url = f'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&cb={cb}&_={ts+1}'
try:
    resp = requests.get(url, timeout=10)
    print('Status:', resp.status_code)
    print('Response:', resp.text[:200])
except Exception as e:
    print('FAIL:', str(e)[:80])

# Test with Chrome headers
print()
print('=== Test 3: Chrome headers ===')
ts = int(time.time()*1000)
cb = f'jQuery{random.randint(int(1e16),int(1e17))}_{ts}'
url = f'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&cb={cb}&_={ts+1}'
Headers3 = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}
try:
    resp = requests.get(url, headers=Headers3, timeout=10)
    print('Status:', resp.status_code)
    print('Response:', resp.text[:200])
except Exception as e:
    print('FAIL:', str(e)[:80])
