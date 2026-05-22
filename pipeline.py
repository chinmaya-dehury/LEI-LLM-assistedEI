"""
Master pipeline for LEI-LLM-assistedEI.

Adds timestamped CSV logging (script start/end, duration, status) so runs
can be correlated with downstream step logs. The pipeline executes the single
configured model from config.py and records that model in downstream CSV logs.

Modified on: 20-05-2026
"""

import csv
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from config import DATA_TYPE, DEFAULT_MODEL
from shared_utils import sanitize_model_name, IST


BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "task_generator.py"
STEP_2_SCRIPT = BASE_DIR / "code_generator.py"
STEP_3_SCRIPT = BASE_DIR / "scheduler" / "edge_scheduler_sequential.py"

TIMESTAMP_DIR = BASE_DIR / "timestamp_path" / DATA_TYPE
RUN_ID = ""
PIPELINE_CSV: Path | None = None


def _set_pipeline_run(model: str) -> None:
	global RUN_ID, PIPELINE_CSV
	RUN_ID = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
	PIPELINE_CSV = TIMESTAMP_DIR / f"pipeline_timestamp_{sanitize_model_name(model)}_{RUN_ID}.csv"


def _append_pipeline_rows(rows: list[dict]) -> None:
	TIMESTAMP_DIR.mkdir(parents=True, exist_ok=True)
	if PIPELINE_CSV is None:
		raise RuntimeError("PIPELINE_CSV not initialized")

	file_exists = PIPELINE_CSV.exists() and PIPELINE_CSV.stat().st_size > 0
	fieldnames = [
		"run_id",
		"model",
		"run_count",
		"step",
		"script",
		"start_time_ist",
		"end_time_ist",
		"duration_sec",
		"status",
		"return_code",
	]

	with open(PIPELINE_CSV, "a", newline="", encoding="utf-8") as file_obj:
		writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
		if not file_exists:
			writer.writeheader()
		for row in rows:
			writer.writerow(row)


def run_script(
	step_name: str,
	script_path: Path,
	cwd: Optional[Path] = None,
	env_override: Optional[dict] = None,
) -> bool:
	"""Execute a Python script using the current interpreter and log timing."""

	command = [sys.executable, str(script_path)]
	env = os.environ.copy()
	env["PYTHONIOENCODING"] = "utf-8"
	if env_override:
		env.update(env_override)

	active_model = env.get("LLM_MODEL", DEFAULT_MODEL)
	run_count = env.get("RUN_COUNT", "")
	start_time_ist = datetime.now(IST).isoformat()
	start_perf = time.perf_counter()

	try:
		print(f"\nStarting: {script_path} (CWD: {cwd if cwd else os.getcwd()})")
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
		print(f"Success. ({elapsed:.2f}s)")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"model": active_model,
				"run_count": run_count,
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

	except subprocess.CalledProcessError as exc:
		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()
		print(f"\nERROR: {script_path} failed (exit {exc.returncode}).")
		print(f"--- Stderr ---\n{exc.stderr}")
		print(f"--- Stdout ---\n{exc.stdout}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"model": active_model,
				"run_count": run_count,
				"step": step_name,
				"script": str(script_path),
				"start_time_ist": start_time_ist,
				"end_time_ist": end_time_ist,
				"duration_sec": elapsed,
				"status": "failed",
				"return_code": exc.returncode,
			}
		])
		raise

	except FileNotFoundError:
		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()
		print(f"\nERROR: Script not found at {script_path}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"model": active_model,
				"run_count": run_count,
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
	"""Execute the pipeline sequentially for the single configured model."""

	model = DEFAULT_MODEL
	print("\n================ PIPELINE START ===============")
	print(f"Configured model: {model}")

	failures: list[str] = []
	_set_pipeline_run(model)

	for run_num in range(1, 6):
		print(f"\nRunning pipeline for model {model} Run {run_num}")
		# Removed _clean_before_run() to preserve generated_tasks and output directories
		env_override = {
			"LLM_MODEL": model,
			"RUN_ID": RUN_ID,
			"RUN_COUNT": str(run_num),
		}

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
			continue

	print("\n Pipeline completed for all runs.")
	print("================= PIPELINE END =================\n")
	if failures:
		print("Failures:")
		for failure in failures:
			print(" -", failure)
		sys.exit(1)


if __name__ == "__main__":
	run_pipeline()

