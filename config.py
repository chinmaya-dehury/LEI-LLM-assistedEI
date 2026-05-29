import os
from dotenv import load_dotenv

load_dotenv()

# later on change the default "air_quality" to use COMPLEX tasks
DATA_TYPE = os.getenv("DATA_TYPE", "air_quality")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "generic").strip().lower()

# LLM API credentials and endpoint
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_VAL_MODEL = os.getenv("LLM_VAL_MODEL", DEFAULT_MODEL)  # Validation-specific model (defaults to DEFAULT_MODEL)

# Optional rate limit and provider-specific settings (safe defaults)
MODEL_RATE_LIMITS = {}
MIN_REQUEST_INTERVAL_SECONDS = float(os.getenv("MIN_REQUEST_INTERVAL_SECONDS", "0"))
OPENROUTER_DATA_COLLECTION_OPT_IN = os.getenv("OPENROUTER_DATA_COLLECTION_OPT_IN", None)
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.getenv("OPENROUTER_TITLE", "")

# Validation
if not LLM_API_KEY:
	raise RuntimeError("LLM_API_KEY not found in .env file")

if not LLM_BASE_URL:
	raise RuntimeError("LLM_BASE_URL not configured in .env file")

if not DATA_TYPE:
	raise RuntimeError("DATA_TYPE is not set. Please set it in config.py.")

# ============================================================================
# LLM Configuration
# ============================================================================
# Two options supported:
# 
# OPTION 1: Generic LLM Provider (ChatGPT, Gemini, Groq, Claude, etc.)
#   LLM_PROVIDER=generic
#   LLM_BASE_URL=https://api.groq.com/openai/v1  (or your provider's URL)
#   LLM_API_KEY=your-api-key
#   LLM_MODEL=llama-3.3-70b-versatile  (or your model name)
#
# OPTION 2: Ollama (Local LLM - self-hosted)
#   LLM_PROVIDER=ollama
#   LLM_BASE_URL=http://localhost:11434/v1
#   LLM_API_KEY=ollama
#   LLM_MODEL=llama2  (or any ollama model)
#
# See .env.example for detailed provider configurations
# ============================================================================