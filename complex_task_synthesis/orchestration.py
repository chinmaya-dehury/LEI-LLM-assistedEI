"""
Orchestration module for complex task synthesis.

Coordinates LLM generation, composite task generation, and workflow creation.
"""

import sys
import json
from pathlib import Path

try:
    from .analysis import TaskAnalyzer, DependencyResolver
    from .generation import CompositeTaskGenerator, generate_workflow_executor
except ImportError:
    from analysis import TaskAnalyzer, DependencyResolver
    from generation import CompositeTaskGenerator, generate_workflow_executor


def run_complex_task_synthesis_workflow(skip_llm_generation=False):
    """Execute the complete complex task synthesis workflow.

    Args:
        skip_llm_generation: If True, skip LLM generation and use existing composite_tasks_list.json.
                           Useful for regenerating workflows from already-generated tasks.
    """

    BASE_DIR = Path(__file__).parent.parent
    COMPOSITE_TASKS_PATH = BASE_DIR / "generated_tasks" / "complex" / "complex_tasks_list.json"

    if not skip_llm_generation:
        print("\n" + "=" * 80)
        print("STEP 1: LLM-DRIVEN COMPLEX TASK GENERATION")
        print("=" * 80)
        try:
            try:
                from .generation import generate_complex_tasks_llm
            except ImportError:
                from generation import generate_complex_tasks_llm

            generation_result = generate_complex_tasks_llm()
            if not generation_result:
                print("[INFO] No new composite tasks were generated; skipping workflow creation.")
                return
        except Exception as e:
            print(f"[WARNING] LLM generation skipped: {e}")
            return
    else:
        print("\n" + "=" * 80)
        print("STEP 1: SKIPPED (using existing composite_tasks_list.json)")
        print("=" * 80)

    print("\n" + "=" * 80)
    print("STEP 2: COMPOSITE TASK ANALYSIS AND WORKFLOW CREATION")
    print("=" * 80)

    if not COMPOSITE_TASKS_PATH.exists():
        print("[INFO] No composite tasks found at", COMPOSITE_TASKS_PATH)
        return

    try:
        with open(COMPOSITE_TASKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            composite_tasks_specs = data.get("composite_tasks", [])
    except Exception as e:
        print(f"[ERROR] Failed to load composite tasks: {e}")
        return

    if not composite_tasks_specs:
        print("[INFO] No composite task specs to process")
        return

    print(f"[OK] Loaded {len(composite_tasks_specs)} composite task specifications")

    try:
        analyzer = TaskAnalyzer(generated_tasks_dir=str(BASE_DIR / "generated_tasks"))
        resolver = DependencyResolver(analyzer)
        generator = CompositeTaskGenerator(resolver)
    except Exception as e:
        print(f"[ERROR] Failed to initialize components: {e}")
        return

    processed = 0
    for spec in composite_tasks_specs:
        task_name = spec.get("task_name", "Unknown")
        print(f"\n[PROCESSING] {task_name}")

        try:
            composite_task = generator.generate_composite_task(spec)
            generator.print_composite_task_details(composite_task)

            executor_script = generate_workflow_executor(
                composite_task,
                output_dir=str(BASE_DIR / "generated_tasks" / "complex"),
            )
            if executor_script:
                print(f"[OK] {task_name} executor script generated: {executor_script}")

            processed += 1
            print(f"[OK] {task_name} processing complete")

        except Exception as e:
            print(f"[ERROR] Failed to process {task_name}: {e}")

    print("\n" + "=" * 80)
    print("COMPLEX TASK SYNTHESIS WORKFLOW COMPLETE")
    print("=" * 80)
    print(f"Processed: {processed}/{len(composite_tasks_specs)} composite tasks")
    print(f"\nOUTPUTS:")
    print(f"  - Composite task specs: generated_tasks/complex/complex_tasks_list.json")
    print(f"  - Executable scripts: generated_tasks/complex/*_executor.py")
    print(f"\nEXECUTE A COMPLEX TASK:")
    print(f"  python run_complex_task.py --list")
    print(f"  python run_complex_task.py TASK_NAME")
    print()


if __name__ == "__main__":
    skip_generation = "--skip" in sys.argv or "--skip-llm" in sys.argv
    run_complex_task_synthesis_workflow(skip_llm_generation=skip_generation)


__all__ = ["run_complex_task_synthesis_workflow"]
