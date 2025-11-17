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


# === Script Locations ===
BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "llm_orchestrator_adaptive_resource.py"
STEP_2_SCRIPT = BASE_DIR / "task_code_generator.py"
STEP_3_SCRIPT = BASE_DIR / "scheduler" / "edge_scheduler_sequential.py"


def run_script(script_path: Path, cwd: Optional[Path] = None) -> None:
	"""Execute a Python script using the current interpreter."""

	command = [sys.executable, script_path]

	# Prepare environment forcing UTF-8 for child Python process output
	env = os.environ.copy()
	env["PYTHONIOENCODING"] = "utf-8"

	try:
		print(f"\n🚀 Starting: {script_path} (CWD: {cwd if cwd else os.getcwd()})")
		start = time.perf_counter()

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

		elapsed = time.perf_counter() - start
		print(f"✅ Success. ({elapsed:.2f}s) Output Snippet:\n{result.stdout[:200]}...") 
		return True

	except subprocess.CalledProcessError as e:
		print(f"\n❌ ERROR: {script_path} failed (exit {e.returncode}).")
		print(f"--- Stderr ---\n{e.stderr}")
		print(f"--- Stdout ---\n{e.stdout}")
		raise
	except FileNotFoundError:
		print(f"\n❌ ERROR: Script not found at {script_path}")
		raise


def run_pipeline() -> None:
	"""Execute the three-stage pipeline sequentially."""

	print("\n================ PIPELINE START ===============")
	try:
		print("\nStep 1/3: Generating task list via llm_orchestrator_adaptive_resource.py")
		run_script(STEP_1_SCRIPT)

		print("\nStep 2/3: Generating code via task_code_generator.py")
		run_script(STEP_2_SCRIPT)

		print("\nIntermediate Step: Validator run now\n");
		run_script(BASE_DIR / "validator.py")

		print("\nStep 3/3: Executing generated tasks via edge_scheduler_sequential.py")
		run_script(STEP_3_SCRIPT, cwd=BASE_DIR)

	except Exception as exc:
		print("\n Pipeline aborted due to failure.")
		print(f"Reason: {exc}")
		sys.exit(1)

	print("\n Pipeline completed successfully.")
	print("================= PIPELINE END =================\n")


if __name__ == "__main__":
	run_pipeline()

