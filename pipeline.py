"""
pipeline.py
--------------------------------
Master pipeline for LEI-LLM-assistedEI.

Adds timestamped CSV logging (script start/end, duration, status) so runs
can be correlated with downstream step logs. Unlike LEI-OLLAMA, this version
 targets Gemini models from config.py and does not use models.yaml.
"""

import csv
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from config import DATA_TYPE, DEFAULT_MODEL, COMPARISON_MODELS, RUNS_PER_MODEL

# === Script Locations ===
BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "task_generator.py"
STEP_2_SCRIPT = BASE_DIR / "code_generator.py"
STEP_3_SCRIPT = BASE_DIR / "scheduler" / "edge_scheduler_sequential.py"

# === Directory paths ===
project_root = BASE_DIR
generated_tasks_dir = BASE_DIR / "generated_tasks" / DATA_TYPE
output_dir = BASE_DIR / "output" / DATA_TYPE

# === Timestamp logging ===
TIMESTAMP_DIR = BASE_DIR / "timestamp_path" / DATA_TYPE
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


def _clean_before_run():
    """Remove old generated files before starting new run."""
    dirs_to_clean = [
        generated_tasks_dir,
        output_dir,
        os.path.join(project_root, "scheduler", "output", DATA_TYPE),
    ]
    for p in dirs_to_clean:
        if os.path.isdir(p):
            try:
                # Try to remove all contents but keep the directory
                for item in os.listdir(p):
                    item_path = os.path.join(p, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True)
                    except Exception as e:
                        print(f"Warning: Could not remove {item_path}: {e}")
            except PermissionError as e:
                print(f"Warning: Permission denied cleaning {p}: {e}")
                print(f"Continuing anyway - files may be overwritten.")
            except Exception as e:
                print(f"Warning: Error cleaning {p}: {e}")
                print(f"Continuing anyway.")
        
        # Ensure directory exists
        os.makedirs(p, exist_ok=True)


def _append_pipeline_rows(rows: list[dict]) -> None:
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
	"""Execute a Python script using the current interpreter and log timing."""

	command = [sys.executable, str(script_path)]

	env = os.environ.copy()
	env["PYTHONIOENCODING"] = "utf-8"
	if env_override:
		env.update(env_override)

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
				"model": env_override.get("MODEL_NAME", DEFAULT_MODEL) if env_override else DEFAULT_MODEL,
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

		print(f"\nERROR: {script_path} failed (exit {e.returncode}).")
		print(f"--- Stderr ---\n{e.stderr}")
		print(f"--- Stdout ---\n{e.stdout}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"model": env_override.get("MODEL_NAME", DEFAULT_MODEL) if env_override else DEFAULT_MODEL,
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
		print(f"\nERROR: Script not found at {script_path}")

		_append_pipeline_rows([
			{
				"run_id": RUN_ID,
				"model": env_override.get("MODEL_NAME", DEFAULT_MODEL) if env_override else DEFAULT_MODEL,
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
	"""Execute the pipeline for each comparison model, running each RUNS_PER_MODEL times."""

	models = COMPARISON_MODELS if COMPARISON_MODELS else [DEFAULT_MODEL]
	total_runs = RUNS_PER_MODEL

	print("\n================ PIPELINE START ===============")
	print(f"Models to compare: {len(models)}")
	print(f"Runs per model: {total_runs}")
	print(f"Total pipeline executions: {len(models) * total_runs}")

	failures: list[str] = []

	for model_idx, model in enumerate(models, 1):
		print(f"\n{'='*50}")
		print(f"MODEL {model_idx}/{len(models)}: {model}")
		print(f"{'='*50}")

		_set_pipeline_run(model)
		TIMESTAMP_DIR.mkdir(parents=True, exist_ok=True)

		for run_num in range(1, total_runs + 1):
			print(f"\n--- Run {run_num}/{total_runs} for {model} ---")
			_clean_before_run()
			env_override = {"MODEL_NAME": model, "RUN_ID": RUN_ID, "RUN_COUNT": str(run_num)}
			try:
				print("\nStep 1/4: Generating task list")
				run_script("step1_task_generator", STEP_1_SCRIPT, cwd=BASE_DIR, env_override=env_override)

				print("\nStep 2/4: Generating code")
				run_script("step2_code_generator", STEP_2_SCRIPT, cwd=BASE_DIR, env_override=env_override)

				print("\nStep 3/4: Validator run")
				run_script("step3_validator", BASE_DIR / "validator.py", cwd=BASE_DIR, env_override=env_override)

				print("\nStep 4/4: Executing generated tasks")
				run_script("step4_scheduler", STEP_3_SCRIPT, cwd=BASE_DIR, env_override=env_override)

			except Exception as exc:
				failures.append(f"{model} run {run_num}: {exc}")
				print("\n Pipeline aborted for this run due to failure.")
				print(f"Reason: {exc}")
				continue

	print("\n================= PIPELINE END =================")
	print(f"Total models: {len(models)}, Runs per model: {total_runs}")
	if failures:
		print(f"\nFailures ({len(failures)}):")
		for f in failures:
			print(" -", f)
		sys.exit(1)
	else:
		print("\nAll runs completed successfully!")


if __name__ == "__main__":
	run_pipeline()

