"""
validator.py
-------------------
Runs all generated task scripts (after step 2, before step 3).
If a task fails, logs the error, calls the LLM for fixes (up to 2 retries),
replaces the script on success, or moves it to failed/ when retries are exhausted.

Code updated: added FutureWarning/deprecation warning handling logic.
Modified on: 25-05-2026

"""

import json
import csv
import ast
import os
import sys
import subprocess
import time

from typing import Dict, List
import shutil
from datetime import datetime
import re
from pathlib import Path
import threading
import concurrent.futures

from config import DATA_TYPE, LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL, LLM_VAL_MODEL
from prompts.get_validated import SYSTEM_PROMPT
from resource_monitor import log_resource_metrics
from shared_utils import (
    sanitize_model_name,
    extract_first_json_object,
    get_environment_vars,
    setup_timing_paths,
    validate_data_type_exists,
    write_validator_detailed_row,
    IST,
)
from val_semantic import _validate_output_structure


# Placeholders for global variables populated in main()
client = None
_env = get_environment_vars()
RUN_ID = _env.get("RUN_ID", "complex_run")
RUN_COUNT = _env.get("RUN_COUNT", "1")
TIMESTAMP_PATH = None
STEP3_CSV = None
RESOURCE_CSV = None
SANITIZED_MODEL = sanitize_model_name(LLM_VAL_MODEL)
SCRIPT_START_TIME = None
SCRIPT_START_PERF = None

MAX_RETRIES = 2
CLIENT_TIMEOUT = 300
ENABLE_LLM_CORRECTION = True  # Set to True to enable LLM self-correction, False to fail immediately
csv_lock = threading.Lock()

DEFAULT_SCRIPTS_DIR = os.environ.get("LEI_TASKS_DIR", os.path.join("generated_tasks", DATA_TYPE))
DEFAULT_TASKS_FILE = os.path.join(DEFAULT_SCRIPTS_DIR, "tasks_list.json")
FALLBACK_TASKS_FILE = os.path.join(DEFAULT_SCRIPTS_DIR, "new_tasks.json")
ERROR_LOG_PATH = os.path.join(DEFAULT_SCRIPTS_DIR, "error.csv")
DEFAULT_VALIDATOR_LOG = os.path.join("validator", DATA_TYPE)
COMPLEX_TASKS_FILE = os.path.join("generated_tasks", "complex", "complex_tasks_list.json")
COMPLEX_SCRIPTS_DIR = os.path.join("generated_tasks", "complex")
COMPLEX_MISSING_DIR = os.path.join(COMPLEX_SCRIPTS_DIR, "missing")
COMPLEX_VALIDATOR_LOG = os.path.join("validator", "complex")


def _append_central_error_log(run_number: str, model: str, use_case: str, error_details: str) -> None:
    """Log validation and execution errors to a unified central CSV at results/all_errors.csv."""
    central_log_path = os.path.join("results", "all_errors.csv")
    os.makedirs(os.path.dirname(central_log_path), exist_ok=True)
    
    from shared_utils import sanitize_model_name
    short_model = sanitize_model_name(model)
    
    fieldnames = ["run_number", "model", "use_case", "error_details", "count"]
    err_clean = error_details.strip()
    
    with csv_lock:
        rows = []
        found = False
        if os.path.exists(central_log_path) and os.path.getsize(central_log_path) > 0:
            try:
                with open(central_log_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames and all(field in reader.fieldnames for field in fieldnames):
                        for row in reader:
                            rows.append(row)
            except Exception as e:
                print(f"[WARNING] Could not read existing central error CSV: {e}")
                
        for row in rows:
            if (row["run_number"] == str(run_number) and 
                row["model"] == short_model and 
                row["use_case"] == use_case and 
                row["error_details"].strip() == err_clean):
                row["count"] = str(int(row["count"]) + 1)
                found = True
                break
                
        if not found:
            rows.append({
                "run_number": str(run_number),
                "model": short_model,
                "use_case": use_case,
                "error_details": err_clean,
                "count": "1"
            })
            
        try:
            with open(central_log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            print(f"[WARNING] Could not write central error CSV: {e}")


def _append_error_log(task_name: str, exit_code: int, stderr: str, log_path: str = None) -> None:
    """Append or update runtime failure details in error.csv."""
    if log_path is None:
        log_path = ERROR_LOG_PATH
        
    try:
        _append_central_error_log(RUN_COUNT, LLM_VAL_MODEL, DATA_TYPE, stderr)
    except Exception as e:
        print(f"[WARNING] Failed to append error to central CSV: {e}")
    
    # Change extension from .txt to .csv if it still has .txt
    if log_path.endswith(".txt"):
        log_path = log_path[:-4] + ".csv"
        
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = datetime.now().isoformat()
    stderr_clean = stderr.strip()
    
    with csv_lock:
        rows = []
        found = False
        fieldnames = ["task_name", "exit_code", "error_message", "count", "last_timestamp"]
        
        if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
            try:
                with open(log_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames and all(field in reader.fieldnames for field in fieldnames):
                        for row in reader:
                            rows.append(row)
            except Exception as e:
                print(f"[WARNING] Could not read existing error CSV: {e}")
                
        for row in rows:
            if row["task_name"] == task_name and row["error_message"].strip() == stderr_clean:
                row["count"] = str(int(row["count"]) + 1)
                row["last_timestamp"] = timestamp
                row["exit_code"] = str(exit_code)
                found = True
                break
                
        if not found:
            rows.append({
                "task_name": task_name,
                "exit_code": str(exit_code),
                "error_message": stderr_clean,
                "count": "1",
                "last_timestamp": timestamp
            })
            
        try:
            with open(log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            print(f"[WARNING] Could not write error CSV: {e}")


def _load_context_for(datatype: str) -> Dict[str, object]:
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


def _normalize_domains(domains) -> List[str]:
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]
    if not isinstance(domains, list):
        return []
    return [str(d).strip() for d in domains if str(d).strip()]


def _load_complex_context_for(task_info: Dict[str, object]) -> Dict[str, object]:
    """Load merged context for complex tasks from their component domains."""
    domains = _normalize_domains(
        task_info.get("domains")
        or task_info.get("metadata", {}).get("domains")
        or []
    )

    sample_parts = []
    context_parts = []
    metadata_parts = {}

    for domain in domains:
        assets = _load_context_for(domain)
        if assets.get("sample_data"):
            sample_parts.append(f"# Domain: {domain}\n{assets['sample_data']}")
        if assets.get("context"):
            context_parts.append(f"# Domain: {domain}\n{assets['context']}")
        metadata_parts[domain] = assets.get("metadata", {})

    return {
        "sample_data": "\n\n".join(sample_parts),
        "metadata": {
            "domains": domains,
            "domain_metadata": metadata_parts,
            "task_name": task_info.get("task_name", ""),
            "description": task_info.get("description", ""),
            "business_value": task_info.get("business_value", ""),
        },
        "context": "\n\n".join(context_parts),
    }


def _safe_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def _load_complex_task_specs(complex_tasks_file: str) -> List[Dict[str, object]]:
    if not os.path.exists(complex_tasks_file):
        return []
    try:
        with open(complex_tasks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    return data.get("composite_tasks", []) or []


def _build_complex_validation_targets(complex_tasks_file: str, scripts_dir: str) -> List[Dict[str, object]]:
    """Create validation targets for complex executors and generated missing subtasks."""
    targets: List[Dict[str, object]] = []
    composite_tasks = _load_complex_task_specs(complex_tasks_file)

    for spec in composite_tasks:
        if not isinstance(spec, dict):
            continue
        task_name = str(spec.get("task_name", "")).strip()
        if not task_name:
            continue

        script_filename = f"{_safe_slug(task_name)}_executor.py"
        script_path = os.path.join(scripts_dir, script_filename)
        if not os.path.exists(script_path):
            continue

        targets.append({
            "script_path": script_path,
            "validation_kind": "composite_executor",
            "task_info": {
                "task_name": task_name,
                "description": spec.get("description", ""),
                "business_value": spec.get("business_value", ""),
                "data_type": "complex",
                "domains": spec.get("domains", []),
                "metadata": {
                    "domains": spec.get("domains", []),
                    "missing_capabilities": spec.get("missing_capabilities", []),
                },
                "script_filename": script_filename,
            },
            "scripts_dir": scripts_dir,
        })

    missing_dir = os.path.join(scripts_dir, "missing")
    if os.path.isdir(missing_dir):
        for entry in sorted(os.listdir(missing_dir)):
            if not entry.endswith(".py"):
                continue
            script_path = os.path.join(missing_dir, entry)
            if not os.path.isfile(script_path):
                continue

            stem = Path(entry).stem
            pretty_name = stem.replace("_", " ").strip() or stem
            targets.append({
                "script_path": script_path,
                "validation_kind": "generated_missing_subtask",
                "task_info": {
                    "task_name": f"{pretty_name} (generated fallback)",
                    "description": f"Auto-generated missing complex subtask: {pretty_name}",
                    "data_type": "complex",
                    "domains": ["complex"],
                    "metadata": {
                        "source": "generated_missing_complex_subtask",
                    },
                    "script_filename": entry,
                },
                "scripts_dir": missing_dir,
            })

    return targets


def _execute_task_script(script_path: str, timeout: int = 60) -> Dict[str, object]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    max_exec_retries = 3
    for attempt in range(max_exec_retries):
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            
            if "modulenotfounderror" in stderr.lower() or "no module named" in stderr.lower():
                # Extract missing module
                match = re.search(r"No module named ['\"]([^'\"]+)['\"]", stderr)
                missing_module = None
                if match:
                    missing_module = match.group(1).split('.')[0]
                else:
                    match_alt = re.search(r"No module named ([^\s]+)", stderr)
                    if match_alt:
                        missing_module = match_alt.group(1).split('.')[0]
                
                if missing_module:
                    # Map import names to pip package names if they differ
                    package_map = {
                        "sklearn": "scikit-learn",
                        "cv2": "opencv-python",
                        "yaml": "pyyaml",
                        "PIL": "pillow",
                        "bs4": "beautifulsoup4",
                        "skimage": "scikit-image",
                        "fitz": "pymupdf",
                        "docx": "python-docx",
                        "pptx": "python-pptx",
                        "dateutil": "python-dateutil",
                        "jwt": "pyjwt",
                        "dotenv": "python-dotenv",
                    }
                    pip_package = package_map.get(missing_module, missing_module)
                    print(f"[Dynamic Dependency - LEI] Installing missing package: {pip_package} (imported as {missing_module})...")
                    try:
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", pip_package],
                            check=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        # Append to LEI requirements.txt
                        req_path = "requirements.txt"
                        if os.path.exists(req_path):
                            with open(req_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            if pip_package not in content:
                                if content and not content.endswith('\n'):
                                    with open(req_path, "a", encoding="utf-8") as f:
                                        f.write("\n")
                                with open(req_path, "a", encoding="utf-8") as f:
                                    f.write(f"{pip_package}\n")
                                print(f"[Dynamic Dependency - LEI] Added {pip_package} to requirements.txt")
                        continue
                    except Exception as e:
                        print(f"[WARNING - LEI] Failed to install package {pip_package}: {e}")
            
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Script execution timed out after {timeout}s",
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Failed to execute script: {e}",
            }
    
    return {
        "exit_code": -1,
        "stdout": "",
        "stderr": "Module installation retry limit reached",
    }


def _normalize_code_string(code: str, data_type: str = None) -> str:
    """Convert JSON-escaped/code-fenced text into plain Python source and auto-repair paths/typos."""
    if not isinstance(code, str):
        return ""
    s = code.strip()
    
    # Strip markdown code blocks robustly
    if s.startswith("```"):
        s = re.sub(r"^```(?:python)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```$", "", s)
    elif "```python" in s:
        match = re.search(r"```python\s*(.+?)\s*```", s, flags=re.DOTALL | re.IGNORECASE)
        if match:
            s = match.group(1)
            
    # Remove literal backslash sequences that should be normal escapes
    s = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    s = s.replace("\\'", "'").replace('\\"', '"')
    
    # Auto-repair common boolean/null typos outside string literals/comments using token offsets
    import tokenize
    import io
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(s.encode('utf-8')).readline))
        replacements = {}
        for tok in tokens:
            if tok.type == tokenize.NAME and tok.string in {"true", "false", "null"}:
                line_num = tok.start[0]
                start_col = tok.start[1]
                end_col = tok.end[1]
                val = tok.string
                
                if line_num not in replacements:
                    replacements[line_num] = []
                replacements[line_num].append((start_col, end_col, val))
                
        lines = s.splitlines(keepends=True)
        for line_num, reps in replacements.items():
            line_idx = line_num - 1
            if line_idx >= len(lines):
                continue
            # Sort in reverse order of start_col so offsets remain valid during replacements
            reps.sort(key=lambda x: x[0], reverse=True)
            line_str = lines[line_idx]
            for start, end, val in reps:
                rep_val = "True" if val == "true" else ("False" if val == "false" else "None")
                line_str = line_str[:start] + rep_val + line_str[end:]
            lines[line_idx] = line_str
        s = "".join(lines)
    except Exception:
        # Fallback to simple regex if tokenization fails (e.g. invalid syntax)
        s = re.sub(r'\bfalse\b', 'False', s)
        s = re.sub(r'\btrue\b', 'True', s)
        s = re.sub(r'\bnull\b', 'None', s)

    # Resolve data_type dynamically if not provided
    if not data_type:
        try:
            from config import DATA_TYPE as config_dt
            data_type = os.environ.get("DATA_TYPE", config_dt)
        except Exception:
            data_type = "lab-data"  # fallback default
        
    # Inject robust path preamble
    path_preamble = f"""# Programmatic path resolution pre-injected for reliability
import os
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir
while _root_dir.name and not (_root_dir / "data").exists():
    _parent = _root_dir.parent
    if _parent == _root_dir:
        break
    _root_dir = _parent

DATA_FILE_PATH = os.path.join(_root_dir, "data", "{data_type}", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "{data_type}", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "{data_type}", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "{data_type}")
os.makedirs(OUTPUT_DIR, exist_ok=True)
"""
    
    # Apply regex path correction
    s = re.sub(
        r'read_csv\(\s*r?["\'][^"\']+["\']',
        r'read_csv(DATA_FILE_PATH',
        s
    )
    s = re.sub(
        r'open\(\s*r?["\'](?:[^"\']+\.(csv|txt)|path_to_your_file|your_file)["\']',
        r'open(DATA_FILE_PATH',
        s
    )
    
    # Replace open for json metadata files with METADATA_FILE_PATH
    s = re.sub(
        r'open\(\s*r?["\'][^"\']+\.json["\']',
        r'open(METADATA_FILE_PATH',
        s
    )
    
    # Replace literal output path variables or placeholders
    s = s.replace("{OUTPUT_DIR}", "OUTPUT_DIR").replace("{OUTPUT}", "OUTPUT_DIR")
    s = re.sub(
        r'["\']output/([^"\']+)["\']',
        r'os.path.join(OUTPUT_DIR, "\1")',
        s
    )
    
    # Handle missing imports
    imports_to_check = [
        ("pd.", "import pandas as pd"),
        ("pandas", "import pandas as pd"),
        ("np.", "import numpy as np"),
        ("numpy", "import numpy as np"),
        ("plt.", "import matplotlib.pyplot as plt"),
        ("pyplot", "import matplotlib.pyplot as plt"),
        ("sns.", "import seaborn as sns"),
        ("seaborn", "import seaborn as sns"),
        ("json.", "import json"),
        ("os.", "import os"),
        ("sys.", "import sys"),
        ("re.", "import re"),
        ("Path", "from pathlib import Path"),
        ("datetime", "from datetime import datetime"),
        ("math.", "import math"),
        ("PCA", "from sklearn.decomposition import PCA"),
        ("shutil", "import shutil"),
        ("csv.", "import csv"),
    ]

    missing_imports = []
    for usage, import_stmt in imports_to_check:
        if usage in s:
            import_pattern = import_stmt.replace("import ", r"import\s+").replace("from ", r"from\s+")
            if not re.search(import_pattern, s):
                if import_stmt not in missing_imports:
                    missing_imports.append(import_stmt)

    if missing_imports:
        imports_block = "\n".join(missing_imports) + "\n"
        s = imports_block + s

    # Inject the path_block if we used any path constants in our replacements
    if "DATA_FILE_PATH" in s or "METADATA_FILE_PATH" in s or "OUTPUT_DIR" in s:
        if "Programmatic path resolution" not in s:
            s = path_preamble + "\n" + s
            
    return s


def _validate_python_syntax(code: str) -> tuple[bool, str]:
    """Validate that a Python source string parses successfully."""
    if not isinstance(code, str) or not code.strip():
        return False, "Python source is empty"

    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        line_info = f"line {e.lineno}, column {e.offset}" if e.lineno is not None else "unknown location"
        message = e.msg or "Invalid Python syntax"
        return False, f"Syntax error at {line_info}: {message}"


def _output_is_only_warning(text: str) -> bool:
    """
    Returns True if the provided text (stdout or stderr) contains only
    warning-like messages (FutureWarning, DeprecationWarning, UserWarning, etc.)
    and no actual error patterns. Empty or missing text is considered warning-only.
    """
    if not text or not isinstance(text, str):
        return True  # No output means no warnings/errors

    lines = text.strip().split("\n")
    if not lines or all(not line.strip() for line in lines):
        return True  # Empty or whitespace-only

    # Patterns that indicate warnings (not errors)
    warning_patterns = [
        r"Warning:",
        r"FutureWarning:",
        r"DeprecationWarning:",
        r"UserWarning:",
        r"PendingDeprecationWarning:",
        r"RuntimeWarning:",
        r"SyntaxWarning:",
        r"ResourceWarning:",
        r"ImportWarning:",
        r"UnicodeWarning:",
        r"BytesWarning:",
        r"warnings\.warn",
        r"^\s*warnings\.filterwarnings",
        # Common warning file references
        r"site-packages.*Warning",
        r"lib.*Warning",
    ]

    # Patterns that indicate actual errors (not just warnings)
    error_patterns = [
        r"Error:",
        r"Exception:",
        r"Traceback \(most recent call last\):",
        r"^\s*File \".*\", line \d+",
        r"ModuleNotFoundError:",
        r"ImportError:",
        r"SyntaxError:",
        r"NameError:",
        r"TypeError:",
        r"ValueError:",
        r"KeyError:",
        r"IndexError:",
        r"AttributeError:",
        r"FileNotFoundError:",
        r"OSError:",
        r"IOError:",
        r"RuntimeError:",
        r"ZeroDivisionError:",
        r"AssertionError:",
    ]

    full_text = text.strip()

    # If any error pattern matches, it's not warning-only
    for pattern in error_patterns:
        if re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE):
            return False

    # If we get here, check if there's any content that doesn't look like a warning
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line matches any warning pattern
        is_warning_line = any(re.search(p, line, re.IGNORECASE) for p in warning_patterns)

        # Also accept lines that are part of warning stack traces (indented or file refs)
        is_context_line = (
            line.startswith(" ") or
            line.startswith("\t") or
            re.match(r"^\s*\^+\s*$", line) or
            re.match(r"^\s*~+\s*$", line) or
            "site-packages" in line or
            ".py:" in line
        )

        if not is_warning_line and not is_context_line:
            return False

    # If no error patterns matched, treat as warning-only
    return True


def _build_correction_prompt(task: Dict, runtime_error: str, exit_code: int, assets: Dict, validation_error: str = "") -> str:
    validation_section = ""
    if validation_error:
        validation_section = f"""
SEMANTIC VALIDATION ERROR:
{validation_error}

The output was valid JSON but failed semantic validation. Fix the code to produce output matching the expected schema.
"""
    
    # 1. Trim Sample Data: Keep only first 5 lines (or ~400 chars)
    sample_data = assets.get('sample_data', '')
    sample_data_lines = sample_data.strip().split('\n')
    trimmed_sample = "\n".join(sample_data_lines[:5])
    if len(sample_data_lines) > 5:
        trimmed_sample += "\n... [TRUNCATED] ..."

    # 2. Trim Metadata: Only keep the first 500 characters
    trimmed_metadata = json.dumps(assets.get('metadata', {}), indent=2, ensure_ascii=False)[:500]
    if len(json.dumps(assets.get('metadata', {}))) > 500:
        trimmed_metadata += "\n... [TRUNCATED] ..."

    # 3. Trim Context: Keep only first 500 characters
    trimmed_context = assets.get('context', '')[:500]
    if len(assets.get('context', '')) > 500:
        trimmed_context += "\n... [TRUNCATED] ..."

    # 4. Trim Runtime Error: Keep first 2 lines and last 15 lines of traceback
    trimmed_error = ""
    if runtime_error:
        err_lines = runtime_error.strip().split('\n')
        if len(err_lines) > 20:
            trimmed_error = "\n".join(err_lines[:2]) + "\n... [TRUNCATED] ...\n" + "\n".join(err_lines[-15:])
        else:
            trimmed_error = runtime_error

    return f"""
Sample Data:
{trimmed_sample}

Metadata:
{trimmed_metadata}

Context:
{trimmed_context}

Task Name: {task.get('task_name', 'UNKNOWN')}
Task Description: {task.get('description', 'N/A')}
Data Type: {task.get('data_type', DATA_TYPE)}

Metadata:
{json.dumps(task.get('metadata', {}), indent=2, ensure_ascii=False)[:500]}

RUNTIME ERROR (exit code {exit_code}):
{trimmed_error}
{validation_section}

ORIGINAL CODE THAT FAILED:
{task.get('code', '')}

Provide corrected code following the response format specified in the system prompt.
""".strip()


def _call_llm_chat(system_prompt: str, user_prompt: str) -> dict:
    global client
    if client is None:
        from openai import OpenAI
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=CLIENT_TIMEOUT)
    response = client.chat.completions.create(
        model=LLM_VAL_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    usage = getattr(response, "usage", None) or {}
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    else:
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0) or 0)

    content = ""
    if getattr(response, "choices", None):
        content = response.choices[0].message.content or ""

    return {
        "content": content,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "model": getattr(response, "model", LLM_VAL_MODEL),
        "raw": response,
    }


def _extract_json_from_text(text: str) -> dict | list | None:
    """
    Extract JSON (object or array) from text that may contain:
    - Code fences (```json ... ```
    - Natural language before/after JSON
    - Warnings or other output mixed in
    
    Returns parsed JSON (dict or list) or None if extraction fails.
    """
    if not text or not isinstance(text, str):
        return None

    s = text.strip()
    if not s:
        return None

    # 1. Strip code fences if present (```json ... ``` or ``` ... ```
    if "```" in s:
        # Find content between first ``` and last ```
        parts = s.split("```")
        for i, part in enumerate(parts):
            # Skip the language identifier line if present (e.g., "json\n{...}")
            candidate = part.strip()
            if candidate.startswith(("json", "python", "JSON")):
                candidate = candidate.split("\n", 1)[1].strip() if "\n" in candidate else ""
            
            if not candidate:
                continue
                
            # Try to parse this block
            try:
                if candidate.startswith("{"):
                    return json.loads(candidate)
                elif candidate.startswith("["):
                    return json.loads(candidate)
            except json.JSONDecodeError:
                pass
            
            # Try extracting JSON from within this block
            result = _try_extract_json_structure(candidate)
            if result is not None:
                return result

    # 2. Try direct parse
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 3. Try extracting JSON structure from the text
    return _try_extract_json_structure(s)


def _try_extract_json_structure(text: str) -> dict | list | None:
    """
    Try to find and parse a JSON object or array from text.
    Uses JSONDecoder.raw_decode to handle trailing content.
    """
    if not text:
        return None

    # Try to find JSON object
    obj_start = text.find("{")
    arr_start = text.find("[")

    # Determine which comes first
    if obj_start == -1 and arr_start == -1:
        return None

    # Try object first if it appears before array (or array not found)
    if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(text[obj_start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # Try array
    if arr_start != -1:
        try:
            decoder = json.JSONDecoder()
            arr, _ = decoder.raw_decode(text[arr_start:])
            if isinstance(arr, list):
                return arr
        except json.JSONDecodeError:
            pass

    # Fallback: try finding the last complete JSON object/array (for cases where warnings come first)
    # Find last { and matching }
    last_obj_end = text.rfind("}")
    if last_obj_end != -1:
        # Search backwards for matching {
        depth = 0
        for i in range(last_obj_end, -1, -1):
            if text[i] == "}":
                depth += 1
            elif text[i] == "{":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:last_obj_end + 1])
                    except json.JSONDecodeError:
                        break

    # Find last [ and matching ]
    last_arr_end = text.rfind("]")
    if last_arr_end != -1:
        depth = 0
        for i in range(last_arr_end, -1, -1):
            if text[i] == "]":
                depth += 1
            elif text[i] == "[":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i:last_arr_end + 1])
                    except json.JSONDecodeError:
                        break

    return None


def _parse_json_from_output(output: str) -> Dict | None:
    """
    Attempt to extract a JSON object from stdout even if warnings or extra text
    are present. Returns dict if successful, otherwise None.
    
    Accepts:
    - JSON object with task_name: {"task_name": "...", "result_summary": [...]}
    - JSON array (result_summary only): [{...}, {...}]
    - JSON with code fences or extra text around it
    """
    if not output:
        return None

    parsed = _extract_json_from_text(output)
    
    if parsed is None:
        return None

    # If it's already a dict with task_name, return as-is
    if isinstance(parsed, dict):
        return parsed

    # If it's a list (result_summary array), wrap it for compatibility
    if isinstance(parsed, list):
        return {"result_summary": parsed, "_array_output": True}


def _complex_payload_has_failure(json_output: Dict[str, object]) -> str:
    """Return a human-readable failure reason for complex executor payloads."""
    if not isinstance(json_output, dict):
        return ""

    top_status = str(json_output.get("status", "")).strip().lower()
    if top_status in {"partial_failure", "failed", "error"}:
        return f"Top-level status reported {top_status}"

    combined_analysis = json_output.get("combined_analysis")
    if isinstance(combined_analysis, dict):
        workflow_status = str(combined_analysis.get("workflow_status", "")).strip().lower()
        if workflow_status in {"partial_failure", "failed", "error"}:
            return f"Combined analysis reported {workflow_status}"

        summary_metrics = combined_analysis.get("summary_metrics")
        if isinstance(summary_metrics, dict):
            bad_metric_keys = [str(key) for key in summary_metrics.keys() if "none" in str(key).lower()]
            if bad_metric_keys:
                sample = ", ".join(bad_metric_keys[:3])
                return f"Combined analysis contains malformed metric keys: {sample}"

    subtask_results = json_output.get("subtask_results")
    if isinstance(subtask_results, dict):
        failed_subtasks = [
            str(task_id)
            for task_id, payload in subtask_results.items()
            if isinstance(payload, dict) and str(payload.get("status", "")).strip().lower() == "error"
        ]
        if failed_subtasks:
            sample = ", ".join(failed_subtasks[:3])
            return f"Subtasks failed at runtime: {sample}"

    return ""

    return None


def _extract_code_from_llm_response(raw: str) -> str:
    """
    Extract corrected Python code from LLM response.
    Handles responses that include code in:
    - JSON field "corrected_code"
    - Code fences ```python ... ```
    - Raw code mixed with explanation
    """
    if not raw or not isinstance(raw, str):
        return ""

    s = raw.strip()

    # 1. Try to parse as JSON and extract corrected_code field
    parsed = _extract_json_from_text(s)
    if isinstance(parsed, dict):
        code = parsed.get("corrected_code", "")
        if code and isinstance(code, str):
            return code.strip()

    # 2. Try to extract from Python code fences
    if "```python" in s.lower() or "```py" in s.lower():
        # Find python code block
        pattern = r"```(?:python|py)\s*\n(.*?)```"
        matches = re.findall(pattern, s, re.DOTALL | re.IGNORECASE)
        if matches:
            # Return the longest match (likely the full corrected code)
            return max(matches, key=len).strip()

    # 3. Try generic code fences
    if "```" in s:
        parts = s.split("```")
        code_blocks = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are inside fences
                # Skip language identifier
                lines = part.split("\n")
                if lines and lines[0].strip().lower() in ("python", "py", ""):
                    code_blocks.append("\n".join(lines[1:]).strip())
                elif lines and lines[0].strip().lower() in ("json", "yaml", "yml", "xml", "markdown", "md", "bash", "sh", "text", "txt", "javascript", "js", "html", "css"):
                    continue
                else:
                    code_blocks.append(part.strip())
        if code_blocks:
            # Return the longest code block
            return max(code_blocks, key=len)

    # 4. If it looks like Python code (has def/import/class), return as-is
    if any(keyword in s for keyword in ["import ", "def ", "class ", "from "]):
        return s

    return ""


def _call_llm_for_correction(task: Dict, runtime_error: str, exit_code: int, assets: Dict, attempt: int, validation_error: str = "", task_start_time = None, task_start_perf = None) -> Dict:
    datatype = task.get("data_type", DATA_TYPE)
    output_dir_str = os.environ.get("LEI_OUTPUT_DIR", os.path.join("output", datatype)).replace("\\", "/")
    system_prompt = SYSTEM_PROMPT.replace("{DATA_TYPE}", datatype).replace("{OUTPUT_DIR}", output_dir_str)
    user_prompt = _build_correction_prompt(task, runtime_error, exit_code, assets, validation_error)

    llm_start_time = datetime.now(IST).isoformat()
    llm_start_perf = time.perf_counter()

    start_time = task_start_time or SCRIPT_START_TIME or llm_start_time
    start_perf = task_start_perf or SCRIPT_START_PERF or llm_start_perf

    try:
        native = _call_llm_chat(system_prompt, user_prompt)
    except Exception as e:
        llm_end_perf = time.perf_counter()
        llm_end_time = datetime.now(IST).isoformat()
        llm_duration = llm_end_perf - llm_start_perf

        script_end_time = datetime.now(IST).isoformat()
        script_duration = time.perf_counter() - start_perf
        with csv_lock:
            write_validator_detailed_row(
                STEP3_CSV, "llm_call_failed", LLM_VAL_MODEL, RUN_COUNT,
                task.get("task_name", ""), "llm_error", str(attempt),
                start_time, script_end_time, script_duration,
                llm_start_time, llm_end_time, llm_duration, 0, 0, 0
            )
        print(f"[Validator] LLM call failed: {e}")
        return {
            "task_name": task.get("task_name"),
            "is_valid": False,
            "error_message": f"LLM call failed: {e}",
            "corrected_code": "",
        }

    llm_end_perf = time.perf_counter()
    llm_end_time = datetime.now(IST).isoformat()
    llm_duration = llm_end_perf - llm_start_perf

    prompt_tokens = int(native.get("prompt_tokens") or 0)
    completion_tokens = int(native.get("completion_tokens") or 0)
    total_tokens = prompt_tokens + completion_tokens

    raw = native.get("content") or ""

    with csv_lock:
        write_validator_detailed_row(
            STEP3_CSV, "llm_call", native.get("model") or LLM_VAL_MODEL, RUN_COUNT,
            task.get("task_name", ""), "correction_attempt", str(attempt),
            start_time, datetime.now(IST).isoformat(), time.perf_counter() - start_perf,
            llm_start_time, llm_end_time, llm_duration, prompt_tokens, completion_tokens, total_tokens
        )

    # Try to parse as JSON first
    parsed = _extract_json_from_text(raw)
    
    if isinstance(parsed, dict):
        # Got a proper JSON response
        corrected_code = parsed.get("corrected_code", "")
        if (corrected_code is None) or ("corrected_code" not in parsed):
            # Maybe the code is in a different field or needs extraction
            corrected_code = _extract_code_from_llm_response(raw)
        
        return {
            "task_name": parsed.get("task_name", task.get("task_name")),
            "is_valid": bool(parsed.get("is_valid", False)),
            "error_message": parsed.get("error_message", "") or "",
            "corrected_code": corrected_code or "",
        }

    # JSON parsing failed - try to extract code directly
    corrected_code = _extract_code_from_llm_response(raw)
    
    if corrected_code:
        return {
            "task_name": task.get("task_name"),
            "is_valid": True,  # Assume valid if we got code
            "error_message": "",
            "corrected_code": corrected_code,
        }

    return {
        "task_name": task.get("task_name"),
        "is_valid": False,
        "error_message": "LLM response did not contain valid JSON or extractable code.",
        "corrected_code": "",
    }


def prevalidate_task_script(script_path: str, task_info: Dict) -> Dict[str, object]:
    """Validate task code, metadata, and datatype before execution.

    This performs syntax and semantic validation without running the script.
    """
    task_name = task_info.get("task_name", Path(script_path).stem)
    datatype = task_info.get("data_type", DATA_TYPE)
    task_description = task_info.get("description", "")
    metadata = task_info.get("metadata", {})
    assets = _load_context_for(datatype)

    generated_code = ""
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            generated_code = f.read()
    except Exception as e:
        return {
            "task_name": task_name,
            "valid": False,
            "syntax_valid": False,
            "semantic_performed": False,
            "semantic_passed": False,
            "message": f"Could not read script: {e}",
        }

    syntax_valid, syntax_error = _validate_python_syntax(generated_code)
    if not syntax_valid:
        return {
            "task_name": task_name,
            "valid": False,
            "syntax_valid": False,
            "semantic_performed": False,
            "semantic_passed": False,
            "message": syntax_error,
        }

    json_for_validation = {"task_name": task_name, "result_summary": []}
    validated_output, validation_error, semantic_details = _validate_output_structure(
        json_for_validation,
        task_name,
        task_description,
        generated_code,
        assets.get("sample_data", ""),
        min_results=0,
    )

    return {
        "task_name": task_name,
        "valid": validated_output is not None,
        "syntax_valid": True,
        "semantic_performed": semantic_details.get("performed", False),
        "semantic_passed": semantic_details.get("passed", False),
        "message": validation_error or "OK",
        "datatype": datatype,
        "metadata": metadata,
    }


def validate_and_fix_task(script_path: str, task_info: Dict, scripts_dir: str) -> Dict:
    task_start_time = datetime.now(IST).isoformat()
    task_start_perf = time.perf_counter()

    task_name = task_info.get("task_name")
    datatype = task_info.get("data_type", DATA_TYPE)
    task_description = task_info.get("description", "")
    error_log_path = os.path.join(COMPLEX_SCRIPTS_DIR, "error.csv") if str(datatype).strip().lower() == "complex" else ERROR_LOG_PATH
    if str(datatype).strip().lower() == "complex":
        assets = _load_complex_context_for(task_info)
    else:
        assets = _load_context_for(datatype)
    
    # Read generated code for LLM-based validation
    generated_code = ""
    if os.path.exists(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                generated_code = f.read()
            
            # Programmatic Auto-Repair BEFORE syntax check and execution
            repaired_code = _normalize_code_string(generated_code, datatype)
            if repaired_code != generated_code:
                print(f"[Auto-Repair] Programmatically repaired paths/casing/imports in script: {os.path.basename(script_path)}")
                with open(script_path, "w", encoding="utf-8") as f_out:
                    f_out.write(repaired_code)
                generated_code = repaired_code
        except Exception as e:
            print(f"[Warning] Auto-repair failed for script {os.path.basename(script_path)}: {e}")

    syntax_valid, syntax_error = _validate_python_syntax(generated_code)
    if not syntax_valid:
        print(f"[ERROR] {task_name} failed syntax validation: {syntax_error}")
        _append_error_log(task_name, 1, syntax_error, error_log_path)

    print(f"\n[Validator] Testing {task_name}...")

    exec_result = {"exit_code": 1, "stdout": "", "stderr": syntax_error} if not syntax_valid else _execute_task_script(script_path)
    
    # 1. basic runtime errors, output status flags checks (same as AutoGen and LangGraph)
    stdout = exec_result.get("stdout", "") or ""
    stderr = exec_result.get("stderr", "") or ""
    s = (stdout + "\n" + stderr).lower()
    indicators = ["error", "exception", "traceback", "failed", "input file not found", "error:"]
    has_error = any(ind in s for ind in indicators)

    result_json = _parse_json_from_output(stdout)
    if result_json:
        try:
            status_val = str(result_json.get("status", "")).lower()
            if status_val in {"failed", "error"} or result_json.get("error"):
                has_error = True
            result = result_json.get("result_summary")
            if isinstance(result, dict):
                if str(result.get("status", "")).lower() in {"failed", "error"} or result.get("error"):
                    has_error = True
        except Exception:
            pass

    # Record if basic code execution passed
    code_passed = exec_result["exit_code"] == 0 and not has_error

    # Always perform semantic validation if we have task description or code or sample data
    # This validates code-description matching even if JSON output fails
    validated_output = None
    validation_error = None
    semantic_details = {"performed": False, "passed": True, "reasoning": "Semantic validation not performed."}
    
    if task_description or generated_code or assets.get("sample_data", ""):
        json_for_validation = result_json or {"task_name": task_name, "result_summary": []}
        validated_output, validation_error, semantic_details = _validate_output_structure(
            json_for_validation,
            task_name,
            task_description,
            generated_code,
            assets.get("sample_data", ""),
            min_results=0,
        )
        if validated_output is None:
            has_error = True

    # Complex payload checks (remain active for LEI complex executors check, but adjusted for equivalence)
    if exec_result["exit_code"] == 0 and not has_error:
        if result_json and str(datatype).strip().lower() == "complex":
            complex_failure = _complex_payload_has_failure(result_json)
            if complex_failure:
                print(f"[ERROR] {task_name} produced a complex payload that should not pass validation: {complex_failure}")
                _append_error_log(task_name, 0, complex_failure, error_log_path)
                has_error = True

    validator_passed = exec_result["exit_code"] == 0 and not has_error

    if validator_passed:
        print(f"[OK] {task_name} passed validation (runtime & semantic check)")
        with csv_lock:
            write_validator_detailed_row(
                STEP3_CSV, "validation", LLM_VAL_MODEL, RUN_COUNT, task_name, "passed", "0",
                task_start_time, datetime.now(IST).isoformat(), time.perf_counter() - task_start_perf,
                semantic_performed=semantic_details.get("performed", False),
                semantic_passed=semantic_details.get("passed", False),
                semantic_reasoning=semantic_details.get("reasoning", "")
            )
        return {
            "task_name": task_name,
            "status": "passed",
            "message": "Executed and validated successfully",
            "code_passed": code_passed,
            "validator_passed": True,
        }

    # If it fails, log the failure details
    _append_error_log(
        task_name,
        exec_result["exit_code"],
        f"Validation failed (exit {exec_result['exit_code']}).\nStdout:\n{stdout}\nStderr:\n{stderr}\nSemantic Error:\n{validation_error}",
        error_log_path,
    )
    print(f"[WARNING] {task_name} failed validation (exit {exec_result['exit_code']} or has_error=True)")

    # Fail immediately if LLM repair loop is disabled
    if not ENABLE_LLM_CORRECTION:
        with csv_lock:
            write_validator_detailed_row(
                STEP3_CSV, "validation", LLM_VAL_MODEL, RUN_COUNT, task_name, "failed", "0",
                task_start_time, datetime.now(IST).isoformat(), time.perf_counter() - task_start_perf,
                semantic_performed=semantic_details.get("performed", False),
                semantic_passed=semantic_details.get("passed", False),
                semantic_reasoning=validation_error or semantic_details.get("reasoning", "")
            )
        
        failed_dir = os.path.join(scripts_dir, "failed")
        os.makedirs(failed_dir, exist_ok=True)
        failed_path = os.path.join(failed_dir, os.path.basename(script_path))

        try:
            shutil.move(script_path, failed_path)
            print(f"[ERROR] {task_name} failed validation. Moved to failed/ (self-correction disabled)")
        except Exception as e:
            print(f"[ERROR] {task_name} failed and could not move to failed/: {e}")

        return {
            "task_name": task_name,
            "status": "failed",
            "message": "Execution failed (self-correction disabled for comparison)",
            "code_passed": code_passed,
            "validator_passed": False,
        }

    # Retry/correction logic (only reached if task failed validation above and ENABLE_LLM_CORRECTION is True)
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            original_code = f.read()
    except Exception as e:
        return {"task_name": task_name, "status": "failed", "message": f"Could not read script: {e}"}

    task_info = dict(task_info)
    task_info["code"] = original_code

    # Log initial attempt (attempt 0) with no LLM interaction
    with csv_lock:
        write_validator_detailed_row(
            STEP3_CSV, "initial_run", LLM_VAL_MODEL, RUN_COUNT, task_name, "initial_validation", "0",
            task_start_time, datetime.now(IST).isoformat(), time.perf_counter() - task_start_perf
        )

    # LLM-assisted repair loop
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"[Validator] Retry {attempt}/{MAX_RETRIES} for {task_name}...")

        # Determine validation error from previous attempt (if any)
        validation_error_msg = ""
        if exec_result["exit_code"] == 0:
            result_json = _parse_json_from_output(exec_result["stdout"])
            if result_json:
                # Perform semantic validation check to find exact errors
                val_out, val_err, _ = _validate_output_structure(
                    result_json,
                    task_name,
                    task_info.get("task_description", ""),
                    task_info.get("code", ""),
                    assets.get("sample_data", ""),
                    min_results=0,
                )
                if val_err:
                    validation_error_msg = val_err
                if val_out is not None and str(datatype).strip().lower() == "complex":
                    complex_failure = _complex_payload_has_failure(result_json)
                    if complex_failure:
                        validation_error_msg = complex_failure

        correction = _call_llm_for_correction(
            task_info,
            exec_result["stderr"] or exec_result["stdout"],
            exec_result["exit_code"],
            assets,
            attempt,
            validation_error_msg,
            task_start_time=task_start_time,
            task_start_perf=task_start_perf,
        )

        if not correction.get("corrected_code"):
            print(f"[ERROR] LLM could not provide correction: {correction.get('error_message')}")
            continue

        corrected_code = _normalize_code_string(correction["corrected_code"])
        temp_path = script_path + ".tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(corrected_code)
        except Exception as e:
            print(f"[ERROR] Failed to write corrected code: {e}")
            continue

        corrected_syntax_valid, corrected_syntax_error = _validate_python_syntax(corrected_code)
        if not corrected_syntax_valid:
            print(f"[ERROR] Corrected code failed syntax validation: {corrected_syntax_error}")
            _append_error_log(task_name, 1, corrected_syntax_error, error_log_path)
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            continue

        exec_result = _execute_task_script(temp_path)

        if exec_result["exit_code"] == 0:
            result_json = _parse_json_from_output(exec_result["stdout"])
            # Accept valid JSON output that also passes semantic validation
            if result_json:
                validated_output, validation_error, semantic_details = _validate_output_structure(
                    result_json,
                    task_name,
                    task_info.get("task_description", ""),
                    corrected_code,
                    assets.get("sample_data", ""),
                    min_results=0,
                )
                if validated_output is not None:
                    # Both JSON and semantic validation passed
                    shutil.move(temp_path, script_path)
                    # Log a 'passed' status timing row for this attempt
                    with csv_lock:
                        write_validator_detailed_row(
                            STEP3_CSV, "validation", LLM_VAL_MODEL, RUN_COUNT, task_name, "passed", str(attempt),
                            task_start_time, datetime.now(IST).isoformat(), time.perf_counter() - task_start_perf,
                            semantic_performed=semantic_details.get("performed", False),
                            semantic_passed=semantic_details.get("passed", False),
                            semantic_reasoning=semantic_details.get("reasoning", "")
                        )
                    print(f"[OK] {task_name} corrected and validated successfully")
                    return {"task_name": task_name, "status": "passed", "message": f"Fixed after {attempt} attempt(s)"}
                else:
                    # Semantic validation failed - log and continue to next retry
                    print(f"[WARNING] Corrected code has valid JSON but failed semantic validation: {validation_error}")
                    _append_error_log(task_name, 0, f"Semantic validation failed:\n{validation_error}", error_log_path)

        _append_error_log(task_name, exec_result["exit_code"], exec_result["stderr"] or exec_result["stdout"], error_log_path)
        task_info["code"] = corrected_code
        print(f"[WARNING] Corrected code still failed (exit {exec_result['exit_code']})")

        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

    failed_dir = os.path.join(scripts_dir, "failed")
    os.makedirs(failed_dir, exist_ok=True)
    failed_path = os.path.join(failed_dir, os.path.basename(script_path))

    try:
        shutil.move(script_path, failed_path)
        print(f"[ERROR] {task_name} failed after {MAX_RETRIES} retries. Moved to failed/")
    except Exception as e:
        print(f"[ERROR] {task_name} failed and could not move to failed/: {e}")

    return {
        "task_name": task_name,
        "status": "failed",
        "message": f"Failed after {MAX_RETRIES} correction attempts",
        "code_passed": code_passed,
        "validator_passed": False,
    }


def validate_complex_generated_tasks(complex_tasks_file: str, scripts_dir: str) -> Dict[str, object]:
    """Validate composite complex executors and generated missing subtasks."""
    print("\n" + "=" * 60)
    print("VALIDATING COMPLEX GENERATED TASKS")
    print("=" * 60)

    targets = _build_complex_validation_targets(complex_tasks_file, scripts_dir)
    results: List[Dict] = []

    composite_targets = sum(1 for target in targets if target.get("validation_kind") == "composite_executor")
    fallback_targets = sum(1 for target in targets if target.get("validation_kind") == "generated_missing_subtask")

    if not targets:
        print("[INFO] No complex validation targets found")
    else:
        print(
            f"[INFO] Validation scope: {composite_targets} composite executors + "
            f"{fallback_targets} generated fallback subtasks"
        )
    
    # Filter valid targets
    valid_targets = []
    for target in targets:
        script_path = target.get("script_path")
        if script_path and os.path.exists(script_path):
            valid_targets.append(target)

    if valid_targets:
        max_workers = min(len(valid_targets), 4)
        print(f"[INFO] Validating {len(valid_targets)} complex tasks in parallel using {max_workers} threads...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_target = {}
            for target in valid_targets:
                script_path = target.get("script_path")
                task_info = target.get("task_info", {})
                target_scripts_dir = target.get("scripts_dir", scripts_dir)
                
                print(f"[PROCESSING] {task_info.get('task_name', Path(script_path).stem)}")
                future_to_target[executor.submit(validate_and_fix_task, script_path, task_info, target_scripts_dir)] = target
                
            for future in concurrent.futures.as_completed(future_to_target):
                target = future_to_target[future]
                task_info = target.get("task_info", {})
                try:
                    result = future.result()
                except Exception as e:
                    task_name = task_info.get("task_name", "unknown")
                    print(f"[ERROR] Complex task {task_name} threw exception during validation: {e}")
                    result = {
                        "task_name": task_name,
                        "status": "failed",
                        "message": f"Complex validation execution error: {e}",
                    }
                result["validation_kind"] = target.get("validation_kind", "unknown")
                results.append(result)

    passed = sum(1 for r in results if r.get("status") == "passed")
    failed = sum(1 for r in results if r.get("status") == "failed")

    composite_passed = sum(
        1 for r in results if r.get("validation_kind") == "composite_executor" and r.get("status") == "passed"
    )
    composite_failed = sum(
        1 for r in results if r.get("validation_kind") == "composite_executor" and r.get("status") == "failed"
    )
    fallback_passed = sum(
        1 for r in results if r.get("validation_kind") == "generated_missing_subtask" and r.get("status") == "passed"
    )
    fallback_failed = sum(
        1 for r in results if r.get("validation_kind") == "generated_missing_subtask" and r.get("status") == "failed"
    )

    summary = {
        "run_count": RUN_COUNT,
        "model": LLM_VAL_MODEL,
        "tasks": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
        },
        "breakdown": {
            "composite_executors": {
                "total": composite_targets,
                "passed": composite_passed,
                "failed": composite_failed,
            },
            "generated_missing_subtasks": {
                "total": fallback_targets,
                "passed": fallback_passed,
                "failed": fallback_failed,
            },
        },
    }

    os.makedirs(COMPLEX_VALIDATOR_LOG, exist_ok=True)
    timestamp_str = RUN_ID.replace("lei_v3_bench_", "") if RUN_ID else ""
    individual_summary_path = os.path.join(
        COMPLEX_VALIDATOR_LOG,
        f"val_sum_{SANITIZED_MODEL}_{timestamp_str}_complex_run{RUN_COUNT}.json",
    )
    with open(individual_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[Validator] Complex summary saved to {individual_summary_path}")

    return summary


def validate_all_generated_tasks(tasks_file: str, scripts_dir: str) -> Dict[str, object]:
    print("\n" + "=" * 60)
    print("VALIDATING GENERATED TASK SCRIPTS")
    print("=" * 60)

    # Try primary tasks file, fallback if needed
    tasks_data = None
    actual_tasks_file = tasks_file
    try:
        with open(tasks_file, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)
    except Exception as e:
        print(f"[WARNING] Failed to load {tasks_file}: {e}")
        # Try fallback file if primary fails
        if tasks_file != FALLBACK_TASKS_FILE and os.path.exists(FALLBACK_TASKS_FILE):
            try:
                print(f"[INFO] Attempting fallback: {FALLBACK_TASKS_FILE}")
                with open(FALLBACK_TASKS_FILE, "r", encoding="utf-8") as f:
                    tasks_data = json.load(f)
                    actual_tasks_file = FALLBACK_TASKS_FILE
            except Exception as e2:
                print(f"[ERROR] Failed to load fallback tasks file: {e2}")
                return {"tasks": [], "run_count": RUN_COUNT, "model": LLM_VAL_MODEL}
        else:
            return {"tasks": [], "run_count": RUN_COUNT, "model": LLM_VAL_MODEL}
    
    if tasks_data is None:
        print(f"[ERROR] No tasks data loaded")
        return {"tasks": [], "run_count": RUN_COUNT, "model": LLM_VAL_MODEL}
    
    print(f"[INFO] Using tasks file: {actual_tasks_file}")

    results: List[Dict] = []
    tasks_to_validate = []
    
    for task in tasks_data.get("tasks", []):
        task_name = task.get("task_name")
        if not task_name:
            continue

        script_filename = task.get("script_filename")
        if script_filename:
            script_path = os.path.join(scripts_dir, script_filename)
        else:
            safe_name = str(task_name).replace(" ", "_").replace("-", "_").lower()
            script_path = os.path.join(scripts_dir, f"{safe_name}.py")

            if not os.path.exists(script_path):
                script_path = os.path.join(scripts_dir, f"{task_name}.py")

            if not os.path.exists(script_path):
                script_path = os.path.join(scripts_dir, f"{safe_name}_executor.py")

            if not os.path.exists(script_path):
                script_path = os.path.join(scripts_dir, f"{task_name}_executor.py")

        if not os.path.exists(script_path):
            print(f"[WARNING] Script not found: {script_path}")
            results.append({
                "task_name": task_name,
                "status": "failed",
                "message": "Script file not found",
            })
            continue

        tasks_to_validate.append((script_path, task))

    if tasks_to_validate:
        max_workers = min(len(tasks_to_validate), 4)
        print(f"[INFO] Validating {len(tasks_to_validate)} tasks in parallel using {max_workers} threads...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(validate_and_fix_task, script_path, task, scripts_dir): task
                for script_path, task in tasks_to_validate
            }
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    task_name = task.get("task_name", "unknown")
                    print(f"[ERROR] Task {task_name} threw exception during validation: {e}")
                    results.append({
                        "task_name": task_name,
                        "status": "failed",
                        "message": f"Validation execution error: {e}"
                    })

    passed = sum(1 for r in results if r.get("validator_passed"))
    failed = sum(1 for r in results if not r.get("validator_passed"))
    code_passed_count = sum(1 for r in results if r.get("code_passed"))
    validator_passed_count = sum(1 for r in results if r.get("validator_passed"))
    code_generated_count = len(results)

    print("\n" + "=" * 60)
    print(f"VALIDATION COMPLETE: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return {
        "run_count": RUN_COUNT,
        "model": LLM_VAL_MODEL,
        "tasks": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "code_generated": code_generated_count,
            "code_passed": code_passed_count,
            "validator_passed": validator_passed_count,
        },
    }


def main() -> int:
    global client, RUN_ID, RUN_COUNT, TIMESTAMP_PATH, STEP3_CSV, RESOURCE_CSV, SANITIZED_MODEL, SCRIPT_START_TIME, SCRIPT_START_PERF
    global DEFAULT_TASKS_FILE, FALLBACK_TASKS_FILE, DEFAULT_SCRIPTS_DIR, ERROR_LOG_PATH, DEFAULT_VALIDATOR_LOG
    global COMPLEX_TASKS_FILE, COMPLEX_SCRIPTS_DIR, COMPLEX_MISSING_DIR, COMPLEX_VALIDATOR_LOG

    # Windows-safe stdout/stderr
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    from openai import OpenAI
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=CLIENT_TIMEOUT)

    # Validate that the DATA_TYPE folder exists with required files
    validate_data_type_exists(DATA_TYPE)

    # Per-run CSV path with model name and run ID (step3 = validator)
    env_vars = get_environment_vars()
    RUN_ID = env_vars["RUN_ID"]
    RUN_COUNT = env_vars["RUN_COUNT"]
    timing_paths = setup_timing_paths(DATA_TYPE, "step3", LLM_VAL_MODEL)
    TIMESTAMP_PATH = timing_paths["TIMESTAMP_PATH"]
    STEP3_CSV = timing_paths["STEP_CSV"]
    RESOURCE_CSV = timing_paths["RESOURCE_CSV"]
    SANITIZED_MODEL = sanitize_model_name(LLM_VAL_MODEL)

    DEFAULT_SCRIPTS_DIR = os.environ.get("LEI_TASKS_DIR", os.path.join("generated_tasks", DATA_TYPE))
    DEFAULT_TASKS_FILE = os.path.join(DEFAULT_SCRIPTS_DIR, "tasks_list.json")
    FALLBACK_TASKS_FILE = os.path.join(DEFAULT_SCRIPTS_DIR, "new_tasks.json")
    ERROR_LOG_PATH = os.path.join(DEFAULT_SCRIPTS_DIR, "error.csv")
    DEFAULT_VALIDATOR_LOG = os.path.join("validator", DATA_TYPE)
    COMPLEX_TASKS_FILE = os.path.join("generated_tasks", "complex", "complex_tasks_list.json")
    COMPLEX_SCRIPTS_DIR = os.path.join("generated_tasks", "complex")
    COMPLEX_MISSING_DIR = os.path.join(COMPLEX_SCRIPTS_DIR, "missing")
    COMPLEX_VALIDATOR_LOG = os.path.join("validator", "complex")

    # Log resource metrics at start
    log_resource_metrics(RESOURCE_CSV, "step3_validator", "start", model_name=LLM_VAL_MODEL, run_count=RUN_COUNT)

    # Script-level timing
    SCRIPT_START_TIME = datetime.now(IST).isoformat()
    SCRIPT_START_PERF = time.perf_counter()

    os.makedirs(DEFAULT_SCRIPTS_DIR, exist_ok=True)

    summary = validate_all_generated_tasks(DEFAULT_TASKS_FILE, DEFAULT_SCRIPTS_DIR)

    if os.path.exists(COMPLEX_TASKS_FILE) or os.path.isdir(COMPLEX_MISSING_DIR):
        validate_complex_generated_tasks(COMPLEX_TASKS_FILE, COMPLEX_SCRIPTS_DIR)

    # Ensure validator log directory exists
    os.makedirs(DEFAULT_VALIDATOR_LOG, exist_ok=True)
    
    # Save individual run summary with model name and RUN_COUNT in filename
    timestamp_str = RUN_ID.replace("lei_v3_bench_", "") if RUN_ID else ""
    individual_summary_path = os.path.join(DEFAULT_VALIDATOR_LOG, f"val_sum_{SANITIZED_MODEL}_{timestamp_str}_run{RUN_COUNT}.json")
    with open(individual_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[Validator] Individual run summary saved to {individual_summary_path}")
    
    # Accumulate results in master summary file (appends across all runs)
    master_summary_path = os.path.join(DEFAULT_VALIDATOR_LOG, f"val_sum_{SANITIZED_MODEL}_{timestamp_str}_all_runs.json")
    all_runs_data = {}
    
    # Load existing master summary if it exists
    if os.path.exists(master_summary_path):
        try:
            with open(master_summary_path, "r", encoding="utf-8") as f:
                all_runs_data = json.load(f)
        except Exception:
            all_runs_data = {"run_count": RUN_COUNT, "model": LLM_VAL_MODEL, "runs": {}}
    else:
        all_runs_data = {"run_count": RUN_COUNT, "model": LLM_VAL_MODEL, "runs": {}}
    
    # Add current run's results
    all_runs_data["run_count"] = RUN_COUNT  # Update to latest run count
    all_runs_data["model"] = LLM_VAL_MODEL
    if "runs" not in all_runs_data:
        all_runs_data["runs"] = {}
    all_runs_data["runs"][str(RUN_COUNT)] = summary.get("tasks", [])
    
    # Update overall summary with aggregate counts
    total_tasks = 0
    total_passed = 0
    total_failed = 0
    for run_tasks in all_runs_data.get("runs", {}).values():
        total_tasks += len(run_tasks)
        total_passed += sum(1 for t in run_tasks if t.get("status") == "passed")
        total_failed += sum(1 for t in run_tasks if t.get("status") == "failed")
    
    all_runs_data["summary"] = {
        "total_tasks": total_tasks,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_runs": len(all_runs_data.get("runs", {}))
    }
    
    # Save master summary
    with open(master_summary_path, "w", encoding="utf-8") as f:
        json.dump(all_runs_data, f, ensure_ascii=False, indent=2)
    print(f"[Validator] Master summary saved to {master_summary_path}")

    # Always add a run-level record for this validator execution
    with csv_lock:
        write_validator_detailed_row(
            STEP3_CSV, "validator_run", LLM_VAL_MODEL, RUN_COUNT, "", "execution_complete", "",
            SCRIPT_START_TIME, datetime.now(IST).isoformat(), time.perf_counter() - SCRIPT_START_PERF
        )

    # Log resource metrics at end
    log_resource_metrics(RESOURCE_CSV, "step3_validator", "end", model_name=LLM_VAL_MODEL, run_count=RUN_COUNT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

