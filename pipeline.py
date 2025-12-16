"""
pipeline.py
--------------------------------
This is a master pipeline script that orchestrates the entire workflow of
from llm_orchestrator_adaptive.py to task_code_generator_updated.py to edge_scheduler_sequential.py.

It first generates task descriptions using an LLM, then generates Python code for each task,
and finally schedules and executes these tasks on an edge device simulator.

The pipeline is designed to be modular and extensible, allowing for easy updates and improvements
to individual components without affecting the entire workflow.

"""

import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional
import time
import csv
from datetime import datetime, timezone, timedelta
import importlib

from config import DATA_TYPE


# === Script Locations ===
BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "llm_orchestrator_adaptive_resource.py"
STEP_2_SCRIPT = BASE_DIR / "task_code_generator.py"
STEP_3_SCRIPT = BASE_DIR / "scheduler" / "edge_scheduler_sequential.py"

# === Timestamp logging ===
TIMESTAMP_DIR = BASE_DIR / "timestamp_path" / DATA_TYPE
MODELS_FILE = BASE_DIR / "models.yaml"
IST = timezone(timedelta(hours=5, minutes=30))
RUN_ID = ""
PIPELINE_CSV: Path | None = None


def _sanitize_model_name(model: str) -> str:
	return (
		(model or "model")
		.replace(" ", "_")
		.replace(":", "_")
		.replace("/", "_")
		.replace("\\", "_")
	)


def _set_pipeline_run(model: str) -> None:
	global RUN_ID, PIPELINE_CSV
	RUN_ID = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
	PIPELINE_CSV = TIMESTAMP_DIR / f"pipeline_timestamp_{_sanitize_model_name(model)}_{RUN_ID}.csv"


def _load_models() -> list[str]:
	try:
		yaml = importlib.import_module("yaml")
	except ModuleNotFoundError as exc:
		raise RuntimeError("Missing dependency: pyyaml. Install it with 'pip install pyyaml'.") from exc

	with open(MODELS_FILE, "r", encoding="utf-8") as f:
		data = yaml.safe_load(f) or {}
	models = data.get("models") or []
	return [str(m).strip() for m in models if str(m).strip()]


def _clean_before_model_run() -> None:
	# Remove/delelte all the tasks/code from generated_tasks and output before each model run.
	paths = [
		BASE_DIR / "generated_tasks" / DATA_TYPE,
		BASE_DIR / "output" / DATA_TYPE,
	]
	for p in paths:
		if p.exists():
			shutil.rmtree(p)
		p.mkdir(parents=True, exist_ok=True)


def _append_pipeline_rows(rows):
	TIMESTAMP_DIR.mkdir(parents=True, exist_ok=True)
	if PIPELINE_CSV is None:
		raise RuntimeError("PIPELINE_CSV not initialized")
	file_exists = PIPELINE_CSV.exists() and PIPELINE_CSV.stat().st_size > 0
	fieldnames = [
		"run_id",
		"step",
		"script",
		"start_time_ist",
		"end_time_ist",
		"duration_sec",
		"status",
		"return_code",
	]
	with open(PIPELINE_CSV, "a", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=fieldnames)
		if not file_exists:
			writer.writeheader()
		for row in rows:
			writer.writerow(row)


def run_script(step_name: str, script_path: Path, cwd: Optional[Path] = None, env_override: Optional[dict] = None) -> bool:
	"""Execute a Python script using the current interpreter and log timing."""

	command = [sys.executable, script_path]

	# Prepare environment forcing UTF-8 for child Python process output
	env = os.environ.copy()
	env["PYTHONIOENCODING"] = "utf-8"
	if env_override:
		env.update(env_override)

	start_time_ist = datetime.now(IST).isoformat()
	start_perf = time.perf_counter()

	try:
		print(f"\n🚀 Starting: {script_path} (CWD: {cwd if cwd else os.getcwd()})")

		result = subprocess.run(
			command,
			check=True,             # raise CalledProcessError on non-zero exit
			capture_output=True,
			text=True,              # use text mode
			encoding="utf-8",       # decode using UTF-8
			errors="replace",       # replace undecodable bytes instead of raising
			cwd=cwd,
			env=env
		)

		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()
		print(f"✅ Success. ({elapsed:.2f}s) Output Snippet:\n{result.stdout[:200]}...") 

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"step": step_name,
				"script": str(script_path),
				"start_time_ist": start_time_ist,
				"end_time_ist": end_time_ist,
				"duration_sec": elapsed,
				"status": "success",
				"return_code": result.returncode,
			}
		])
		return True

	except subprocess.CalledProcessError as e:
		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()
		print(f"\n❌ ERROR: {script_path} failed (exit {e.returncode}).")
		print(f"--- Stderr ---\n{e.stderr}")
		print(f"--- Stdout ---\n{e.stdout}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"step": step_name,
				"script": str(script_path),
				"start_time_ist": start_time_ist,
				"end_time_ist": end_time_ist,
				"duration_sec": elapsed,
				"status": "failed",
				"return_code": e.returncode,
			}
		])
		raise
	except FileNotFoundError:
		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()
		print(f"\n❌ ERROR: Script not found at {script_path}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"step": step_name,
				"script": str(script_path),
				"start_time_ist": start_time_ist,
				"end_time_ist": end_time_ist,
				"duration_sec": elapsed,
				"status": "missing",
				"return_code": "",
			}
		])
		raise


def run_pipeline() -> None:
	"""Execute the pipeline sequentially for each model in models.yaml."""

	models = _load_models()
	if not models:
		print("No models found in models.yaml under key 'models'.")
		return

	print("\n================ PIPELINE START ===============")
	failures: list[str] = []
	for model in models:
		print(f"\n=== Running pipeline for model: {model} ===")
		_clean_before_model_run()
		_set_pipeline_run(model)
		env_override = {"MODEL_NAME": model}
		try:
			print("\nStep 1/4: Generating task list via llm_orchestrator_adaptive_resource.py")
			run_script("step1_orchestrator", STEP_1_SCRIPT, env_override=env_override)

			print("\nStep 2/4: Generating code via task_code_generator.py")
			run_script("step2_generator", STEP_2_SCRIPT, env_override=env_override)

			print("\nStep 3/4: Validator run")
			run_script("step3_validator", BASE_DIR / "validator.py", env_override=env_override)

			print("\nStep 4/4: Executing generated tasks via edge_scheduler_sequential.py")
			run_script("step4_scheduler", STEP_3_SCRIPT, cwd=BASE_DIR, env_override=env_override)

		except Exception as exc:
			failures.append(f"{model}: {exc}")
			print("\n Pipeline aborted for this model due to failure.")
			print(f"Reason: {exc}")
			continue

	print("\n Pipeline completed for all models.")
	print("================= PIPELINE END =================\n")
	if failures:
		print("Failures:")
		for f in failures:
			print(" -", f)
		sys.exit(1)


if __name__ == "__main__":
	run_pipeline()

