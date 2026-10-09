import os
import json
import urllib.request
from dotenv import load_dotenv

# Load your backend .env file
load_dotenv("d:/Major Hackethon Projects/Moss Hackethon/backend/.env")

api_key = os.getenv("LLM_API_KEY")
print(f"Testing Mistral API with key: {api_key[:5]}...{api_key[-4:] if api_key else 'None'}")

if not api_key:
    print("Error: LLM_API_KEY is not set.")
    exit(1)

url = "https://api.mistral.ai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "model": "mistral-small-latest",
    "messages": [{"role": "user", "content": "Say 'hello world' in 2 words."}]
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Status Code: {response.status}")
        response_data = json.loads(response.read().decode('utf-8'))
        print("Response:", response_data["choices"][0]["message"]["content"])
        print("\n✅ Mistral API is WORKING perfectly!")
except urllib.error.HTTPError as e:
    print(f"Status Code: {e.code}")
    if e.code == 429:
        print("Error: 429 Rate Limit Exceeded. You have hit the rate limit or run out of credits.")
    elif e.code == 401:
        print("Error: 401 Unauthorized. The API key is invalid.")
    else:
        print(f"Error: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Request failed: {e}")
