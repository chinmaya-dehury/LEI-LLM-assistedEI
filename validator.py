"""
validator.py
-------------------
This module defines a function to validate generated Python task code
using an LLM in an LLM-assisted edge computing system.
The module sends generated task code, along with supporting data,
to an LLM for validation. The LLM checks syntax, logic, requirement compliance, and edge-case
handling before we persist the code to disk.

"""

import json
import os
import sys
from string import Template
from typing import Dict, List
import time

from openai import OpenAI

from config import DATA_TYPE, OPENAI_API_KEY
from prompts.get_validator import SYSTEM_PROMPT

# Ensure Unicode-safe console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

client = OpenAI(api_key=OPENAI_API_KEY)


def _load_context_for(datatype: str) -> Dict[str, object]:
    """Load sample data, metadata, and context for the given data type."""
    base = os.path.join("data", datatype)
    sample_path = os.path.join(base, "sample_data.csv")
    meta_path = os.path.join(base, "metadata.json")
    context_path = os.path.join(base, "context.txt")

    sample_data = ""
    metadata = {}
    context = ""

    if os.path.exists(sample_path):
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_data = f.read()
        except Exception:
            sample_data = ""

    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            metadata = {}

    if os.path.exists(context_path):
        try:
            with open(context_path, "r", encoding="utf-8") as f:
                context = f.read()
        except Exception:
            context = ""

    return {
        "sample_data": sample_data,
        "metadata": metadata,
        "context": context,
    }


def _build_user_prompt(task: Dict, assets: Dict[str, object]) -> str:
    """Construct the validator user prompt for a single task/code."""
    return f"""
Sample Data:
{assets['sample_data']}

Metadata:
{json.dumps(assets['metadata'], indent=2, ensure_ascii=False)}

Context:
{assets['context']}

Task Name: {task.get('task_name', 'UNKNOWN')}
Task Description: {task.get('description', 'N/A')}

Please review the following Python code and respond with JSON exactly in this format:
{{
  "task_name": "<same task name>",
  "is_valid": true/false,
  "error_message": "Explain any issues precisely (empty string if valid)."
}}

Code to validate:
\"\"\"python
{task.get('code', '')}
\"\"\"
""".strip()


def _call_llm(task: Dict, system_prompt: str, user_prompt: str) -> Dict:
    """Call the LLM validator for a single task and return parsed JSON result dict."""
    try:
        start = time.perf_counter()
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        elapsed = time.perf_counter() - start
        print(f"[Validator] {task.get('task_name')} check took {elapsed:.2f}s")
    except Exception as e:
        return {
            "task_name": task.get("task_name"),
            "is_valid": False,
            "error_message": f"LLM call failed: {e}",
        }

    raw = ""
    try:
        raw = response.choices[0].message.content if hasattr(response, "choices") else str(response)
    except Exception:
        raw = str(response)

    try:
        parsed = json.loads(raw)
    except Exception:
        # Try to recover JSON from within text (simple heuristic)
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end != -1:
                parsed = json.loads(raw[start:end])
            else:
                raise ValueError("no JSON")
        except Exception:
            return {
                "task_name": task.get("task_name"),
                "is_valid": False,
                "error_message": "Validator response was not valid JSON.",
            }

    return {
        "task_name": parsed.get("task_name", task.get("task_name")),
        "is_valid": bool(parsed.get("is_valid", False)),
        "error_message": parsed.get("error_message", "") or "",
    }


def _quick_static_checks(task: Dict) -> Dict:
    """Return {'ok': True} if passes; otherwise {'ok': False, 'error': msg}."""
    code = task.get("code", "") or ""
    # 1) basic syntax via ast.parse
    try:
        import ast
        ast.parse(code)
    except SyntaxError as e:
        return {"ok": False, "error": f"SyntaxError: {e}"}
    # 2) check for common typos/forbidden hardcoded folder names
    if "tiemstamp" in code:
        return {"ok": False, "error": "Found misspelling 'tiemstamp' instead of 'timestamp'."}
    if "data/environment" in code and task.get("data_type") and f"data/{task.get('data_type')}" not in code:
        return {"ok": False, "error": f"Code references data/environment but task.data_type={task.get('data_type')}."}
    # 3) optional: check for timestamp parsing or numeric coercion usage
    if "pd.to_datetime" not in code and "pd.to_numeric" not in code:
        # not necessarily fatal; return warning as non-blocking (decide policy)
        pass
    return {"ok": True}


def call_llm_for_validator(task_bundle: Dict) -> Dict[str, List[Dict]]:
    """
    Validate a batch of tasks.

    task_bundle: {"tasks": [ {"task_name":..., "description":..., "code":..., "data_type":...}, ... ]}
    Returns: {"tasks": [ {"task_name":..., "is_valid": bool, "error_message": "..."} , ... ]}
    """
    results: List[Dict] = []

    for task in task_bundle.get("tasks", []):
        if not task.get("task_name") or not task.get("code"):
            results.append(
                {
                    "task_name": task.get("task_name", "UNKNOWN"),
                    "is_valid": False,
                    "error_message": "Task missing name or code for validation.",
                }
            )
            continue

        datatype = task.get("data_type", DATA_TYPE)
        assets = _load_context_for(datatype)
        system_prompt = Template(SYSTEM_PROMPT).substitute(DATA_TYPE=datatype)
        user_prompt = _build_user_prompt(task, assets)

        pre = _quick_static_checks(task)
        if not pre['ok']:
            results.append({"task_name":task.get("task_name", "UNKNOWN"),"is_valid":False,"error_message":pre['error']}); continue

        result = _call_llm(task, system_prompt, user_prompt)
        results.append(result)

    return {"tasks": results}

