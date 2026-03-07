import os
from dotenv import load_dotenv

load_dotenv()

DATA_TYPE = "temp_humidity"

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "").strip().lower()

GENERIC_API_KEY = os.getenv("LLM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not LLM_PROVIDER:
	if OPENAI_API_KEY:
		LLM_PROVIDER = "openai"
	elif GEMINI_API_KEY:
		LLM_PROVIDER = "gemini"
	else:
		LLM_PROVIDER = "generic"

if LLM_PROVIDER == "openai":
	LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
	LLM_API_KEY = GENERIC_API_KEY or OPENAI_API_KEY
	DEFAULT_MODEL = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
elif LLM_PROVIDER == "gemini":
	LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta/openai"
	LLM_API_KEY = GENERIC_API_KEY or GEMINI_API_KEY
	DEFAULT_MODEL = os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"
else:
	LLM_BASE_URL = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
	LLM_API_KEY = GENERIC_API_KEY or OPENAI_API_KEY or GEMINI_API_KEY
	DEFAULT_MODEL = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("GEMINI_MODEL") or "gpt-4o-mini"

if not LLM_API_KEY:
	raise RuntimeError("LLM API key not found. Set LLM_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY in your .env file.")

if not LLM_BASE_URL:
	raise RuntimeError("LLM base URL not configured. Set LLM_BASE_URL in your .env file.")

if not DATA_TYPE:
	raise RuntimeError("DATA_TYPE is not set. Please set it in config.py.")