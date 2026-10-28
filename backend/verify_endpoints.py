import urllib.request
import json

endpoints = [
    '/api/health',
    '/api/dashboard',
    '/api/disruptions',
    '/api/shipments',
    '/api/inventory',
    '/api/recovery-plans',
    '/api/audit-events'
]

print("=== VERIFYING API ENDPOINTS ===")
for ep in endpoints:
    url = f"http://127.0.0.1:5000{ep}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"PASS: {ep} -> HTTP {resp.status}, status={data.get('status')}")
    except Exception as e:
        print(f"FAIL: {ep} -> {e}")
