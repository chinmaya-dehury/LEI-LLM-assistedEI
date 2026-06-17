"""
Master pipeline for LEI-LLM-assistedEI.

Adds timestamped CSV logging (script start/end, duration, status) so runs
can be correlated with downstream step logs. The pipeline executes the single
configured model from config.py and records that model in downstream CSV logs.

Modified on: 20-05-2026
"""

import csv
import importlib.util
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from config import DATA_TYPE, DEFAULT_MODEL
from shared_utils import sanitize_model_name, validate_data_type_exists, IST


# Validate that the DATA_TYPE folder exists with required files
validate_data_type_exists(DATA_TYPE)

BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "task_generator.py"
STEP_2_SCRIPT = BASE_DIR / "code_generator.py"
STEP_3_SCRIPT = BASE_DIR / "scheduler" / "edge_scheduler.py"

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
	"""Execute a Python script in-process and log timing."""
	active_model = (env_override or {}).get("LLM_MODEL", DEFAULT_MODEL)
	run_count = (env_override or {}).get("RUN_COUNT", "")
	start_time_ist = datetime.now(IST).isoformat()
	start_perf = time.perf_counter()

	# Save old environment and CWD
	old_env = os.environ.copy()
	old_cwd = os.getcwd()

	try:
		print(f"\nStarting: {script_path} (CWD: {cwd if cwd else os.getcwd()}) [In-Process]")
		
		# Change CWD if provided
		if cwd:
			os.chdir(cwd)

		# Update environment
		if env_override:
			for k, v in env_override.items():
				os.environ[k] = str(v)

		import importlib
		# Reload config and shared_utils to pick up new env vars
		for mod_name in ['config', 'shared_utils']:
			if mod_name in sys.modules:
				try:
					importlib.reload(sys.modules[mod_name])
				except Exception as e:
					print(f"[Pipeline] Warning: failed to reload {mod_name}: {e}")

		# Add parent directory of script to path
		script_dir = str(script_path.parent)
		if script_dir not in sys.path:
			sys.path.insert(0, script_dir)

		# Import the module dynamically
		module_name = script_path.stem
		# Force a fresh load
		sys.modules.pop(module_name, None)
		
		spec = importlib.util.spec_from_file_location(module_name, str(script_path))
		if spec is None or spec.loader is None:
			raise FileNotFoundError(f"Cannot find script at {script_path}")
		module = importlib.util.module_from_spec(spec)
		sys.modules[module_name] = module
		spec.loader.exec_module(module)

		# Run the script's main function
		if hasattr(module, "main"):
			return_code = module.main()
		else:
			print(f"[Warning] Module {module_name} has no main() function, just ran module code.")
			return_code = 0

		if return_code is None:
			return_code = 0

		if return_code != 0:
			raise RuntimeError(f"Script returned non-zero exit code: {return_code}")

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
				"return_code": return_code,
			}
		])
		return True

	except Exception as exc:
		elapsed = time.perf_counter() - start_perf
		end_time_ist = datetime.now(IST).isoformat()
		print(f"\nERROR: {script_path} failed in-process.")
		import traceback
		traceback.print_exc()

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
				"return_code": 1,
			}
		])
		raise

	finally:
		# Restore environment and CWD
		os.environ.clear()
		os.environ.update(old_env)
		os.chdir(old_cwd)


def run_pipeline() -> None:
	"""Execute the pipeline sequentially for the single configured model."""

	model = DEFAULT_MODEL
	print("\n================ PIPELINE START ===============")
	print(f"Configured model: {model}")

	failures: list[str] = []
	_set_pipeline_run(model)

	for run_num in range(1, 2):
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

			print("\nStep 4/4: Executing generated tasks via edge_scheduler.py")
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


def run_complex_task_synthesis() -> None:
	"""Execute LLM-driven complex task synthesis."""
	print("\n================ COMPLEX TASK SYNTHESIS (LLM-DRIVEN) ===============")
	
	try:
		cts_path = BASE_DIR / "complex_task_synthesis"
		if cts_path not in sys.path:
			sys.path.insert(0, str(cts_path))
		
		# Import and run the orchestrator
		import importlib.util
		spec = importlib.util.spec_from_file_location(
			"orchestration",
			cts_path / "orchestration.py"
		)
		runner_module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(runner_module)
		
		runner_module.run_complex_task_synthesis_workflow()
		print("\n[OK] Complex task synthesis completed successfully")
	
	except Exception as exc:
		print(f"\n[ERROR] Complex task synthesis failed: {exc}")
		import traceback
		traceback.print_exc()
		sys.exit(1)


if __name__ == "__main__":
	run_pipeline()
	# Optional: Uncomment to run complex task synthesis after pipeline
	#run_complex_task_synthesis()

