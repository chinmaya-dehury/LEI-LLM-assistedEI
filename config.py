'''
config.py fetches one or more use_case entries (DATA_TYPE) based on the device's hostname from device.yml.
It also loads LLM configuration from environment variables and sets up constants for the pipeline.

Supports multiple use cases per device. When a device lists several use_case values, set EDGE_USE_CASE
to pick one; otherwise the first listed use case is used.

Last updated: 25-02-2026
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


def _normalize_use_cases(raw_use_case) -> List[str]:
	"""Normalize comma-separated strings or lists of use cases into a clean list."""
	if isinstance(raw_use_case, str):
		candidates = [part.strip() for part in raw_use_case.split(",") if part.strip()]
	elif isinstance(raw_use_case, (list, tuple)):
		candidates = [str(part).strip() for part in raw_use_case if str(part).strip()]
	else:
		return []

	seen = set()
	normalized: List[str] = []
	for item in candidates:
		key = item.lower()
		if key in seen:
			continue
		seen.add(key)
		normalized.append(item)
	return normalized


def _load_device_use_cases(devices_file: Path) -> List[Tuple[str, List[str]]]:
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
	runs: List[Tuple[str, List[str]]] = []
	for device_name, device_info in devices_section.items():
		if not isinstance(device_info, dict):
			continue
		use_cases = _normalize_use_cases(device_info.get("use_case"))
		runs.append((device_name, use_cases))
	return runs


DEVICE_USE_CASES = _load_device_use_cases(DEVICE_CONFIG_PATH)
if not DEVICE_USE_CASES:
	raise RuntimeError("No devices found in device.yml; add at least one device entry.")

if all((not use_cases) for _, use_cases in DEVICE_USE_CASES):
	raise RuntimeError(
		"No use_case entries configured for any device in device.yml; add at least one use_case per device."
	)

DEVICE_USE_CASE_MAP: Dict[str, List[str]] = {device: use_cases for device, use_cases in DEVICE_USE_CASES}
DEVICE_NAMES: List[str] = [device for device, _ in DEVICE_USE_CASES]
USE_CASES: List[str] = [use_case for _, use_cases in DEVICE_USE_CASES for use_case in use_cases]


def _normalize_device_name(name: str) -> str:
	return (name or "").strip().lower()


DEVICE_LOOKUP: Dict[str, Tuple[str, List[str]]] = {
	_normalize_device_name(device): (device, use_cases)
	for device, use_cases in DEVICE_USE_CASES
}


def _select_use_case(device: str, use_cases: List[str]) -> str:
	override = os.getenv("EDGE_USE_CASE")
	if not use_cases:
		if override:
			return override.strip()
		fallback_env = os.getenv("DEFAULT_USE_CASE")
		if fallback_env:
			print(
				f"[config] No use_case listed for {device}. Using DEFAULT_USE_CASE='{fallback_env.strip()}'"
			)
			return fallback_env.strip()
		print(
			f"[config] No use_case listed for {device}. Skipping execution for this device unless EDGE_USE_CASE or DEFAULT_USE_CASE is set."
		)
		return ""

	if override:
		override_normalized = override.strip().lower()
		for candidate in use_cases:
			if candidate.lower() == override_normalized:
				return candidate
		available = ", ".join(use_cases)
		raise RuntimeError(
			f"EDGE_USE_CASE '{override}' is not valid for device '{device}'. Available: {available}"
		)

	if len(use_cases) == 1:
		return use_cases[0]

	print(
		f"[config] Multiple use_case entries for {device}: {', '.join(use_cases)}. "
		"Using the first entry; set EDGE_USE_CASE to override."
	)
	return use_cases[0]


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
		device, use_cases = match
		selected_use_case = _select_use_case(device, use_cases)
		return device, selected_use_case
	available = ", ".join(DEVICE_NAMES)
	raise RuntimeError(
		f"Detected device '{detected}' is not defined in device.yml. Available devices: {available}"
	)


ACTIVE_DEVICE, DATA_TYPE = _resolve_active_device()
ACTIVE_USE_CASES: List[str] = [uc for uc in DEVICE_USE_CASE_MAP.get(ACTIVE_DEVICE, []) if uc]
if not ACTIVE_USE_CASES and DATA_TYPE:
	ACTIVE_USE_CASES = [DATA_TYPE]


def _print_device_binding() -> None:
	available = ", ".join(DEVICE_USE_CASE_MAP.get(ACTIVE_DEVICE, []))
	print(f"[config] Active device: {ACTIVE_DEVICE} | use_case: {DATA_TYPE} | available: {available}")

GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

LLM_PROVIDER = "google"
LLM_BASE_URL = GEMINI_BASE_URL
LLM_API_KEY = GEMINI_API_KEY

def _sanitize_model_id(model_id: str) -> str:
	if not isinstance(model_id, str):
		return ""
	model = model_id.strip()
	if not model:
		return ""
	return model

# Requested model for the whole project
DEFAULT_MODEL = _sanitize_model_id(
	os.getenv("GEMINI_MODEL", "gemma-3-12b-it")
)

# Used by llm_orchestrator_* (task list generation)
TASK_LIST_MODEL = DEFAULT_MODEL

# Used by task_code_generator.py (fallback to DEFAULT_MODEL)
TASK_CODE_MODELS = [DEFAULT_MODEL]

# Used by validator.py (LLM-based correction)
VALIDATOR_MODEL = DEFAULT_MODEL

# Models to compare in pipeline (each model runs RUNS_PER_MODEL times)
COMPARISON_MODELS = [
	"gemma-3-12b-it",
]

RUNS_PER_MODEL = 1  # Number of times each model runs for comparison

MODEL_RATE_LIMITS = {
	"requests_per_minute": 30,
	"input_tokens_per_minute": 15_000,
	"requests_per_day": 14_400,
}

MIN_REQUEST_INTERVAL_SECONDS = 2.1  # 30 RPM cap -> ~2s spacing, keeping small safety margin

if not LLM_API_KEY:
	raise RuntimeError(
		"LLM API key not found. Set GEMINI_API_KEY in your environment."
	)

if not LLM_BASE_URL:
	raise RuntimeError(
		"LLM base URL not configured. Set GEMINI_BASE_URL."
	)

NO_OF_TASKS = 1
parallel_execution = False
parallel_execution_limit = 2  # Max number of parallel tasks if parallel_execution is True, DEFAULT value is 1

if os.getenv("PRINT_DEVICE_BINDING") == "1":
	_print_device_binding()

if __name__ == "__main__":
	_print_device_binding()
