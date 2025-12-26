# Paths = Data type specific
# MAke sure that a fodler name with following data type exists inside 
#   data/, generated_tasks/ and output/ folders.
#
#### Select any one data type by uncommenting the line below

import os
from dotenv import load_dotenv

# Load .env from project root (load_dotenv looks for a .env file)
load_dotenv()

# DATA_TYPE available options: "temp_humidity", "air_quality"
DATA_TYPE = "temp_humidity"  # change only this line to switch data type

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "")
OPENROUTER_TITLE = os.getenv("OPENROUTER_TITLE", "")
OPENROUTER_DATA_COLLECTION_OPT_IN = os.getenv("OPENROUTER_DATA_COLLECTION_OPT_IN")

GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

LLM_PROVIDER = os.getenv("LLM_PROVIDER")
if not LLM_PROVIDER:
	if GEMINI_API_KEY:
		LLM_PROVIDER = "google"
	elif OPENROUTER_API_KEY:
		LLM_PROVIDER = "openrouter"
	else:
		LLM_PROVIDER = "google"

if LLM_PROVIDER == "openrouter":
	LLM_BASE_URL = OPENROUTER_BASE_URL
	LLM_API_KEY = OPENROUTER_API_KEY
	if OPENROUTER_DATA_COLLECTION_OPT_IN is None:
		OPENROUTER_DATA_COLLECTION_OPT_IN = "true"
else:
	LLM_PROVIDER = "google"
	LLM_BASE_URL = GEMINI_BASE_URL
	LLM_API_KEY = GEMINI_API_KEY
	OPENROUTER_DATA_COLLECTION_OPT_IN = OPENROUTER_DATA_COLLECTION_OPT_IN or ""

def _sanitize_model_id(model_id: str) -> str:
	if not isinstance(model_id, str):
		return ""
	model = model_id.strip()
	if not model:
		return ""
	if LLM_PROVIDER == "openrouter" and "/" not in model:
		model = f"openai/{model}"
	return model

# Requested model for the whole project
if LLM_PROVIDER == "openrouter":
	DEFAULT_MODEL = _sanitize_model_id(
		os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
	)
else:
	DEFAULT_MODEL = _sanitize_model_id(
		os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
	)

# Used by llm_orchestrator_* (task list generation)
TASK_LIST_MODEL = DEFAULT_MODEL

# Used by task_code_generator.py (ordered fallbacks)
TASK_CODE_MODELS = [
	DEFAULT_MODEL,
]

# Used by validator.py (LLM-based correction)
VALIDATOR_MODEL = DEFAULT_MODEL

MODEL_RATE_LIMITS = {
	"requests_per_minute": 10,
	"input_tokens_per_minute": 250_000,
	"requests_per_day": 20,
}

MIN_REQUEST_INTERVAL_SECONDS = 6.1  # Small buffer over 60 / 10 RPM

if not LLM_API_KEY:
	raise RuntimeError(
		"LLM API key not found. Set GEMINI_API_KEY or OPENROUTER_API_KEY in your environment."
	)

if not LLM_BASE_URL:
	raise RuntimeError(
		"LLM base URL not configured. Set GEMINI_BASE_URL or OPENROUTER_BASE_URL."
	)

NO_OF_TASKS = 1
parallel_execution = False
parallel_execution_limit = 2  # Max number of parallel tasks if parallel_execution is True, DEFAULT value is 1
