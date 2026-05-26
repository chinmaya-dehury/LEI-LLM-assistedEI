"""
Orchestrator for complex task synthesis workflow.
Runs: LLM generation -> Composite task generation -> Executor script generation.
"""

import sys
import json
from pathlib import Path

# Import components (relative imports for module execution)
# Note: LLM client import is done lazily to avoid requiring OpenAI at module import time
from .composite_task_generator import CompositeTaskGenerator
from .task_analyzer import TaskAnalyzer
from .dependency_resolver import DependencyResolver
from .workflow_executor_generator import generate_workflow_executor


def run_complex_task_synthesis_workflow(skip_llm_generation=False):
    """Execute the complete complex task synthesis workflow.
    
    Args:
        skip_llm_generation: If True, skip LLM generation and use existing composite_tasks_list.json.
                           Useful for regenerating workflows from already-generated tasks.
    """
    
    BASE_DIR = Path(__file__).parent.parent
    COMPOSITE_TASKS_PATH = BASE_DIR / "generated_tasks" / "complex" / "complex_tasks_list.json"
    
    # Step 1: Generate complex task specifications using LLM (optional)
    if not skip_llm_generation:
        print("\n" + "=" * 80)
        print("STEP 1: LLM-DRIVEN COMPLEX TASK GENERATION")
        print("=" * 80)
        try:
            # Import lazily to avoid import-time dependency on OpenAI package
            from .complex_task_generator_llm import generate_complex_tasks_llm
            generate_complex_tasks_llm()
        except Exception as e:
            print(f"[WARNING] LLM generation skipped: {e}")
    else:
        print("\n" + "=" * 80)
        print("STEP 1: SKIPPED (using existing composite_tasks_list.json)")
        print("=" * 80)
    
    # Step 2: Load generated complex tasks and create composite/workflow definitions
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
    
    # Initialize synthesis components
    try:
        analyzer = TaskAnalyzer(generated_tasks_dir=str(BASE_DIR / "generated_tasks"))
        resolver = DependencyResolver(analyzer)
        generator = CompositeTaskGenerator(resolver)
    except Exception as e:
        print(f"[ERROR] Failed to initialize components: {e}")
        return
    
    # Process each generated composite task spec
    processed = 0
    for spec in composite_tasks_specs:
        task_name = spec.get("task_name", "Unknown")
        print(f"\n[PROCESSING] {task_name}")
        
        try:
            # Generate composite task
            composite_task = generator.generate_composite_task(spec)
            generator.print_composite_task_details(composite_task)
            
            # Generate executable Python script for this workflow
            executor_script = generate_workflow_executor(composite_task, 
                                                        output_dir=str(BASE_DIR / "generated_tasks" / "complex"))
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
    import sys
    
    # Usage:
    # python -m complex_task_synthesis.runner          # Full workflow: LLM generation + workflow creation
    # python -m complex_task_synthesis.runner --skip   # Skip LLM, regenerate workflows from existing tasks
    
    skip_generation = "--skip" in sys.argv or "--skip-llm" in sys.argv
    run_complex_task_synthesis_workflow(skip_llm_generation=skip_generation)
