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

# OpenRouter is OpenAI-compatible.
LLM_BASE_URL = OPENROUTER_BASE_URL
LLM_API_KEY = OPENROUTER_API_KEY

# OpenRouter requires a fully-qualified model id like: "deepseek/deepseek-r1-0528:free".
def _normalize_openrouter_model_id(model_id: str) -> str:
	if not isinstance(model_id, str):
		return ""
	m = model_id.strip()
	if not m:
		return ""
	# If user provides shorthand like "deepseek-r1-0528:free", add provider prefix.
	if "/" not in m and m.lower().startswith("google/"):
		m = f"google/{m}"
	return m

# Requested model for the whole project
DEFAULT_MODEL = _normalize_openrouter_model_id(
	#os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-0528:free")
	os.getenv("OPENROUTER_MODEL", "allenai/olmo-3.1-32b-think:free")
)

# Used by llm_orchestrator_* (task list generation)
TASK_LIST_MODEL = DEFAULT_MODEL

# Used by task_code_generator.py (ordered fallbacks)
TASK_CODE_MODELS = [
	DEFAULT_MODEL,
]

# Used by validator.py (LLM-based correction)
VALIDATOR_MODEL = DEFAULT_MODEL

if not LLM_API_KEY:
	raise RuntimeError(
		"OPENROUTER_API_KEY not found. Add it to your .env or set the environment variable."
	)

if not LLM_BASE_URL:
	raise RuntimeError(
		"OPENROUTER_BASE_URL not found. Set OPENROUTER_BASE_URL (e.g., https://openrouter.ai/api/v1)."
	)

NO_OF_TASKS = 1
parallel_execution = False
parallel_execution_limit = 2  # Max number of parallel tasks if parallel_execution is True, DEFAULT value is 1
