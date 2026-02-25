import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY", "").strip()
base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").strip()
target = sys.argv[1] if len(sys.argv) > 1 else "gemma-3-12b-it"

if not api_key:
    raise SystemExit("GEMINI_API_KEY is not set.")

url = f"{base_url}/models"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})

with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))

models = [m.get("id", "") for m in data.get("data", [])]
normalized_models = {m.removeprefix("models/") for m in models}
target_normalized = target.removeprefix("models/")
print(f"Total models: {len(models)}")
for m in models:
    print(m)

print("\nCheck:")
if target in models:
    print(f"OK: '{target}' is available.")
elif target_normalized in normalized_models:
    print(f"OK: '{target}' is available (matched as 'models/{target_normalized}').")
else:
    print(f"NOT FOUND: '{target}' is not available.")
