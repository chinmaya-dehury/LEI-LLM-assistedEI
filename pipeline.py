"""
pipeline.py
--------------------------------
This is a master pipeline script that orchestrates the entire workflow of
from task_generator.py to code_generator.py to edge_scheduler_sequential.py.

It first generates task descriptions using an LLM, then generates Python code for each task,
and finally schedules and executes these tasks on an edge device simulator.

The pipeline is designed to be modular and extensible, allowing for easy updates and improvements
to individual components without affecting the entire workflow.

Last Modfified: 19-12-2025
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
STEP_1_SCRIPT = BASE_DIR / "task_generator.py"
STEP_2_SCRIPT = BASE_DIR / "code_generator.py"
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
			"run_id",		"model",			"run_count",
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
	"""Execute a Python script using the current interpreter and log timing.

	This function uses a consistent 4-space indentation style and records
	`run_count` (if provided via `env_override`) into the pipeline CSV rows.
	"""

	command = [sys.executable, str(script_path)]

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
			check=True,
			capture_output=True,
			text=True,
			encoding="utf-8",
			errors="replace",
			cwd=cwd,
			env=env,
		)

		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()

		print(f"✅ Success. ({elapsed:.2f}s)")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"model": env_override.get("MODEL_NAME", "") if env_override else "",
				"run_count": env_override.get("RUN_COUNT") if env_override else os.environ.get("RUN_COUNT", ""),
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
				"model": env_override.get("MODEL_NAME", "") if env_override else "",
				"run_count": env_override.get("RUN_COUNT") if env_override else os.environ.get("RUN_COUNT", ""),
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
				"model": env_override.get("MODEL_NAME", "") if env_override else "",
				"run_count": env_override.get("RUN_COUNT") if env_override else os.environ.get("RUN_COUNT", ""),
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
		# Set RUN_ID once per model so all 10 runs append to the same CSV files
		_set_pipeline_run(model)
		for run_num in range(1,11):
			print(f"\nRunning pipeline for model {model} Run {run_num}")
			# Clean generated tasks/output before each run
			_clean_before_model_run()
			env_override = {"MODEL_NAME": model, "RUN_ID": RUN_ID, "RUN_COUNT": str(run_num)}
			try:
				print("\nStep 1/4: Generating task list via task_generator.py")
				run_script("step1_task_generator", STEP_1_SCRIPT, env_override=env_override)

				print("\nStep 2/4: Generating code via code_generator.py")
				run_script("step2_code_generator", STEP_2_SCRIPT, env_override=env_override)

				print("\nStep 3/4: Validator run")
				run_script("step3_validator", BASE_DIR / "validator.py", env_override=env_override)

				print("\nStep 4/4: Executing generated tasks via edge_scheduler_sequential.py")
				run_script("step4_scheduler", STEP_3_SCRIPT, cwd=BASE_DIR, env_override=env_override)

			except Exception as exc:
				failures.append(f"{model} run {run_num}: {exc}")
				print("\n Pipeline aborted for this run due to failure.")
				print(f"Reason: {exc}")
				# continue to next run
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

