"""
This script lists all available models from the LLM provider's API. 
It reads the base URL and API key from the .env file, makes a GET request to the /models endpoint, and prints the list of models to the console. This is useful for verifying that your API credentials are correct and for seeing which models you can use in your application.

Created on: 20-05-2026
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")

if not LLM_BASE_URL or not LLM_API_KEY:
    print("LLM_BASE_URL and LLM_API_KEY must be set in your .env file.")
    exit(1)

url = LLM_BASE_URL.rstrip("/") + "/models"
headers = {
    "Authorization": f"Bearer {LLM_API_KEY}",
    "Content-Type": "application/json"
}

try:
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    print("Full API response:", data)
    print()
    models = data.get("data") or data.get("models")
    if not models:
        print("No models found or unexpected response format.")
    else:
        print("Available models:")
        for m in models:
            print("-", m["id"] if isinstance(m, dict) and "id" in m else m)
except Exception as e:
    print("Error fetching models:", e)
    if hasattr(e, 'response') and e.response is not None:
        print("Response:", e.response.text)
