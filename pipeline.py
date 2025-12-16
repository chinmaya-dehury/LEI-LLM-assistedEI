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
from pathlib import Path
from typing import Optional
import time
import csv
from datetime import datetime, timezone

from config import DATA_TYPE


# === Script Locations ===
BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "llm_orchestrator_adaptive_resource.py"
STEP_2_SCRIPT = BASE_DIR / "task_code_generator.py"
STEP_3_SCRIPT = BASE_DIR / "scheduler" / "edge_scheduler_sequential.py"

# === Timestamp logging ===
TIMESTAMP_DIR = BASE_DIR / "timestamp_path" / DATA_TYPE
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
PIPELINE_CSV = TIMESTAMP_DIR / f"pipeline_timestamp_{RUN_ID}.csv"


def _append_pipeline_rows(rows):
	TIMESTAMP_DIR.mkdir(parents=True, exist_ok=True)
	file_exists = PIPELINE_CSV.exists() and PIPELINE_CSV.stat().st_size > 0
	fieldnames = [
		"run_id",
		"step",
		"script",
		"start_time_utc",
		"end_time_utc",
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


def run_script(step_name: str, script_path: Path, cwd: Optional[Path] = None) -> None:
	"""Execute a Python script using the current interpreter and log timing."""

	command = [sys.executable, script_path]

	# Prepare environment forcing UTF-8 for child Python process output
	env = os.environ.copy()
	env["PYTHONIOENCODING"] = "utf-8"

	start_time_utc = datetime.now(timezone.utc).isoformat()
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
		end_time_utc = datetime.now(timezone.utc).isoformat()
		print(f"✅ Success. ({elapsed:.2f}s) Output Snippet:\n{result.stdout[:200]}...") 

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"step": step_name,
				"script": str(script_path),
				"start_time_utc": start_time_utc,
				"end_time_utc": end_time_utc,
				"duration_sec": elapsed,
				"status": "success",
				"return_code": result.returncode,
			}
		])
		return True

	except subprocess.CalledProcessError as e:
		elapsed = time.perf_counter() - start_perf
		end_time_utc = datetime.now(timezone.utc).isoformat()
		print(f"\n❌ ERROR: {script_path} failed (exit {e.returncode}).")
		print(f"--- Stderr ---\n{e.stderr}")
		print(f"--- Stdout ---\n{e.stdout}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"step": step_name,
				"script": str(script_path),
				"start_time_utc": start_time_utc,
				"end_time_utc": end_time_utc,
				"duration_sec": elapsed,
				"status": "failed",
				"return_code": e.returncode,
			}
		])
		raise
	except FileNotFoundError:
		elapsed = time.perf_counter() - start_perf
		end_time_utc = datetime.now(timezone.utc).isoformat()
		print(f"\n❌ ERROR: Script not found at {script_path}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"step": step_name,
				"script": str(script_path),
				"start_time_utc": start_time_utc,
				"end_time_utc": end_time_utc,
				"duration_sec": elapsed,
				"status": "missing",
				"return_code": "",
			}
		])
		raise


def run_pipeline() -> None:
	"""Execute the three-stage pipeline sequentially."""

	print("\n================ PIPELINE START ===============")
	try:
		print("\nStep 1/3: Generating task list via llm_orchestrator_adaptive_resource.py")
		run_script("step1_orchestrator", STEP_1_SCRIPT)

		print("\nStep 2/3: Generating code via task_code_generator.py")
		run_script("step2_generator", STEP_2_SCRIPT)

		print("\nIntermediate Step: Validator run now\n");
		run_script("step3_validator", BASE_DIR / "validator.py")

		print("\nStep 3/3: Executing generated tasks via edge_scheduler_sequential.py")
		run_script("step4_scheduler", STEP_3_SCRIPT, cwd=BASE_DIR)

	except Exception as exc:
		print("\n Pipeline aborted due to failure.")
		print(f"Reason: {exc}")
		sys.exit(1)

	print("\n Pipeline completed successfully.")
	print("================= PIPELINE END =================\n")


if __name__ == "__main__":
	run_pipeline()

