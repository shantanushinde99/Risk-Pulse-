import requests
import json
url = 'https://risk-pulse.onrender.com/api/scenarios/safe/run'
try:
    response = requests.post(url, timeout=15)
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception as e:
    print('Failed:', e)
