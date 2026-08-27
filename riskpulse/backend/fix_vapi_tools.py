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
    
    # Remove the 'messages' array from all tools (specifically the empty request-complete message that might crash TTS)
    for t in tools:
        if "messages" in t:
            del t["messages"]
            
    model_obj["tools"] = tools
    
    payload = {
        "model": model_obj
    }
    
    print("Patching assistant to remove empty tool messages...")
    patch_res = requests.patch(url, headers=headers, json=payload)
    if patch_res.status_code == 200:
        print("Success!")
    else:
        print(patch_res.text)
else:
    print(f"Failed to fetch: {response.text}")
