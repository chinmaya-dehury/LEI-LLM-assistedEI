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

import subprocess
import sys
from pathlib import Path
from typing import Optional


# === Script Locations ===
BASE_DIR = Path(__file__).parent.resolve()
STEP_1_SCRIPT = BASE_DIR / "llm_orchestrator_adaptive.py"
STEP_2_SCRIPT = BASE_DIR / "task_code_generator_updated.py"
STEP_3_SCRIPT = BASE_DIR / "edge_scheduler_updated.py"


def run_script(script_path: Path, cwd: Optional[Path] = None) -> None:
	"""Execute a Python script using the current interpreter."""

	if not script_path.exists():
		raise FileNotFoundError(f"Script not found: {script_path}")

	command = [sys.executable, str(script_path)]
	run_cwd = cwd if cwd else script_path.parent

	print(f"\n Starting: {script_path.relative_to(BASE_DIR)}")
	print(f"   Interpreter: {sys.executable}")
	print(f"   Working Dir: {run_cwd}")

	try:
		result = subprocess.run(
			command,
			cwd=run_cwd,
			capture_output=True,
			text=True,
			check=True,
		)
	except subprocess.CalledProcessError as err:
		print(f"\n {script_path.name} failed with exit code {err.returncode}")
		if err.stdout:
			print("--- stdout ---")
			print(err.stdout)
		if err.stderr:
			print("--- stderr ---")
			print(err.stderr)
		raise

	stdout = (result.stdout or "").strip()
	if stdout:
		preview = stdout if len(stdout) < 400 else stdout[:400] + "..."
		print("Output snippet:")
		print(preview)
	else:
		print("Completed with no stdout")


def run_pipeline() -> None:
	"""Execute the three-stage pipeline sequentially."""

	print("\n================ PIPELINE START ===============")
	try:
		print("\nStep 1/3: Generating task list via llm_orchestrator_adaptive.py")
		run_script(STEP_1_SCRIPT)

		print("\nStep 2/3: Generating code via task_code_generator_update.py")
		run_script(STEP_2_SCRIPT)

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


# Following problems need to resolved:
# 1. The generated task code files have data type = "environment" instead of "temp_humidity" for which
# the generated code is not working properly.
# Instead of searching raw_data in temp_humidity folder, it is searching in environment folder.
# 2. The validator may be used after all the code is generated to validate the code before passing to edge_scheduler_updated.py.
# Maybe we can add the datatype parameter in .json file.