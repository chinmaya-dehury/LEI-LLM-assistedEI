import os
from dotenv import load_dotenv

load_dotenv()

DATA_TYPE = os.getenv("DATA_TYPE")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").strip().lower()

# ---------------------------------------------------------------------------
# Generation LLM
# ---------------------------------------------------------------------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "moonshotai/kimi-k2.7-code")

# Optional comma-separated list of generation models used by the benchmark runner
_LLM_GEN_MODELS_RAW = os.getenv("LLM_GEN_MODELS", "").strip()
if _LLM_GEN_MODELS_RAW:
    LLM_GEN_MODELS_LIST = [m.strip() for m in _LLM_GEN_MODELS_RAW.split(",") if m.strip()]
else:
    LLM_GEN_MODELS_LIST = [DEFAULT_MODEL]

# ---------------------------------------------------------------------------
# Validation LLM
# ---------------------------------------------------------------------------
LLM_VAL_BASE_URL = os.getenv("LLM_VAL_BASE_URL", LLM_BASE_URL)
LLM_VAL_API_KEY = os.getenv("LLM_VAL_API_KEY", LLM_API_KEY)
LLM_VAL_MODEL = os.getenv("LLM_VAL_MODEL", DEFAULT_MODEL)

# Optional comma-separated list of validation models (majority voting)
LLM_VAL_MODELS = os.getenv("LLM_VAL_MODELS", "").strip()
if LLM_VAL_MODELS:
    LLM_VAL_MODELS_LIST = [m.strip() for m in LLM_VAL_MODELS.split(",") if m.strip()]
else:
    LLM_VAL_MODELS_LIST = [LLM_VAL_MODEL]

# ---------------------------------------------------------------------------
# Optional rate-limit / provider settings
# ---------------------------------------------------------------------------
MODEL_RATE_LIMITS = {}
MIN_REQUEST_INTERVAL_SECONDS = float(os.getenv("MIN_REQUEST_INTERVAL_SECONDS", "0"))
OPENROUTER_DATA_COLLECTION_OPT_IN = os.getenv("OPENROUTER_DATA_COLLECTION_OPT_IN", None)
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.getenv("OPENROUTER_TITLE", "")

# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY not found in .env file")

if not LLM_BASE_URL:
    raise RuntimeError("LLM_BASE_URL not configured in .env file")

if not LLM_VAL_API_KEY:
    raise RuntimeError("LLM_VAL_API_KEY not found in .env file")

if not LLM_VAL_BASE_URL:
    raise RuntimeError("LLM_VAL_BASE_URL not configured in .env file")

if not DATA_TYPE:
    raise RuntimeError("DATA_TYPE is not set. Please set it in .env.")