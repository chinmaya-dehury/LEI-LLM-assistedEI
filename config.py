'''
config.py fetches the use_case (DATA_TYPE) based on the device's hostname from device.yml. 
It also loads LLM configuration from environment variables and sets up constants for the pipeline.

Last updated: 22-02-2026
By Siddharth
'''


import os
import socket
from pathlib import Path
from typing import Dict, List, Tuple

import yaml
from dotenv import load_dotenv

# Load .env from project root (load_dotenv looks for a .env file)
load_dotenv()

# DATA_TYPE is now derived from device.yml use_case entries

BASE_DIR = Path(__file__).parent.resolve()
DEVICE_CONFIG_PATH = BASE_DIR / "device.yml"


def _load_device_use_cases(devices_file: Path) -> List[Tuple[str, str]]:
	if not devices_file.exists():
		raise RuntimeError(f"Device file not found at {devices_file}")
	try:
		with devices_file.open("r", encoding="utf-8") as handle:
			payload = yaml.safe_load(handle) or {}
	except yaml.YAMLError as exc:
		raise RuntimeError(f"Invalid YAML in {devices_file}: {exc}") from exc
	devices_section = payload.get("devices") or {}
	if not isinstance(devices_section, dict):
		raise RuntimeError("device.yml must define a 'devices' mapping")
	runs: List[Tuple[str, str]] = []
	for device_name, device_info in devices_section.items():
		if not isinstance(device_info, dict):
			continue
		candidate = (device_info.get("use_case") or "").strip()
		if candidate:
			runs.append((device_name, candidate))
	return runs


DEVICE_USE_CASES = _load_device_use_cases(DEVICE_CONFIG_PATH)
if not DEVICE_USE_CASES:
	raise RuntimeError("No use_case entries found in device.yml; add at least one use_case per device.")

DEVICE_USE_CASE_MAP: Dict[str, str] = {device: use_case for device, use_case in DEVICE_USE_CASES}
DEVICE_NAMES: List[str] = [device for device, _ in DEVICE_USE_CASES]
USE_CASES: List[str] = [use_case for _, use_case in DEVICE_USE_CASES]


def _normalize_device_name(name: str) -> str:
	return (name or "").strip().lower()


DEVICE_LOOKUP: Dict[str, Tuple[str, str]] = {
	_normalize_device_name(device): (device, use_case)
	for device, use_case in DEVICE_USE_CASES
}


def _detect_device_name() -> str:
	override = os.getenv("EDGE_DEVICE_NAME")
	if override:
		return override.strip()
	return socket.gethostname().strip()


def _resolve_active_device() -> Tuple[str, str]:
	detected = _detect_device_name()
	normalized = _normalize_device_name(detected)
	match = DEVICE_LOOKUP.get(normalized)
	if match:
		return match
	available = ", ".join(DEVICE_NAMES)
	raise RuntimeError(
		f"Detected device '{detected}' is not defined in device.yml. Available devices: {available}"
	)


ACTIVE_DEVICE, DATA_TYPE = _resolve_active_device()


def _print_device_binding() -> None:
	print(f"[config] Active device: {ACTIVE_DEVICE} | use_case: {DATA_TYPE}")

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
		os.getenv("GEMINI_MODEL", "Gemini 2.5 Flash")
	)

# Used by llm_orchestrator_* (task list generation)
TASK_LIST_MODEL = DEFAULT_MODEL

# Used by task_code_generator.py (fallback to DEFAULT_MODEL)
TASK_CODE_MODELS = [DEFAULT_MODEL]

# Used by validator.py (LLM-based correction)
VALIDATOR_MODEL = DEFAULT_MODEL

# Models to compare in pipeline (each model runs RUNS_PER_MODEL times)
COMPARISON_MODELS = [
	"Gemini 2.5 Flash",
]

RUNS_PER_MODEL = 2  # Number of times each model runs for comparison

MODEL_RATE_LIMITS = {
	"requests_per_minute": 5,
	"input_tokens_per_minute": 250_000,
	"requests_per_day": 20,
}

MIN_REQUEST_INTERVAL_SECONDS = 12.0  # Gemini 2.5 Flash: 5 RPM cap -> ~12s spacing

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

if os.getenv("PRINT_DEVICE_BINDING") == "1":
	_print_device_binding()

if __name__ == "__main__":
	_print_device_binding()
