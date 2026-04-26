import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    
    data = response.json()
    if "models" in data:
        print("Available Models:")
        for m in data["models"]:
            print(f"- {m['name']}")
    else:
        print(f"Error Response: {data}")
except Exception as e:
    print(f"Request failed: {e}")
