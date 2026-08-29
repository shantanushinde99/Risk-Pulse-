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
    model_obj = assistant.get("model", {})
    tools = model_obj.get("tools", [])
    
    # Remove the hardcoded 'server' object so it uses the global URL!
    for t in tools:
        if "server" in t:
            del t["server"]
            
    model_obj["tools"] = tools
    
    payload = {
        "model": model_obj,
        "serverUrl": "https://risk-pulse.onrender.com/api/vapi/webhook"
    }
    
    print("Patching assistant to use Render URL...")
    patch_res = requests.patch(url, headers=headers, json=payload)
    if patch_res.status_code == 200:
        print("Success! Assistant and all tools are now pointing to https://risk-pulse.onrender.com/api/vapi/webhook")
    else:
        print(patch_res.text)
else:
    print(f"Failed to fetch: {response.text}")
