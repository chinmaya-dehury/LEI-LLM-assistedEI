"""
Complex-task validation entrypoint.

Provides a dedicated module for complex-task target discovery and validation
while reusing the shared validator engine for syntax, execution, semantic
checks, and retry/fix behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from validator import (  # noqa: E402
    COMPLEX_SCRIPTS_DIR,
    COMPLEX_TASKS_FILE,
    RUN_COUNT,
    DEFAULT_MODEL,
    COMPLEX_VALIDATOR_LOG,
    _build_complex_validation_targets,
    _load_complex_context_for,
    _load_complex_task_specs,
    validate_and_fix_task,
    validate_complex_generated_tasks,
)


def run_complex_validation() -> Dict[str, Any]:
    """Run complex-task validation in execution-first order.

    Each target is executed first, then the shared validator performs semantic
    validation by calling the LLM on the produced output.
    """
    return validate_complex_generated_tasks(COMPLEX_TASKS_FILE, COMPLEX_SCRIPTS_DIR)


def build_complex_validation_targets() -> list[dict[str, object]]:
    """Expose complex validation target discovery for callers that need it."""
    return _build_complex_validation_targets(COMPLEX_TASKS_FILE, COMPLEX_SCRIPTS_DIR)


def load_complex_task_specs() -> list[dict[str, object]]:
    """Expose the raw complex task specs used by validation."""
    return _load_complex_task_specs(COMPLEX_TASKS_FILE)


def validate_complex_generated_tasks_entry() -> Dict[str, object]:
    """Run the complex validation flow directly from this module.

    The order is explicit here: execute each script first, then pass the
    runtime output into the shared semantic validator, which uses the LLM to
    check schema and code-description alignment.
    """
    targets = build_complex_validation_targets()
    results: list[Dict[str, object]] = []

    for target in targets:
        script_path = target.get("script_path")
        task_info = target.get("task_info", {})
        target_scripts_dir = target.get("scripts_dir", COMPLEX_SCRIPTS_DIR)

        if not script_path:
            continue

        # The shared validator runs the script first, then performs semantic
        # validation via the LLM on the captured output.
        result = validate_and_fix_task(script_path, task_info, target_scripts_dir)
        results.append(result)

    passed = sum(1 for item in results if item.get("status") == "passed")
    failed = sum(1 for item in results if item.get("status") == "failed")

    summary = {
        "run_count": RUN_COUNT,
        "model": DEFAULT_MODEL,
        "tasks": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
        },
    }

    return summary


def main() -> None:
    summary = validate_complex_generated_tasks_entry()
    print(
        f"[OK] Complex validation complete: "
        f"{summary.get('summary', {}).get('passed', 0)} passed, "
        f"{summary.get('summary', {}).get('failed', 0)} failed"
    )


if __name__ == "__main__":
    main()


__all__ = [
    "build_complex_validation_targets",
    "load_complex_task_specs",
    "run_complex_validation",
    "validate_complex_generated_tasks_entry",
    "main",
]