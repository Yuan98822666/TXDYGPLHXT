import requests, json, time, random

ts = int(time.time()*1000)
cb = f'jQuery{random.randint(int(1e16),int(1e17))}_{ts}'

Headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
}

# Test clist/get
url1 = f'https://push2.eastmoney.com/api/qt/clist/get?np=1&fltt=1&invt=2&cb={cb}&fs=m:90+t:3+f:!50&fields=f12,f13,f14,f1,f2,f3&fid=f3&pn=1&pz=3&po=1&ut=fa5fd1943c7b386f172d6893dbfba10b&_={ts+1}'

print('=== clist/get ===')
try:
    resp = requests.get(url1, headers=Headers, timeout=10)
    text = resp.text.strip()
    json_str = text.split(cb+'(', 1)[1].rsplit(')', 1)[0]
    d = json.loads(json_str)
    diff = d.get('data', {}).get('diff', [])
    print('OK! count:', len(diff))
    for item in diff[:3]:
        print('  code:', item.get('f12'), 'name:', item.get('f14'), 'f2=', item.get('f2'), 'f3=', item.get('f3'))
except Exception as e:
    print('FAIL:', str(e)[:80])

# Test stock/get
print()
print('=== stock/get ===')
ts = int(time.time()*1000)
cb = f'jQuery{random.randint(int(1e16),int(1e17))}_{ts}'
url2 = f'https://push2.eastmoney.com/api/qt/stock/get?secid=1.600519&fields=f43,f170&ut=fa5fd1943c7b386f172d6893dbfba10b&cb={cb}&_={ts+1}'
try:
    resp = requests.get(url2, headers=Headers, timeout=10)
    print('Status:', resp.status_code)
    if resp.status_code == 200:
        print('Response:', resp.text[:300])
except Exception as e:
    print('FAIL:', str(e)[:80])
