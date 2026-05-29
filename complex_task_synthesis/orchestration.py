"""
Orchestration module for complex task synthesis.

Coordinates LLM generation, composite task generation, and workflow creation.
"""

import sys
import json
from pathlib import Path

from .analysis import TaskAnalyzer, DependencyResolver
from .generation import CompositeTaskGenerator, generate_workflow_executor
from .val_complex import run_complex_validation


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
            # import generation module and call function only if available
            from importlib import import_module
            gen_mod = import_module('.generation', package='complex_task_synthesis')
            gen_fn = getattr(gen_mod, 'generate_complex_tasks_llm', None)
            if gen_fn is None:
                print("[WARNING] LLM generation skipped: 'generate_complex_tasks_llm' not found in generation module")
                return

            try:
                generation_result = gen_fn()
                if not generation_result:
                    print("[INFO] No new composite tasks were generated; skipping workflow creation.")
                    return
            except Exception as e:
                print(f"[WARNING] LLM generation aborted: {e}")
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
    print("STEP 3: COMPLEX TASK VALIDATION")
    print("=" * 80)
    try:
        validation_summary = run_complex_validation()
        print(
            f"[OK] Complex validation complete: "
            f"{validation_summary.get('summary', {}).get('passed', 0)} passed, "
            f"{validation_summary.get('summary', {}).get('failed', 0)} failed"
        )
    except Exception as e:
        print(f"[ERROR] Complex validation failed: {e}")

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
