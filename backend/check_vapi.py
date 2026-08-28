import requests
import json

API_KEY = "79b1fc90-5245-4007-8f14-7ee86de5d03f"
ASSISTANT_ID = "e6f879b5-b9e5-403a-831a-64500dda7057"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    assistant = response.json()
    tools = assistant.get("model", {}).get("tools", [])
    print(f"Total tools in assistant model: {len(tools)}")
    for t in tools:
        if t.get("type") == "function":
            print(f"- {t.get('function', {}).get('name')}")
else:
    print(f"Failed to fetch: {response.text}")
