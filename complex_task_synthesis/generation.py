"""
Generation module for complex task synthesis.

Combines composite task generation, workflow executor generation,
and LLM-driven composite task generation helpers.
"""

import os
import sys
import json
import time
import ast
from itertools import combinations
from pathlib import Path
from datetime import datetime, timedelta
from string import Template
from typing import Dict, List, Any

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from shared_utils import IST, extract_first_json_object, extract_first_json_value, get_environment_vars, setup_timing_paths, sanitize_model_name
from config import LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL


class CompositeTaskGenerator:
    """Generates complex composite tasks from basic tasks."""

    def __init__(self, dependency_resolver, config: Dict = None):
        self.resolver = dependency_resolver
        self.config = config or {}
        self.generated_tasks = []

    def generate_composite_task(self, task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a composite task based on specification."""
        subtasks_info = self._analyze_subtasks(task_definition["subtasks"])
        execution_order = self.resolver.topological_sort_tasks(subtasks_info["subtasks"])
        data_flow = self._build_data_flow(subtasks_info["subtasks"], execution_order)

        composite_task = {
            "task_name": task_definition["task_name"],
            "task_type": "composite",
            "description": task_definition["description"],
            "domains": list(set(t["domain"] for t in subtasks_info["subtasks"])),
            "subtasks": subtasks_info["subtasks"],
            "execution_order": execution_order,
            "data_flow": data_flow,
            "output_schema": task_definition.get("output_schema", {}),
            "summary": {
                "total_subtasks": len(subtasks_info["subtasks"]),
                "available": subtasks_info["available_count"],
                "pending_generation": subtasks_info["pending_count"],
                "missing": subtasks_info["missing_count"],
            },
            "complexity_score": self._calculate_complexity(subtasks_info["subtasks"]),
            "generated_at": datetime.now().isoformat(),
            "generation_metadata": {
                "generator": "CompositeTaskGenerator v1.0",
                "algorithm": "dependency_based_composition",
                "confidence": self._calculate_confidence(subtasks_info),
            }
        }

        self.generated_tasks.append(composite_task)
        return composite_task

    def _analyze_subtasks(self, subtasks: List[Dict]) -> Dict[str, Any]:
        """Analyze availability of subtasks."""
        analyzer = self.resolver.analyzer
        analysis = {
            "subtasks": subtasks,
            "available_count": 0,
            "pending_count": 0,
            "missing_count": 0,
            "details": [],
        }

        for index, subtask in enumerate(subtasks):
            domain = subtask["domain"]
            task_id = subtask["task_id"]

            domain_info = analyzer.analyze_domain_tasks(domain)

            if task_id in domain_info["tasks"]:
                subtask["status"] = "available"
                analysis["available_count"] += 1
                analysis["details"].append({
                    "task": task_id,
                    "status": "available",
                    "file_path": domain_info["tasks"][task_id]["file_path"],
                })
            else:
                if task_id == "needs_generation" or not task_id.strip():
                    base_name = subtask.get("subtask_name", "generated_subtask")
                    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in base_name).strip("_") or "generated_subtask"
                    task_id = f"{slug}_{index + 1}"
                    subtask["original_task_id"] = subtask.get("task_id", "needs_generation")
                    subtask["task_id"] = task_id

                subtask["status"] = "pending_generation"
                analysis["pending_count"] += 1
                analysis["details"].append({
                    "task": task_id,
                    "status": "pending_generation",
                    "generated_task_id": task_id,
                })

        return analysis

    def _build_data_flow(self, subtasks: List[Dict], execution_order: List[str]) -> List[Dict]:
        """Build data flow connections between subtasks."""
        data_flow = []

        for i in range(len(execution_order) - 1):
            from_task = execution_order[i]
            to_task = execution_order[i + 1]

            from_outputs = next((t.get("outputs", []) for t in subtasks if t["subtask_name"] == from_task), [])
            to_inputs = next((t.get("inputs", []) for t in subtasks if t["subtask_name"] == to_task), [])

            if from_outputs and to_inputs:
                data_flow.append({
                    "from": from_task,
                    "to": to_task,
                    "data": from_outputs[0] if from_outputs else "output",
                })

        return data_flow

    def _calculate_complexity(self, subtasks: List[Dict]) -> float:
        """Calculate overall complexity of composite task."""
        analyzer = self.resolver.analyzer
        complexities = []

        for subtask in subtasks:
            domain = subtask["domain"]
            task_id = subtask["task_id"]
            domain_info = analyzer.analyze_domain_tasks(domain)

            if task_id in domain_info["tasks"]:
                complexities.append(domain_info["tasks"][task_id].get("complexity", 5))

        if not complexities:
            return 5.0

        return min(10, max(1, sum(complexities) / len(complexities) * 1.5))

    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate confidence in the generated composite task."""
        total = analysis["available_count"] + analysis["pending_count"] + analysis["missing_count"]
        if total == 0:
            return 0.0

        available_ratio = analysis["available_count"] / total
        pending_penalty = analysis["pending_count"] * 0.1
        missing_penalty = analysis["missing_count"] * 0.2

        confidence = max(0, min(1, available_ratio - pending_penalty - missing_penalty))
        return round(confidence, 2)

    def print_composite_task_details(self, composite_task: Dict):
        """Print detailed information about generated composite task."""
        summary = composite_task["summary"]

        print(f"\n{'=' * 80}")
        print(f"COMPOSITE TASK GENERATED: {composite_task['task_name'].upper()}")
        print(f"{'=' * 80}")
        print(f"Description: {composite_task['description']}")
        print(f"Task Type: {composite_task['task_type']}")
        print(f"Domains: {', '.join(composite_task['domains'])}")
        print(f"Complexity Score: {composite_task['complexity_score']:.1f}/10")
        print(f"Confidence: {composite_task['generation_metadata']['confidence']:.1%}")

        print(f"\n{'SUBTASK INVENTORY':^80}")
        print(f"{'-' * 80}")
        print(f"Total Subtasks: {summary['total_subtasks']}")
        print(f"  [AVAILABLE]         {summary['available']:3} ({summary['available']/summary['total_subtasks']*100:.1f}%)")
        print(f"  [PENDING]           {summary['pending_generation']:3} ({summary['pending_generation']/summary['total_subtasks']*100:.1f}%)")
        print(f"  [MISSING]           {summary['missing']:3} ({summary['missing']/summary['total_subtasks']*100:.1f}%)")

        print(f"\n{'EXECUTION ORDER':^80}")
        print(f"{'-' * 80}")
        for i, task_name in enumerate(composite_task["execution_order"], 1):
            print(f"  {i}. {task_name}")

        print(f"\n{'DATA FLOW':^80}")
        print(f"{'-' * 80}")
        for flow in composite_task["data_flow"]:
            print(f"  {flow['from']:30} --> {flow['to']:30} ({flow['data']})")

        print(f"\n{'SUBTASK DETAILS':^80}")
        print(f"{'-' * 80}")
        for subtask in composite_task["subtasks"]:
            status_icon = "[OK]" if subtask["status"] == "available" else "[PENDING]" if subtask["status"] == "pending_generation" else "[MISSING]"
            print(f"  {status_icon} {subtask['subtask_name']:35} ({subtask['domain']:15}) - {subtask['status']}")

        print(f"\nGenerated: {composite_task['generated_at']}")
        print()


def load_resource_constraints() -> Dict[str, Any]:
    """Load resource constraints from resource stats (best-effort)."""
    resource_path = BASE_DIR / "resource_stat" / "resource_usage_summary.json"
    defaults = {
        "min_available_memory_mb": 100,
        "max_cpu_percent": 80,
        "skip_if_insufficient": True,
    }
    if resource_path.exists():
        try:
            with open(resource_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
            if isinstance(stats, dict):
                if "available_memory_mb" in stats:
                    defaults["min_available_memory_mb"] = stats.get("available_memory_mb", defaults["min_available_memory_mb"])
                if "cpu_percent" in stats:
                    defaults["max_cpu_percent"] = stats.get("cpu_percent", defaults["max_cpu_percent"])
        except Exception:
            pass
    return defaults


def _validate_python_syntax(code: str) -> tuple[bool, str]:
    """Check whether the supplied Python code parses successfully."""
    if not isinstance(code, str) or not code.strip():
        return False, "Python source is empty"

    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        location = f"line {exc.lineno}, column {exc.offset}" if exc.lineno is not None else "unknown location"
        return False, f"Syntax error at {location}: {exc.msg or 'Invalid Python syntax'}"


def _repair_workflow_executor_with_llm(script_content: str, composite_task: Dict[str, Any]) -> str:
    """Ask the LLM validator to repair a generated workflow executor script."""
    try:
        from openai import OpenAI
    except Exception as exc:
        print(f"[WARNING] Workflow executor repair skipped: {exc}")
        return script_content

    try:
        from prompts.get_validated import SYSTEM_PROMPT as VALIDATION_SYSTEM_PROMPT
    except Exception:
        VALIDATION_SYSTEM_PROMPT = "You are an edge-device Python validator and repair agent. Return only valid JSON."

    task_name = composite_task.get("task_name", "complex_task")
    repair_prompt = Template(
        """
Repair this generated workflow executor script.

Task name: $TASK_NAME
Description: $DESCRIPTION
Domains: $DOMAINS

Requirements:
- Return ONLY a JSON object matching the validator response format.
- If the script is valid, set is_valid=true and corrected_code to the original code.
- If the script needs fixes, set is_valid=false and provide the full corrected script in corrected_code.
- Keep the script lightweight and executable.
- Ensure the executor combines existing subtask scripts correctly and handles missing files safely.

Generated script:
$SCRIPT_CONTENT
"""
    ).substitute(
        TASK_NAME=task_name,
        DESCRIPTION=composite_task.get("description", ""),
        DOMAINS=", ".join(composite_task.get("domains", [])),
        SCRIPT_CONTENT=script_content,
    )

    try:
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        payload = extract_first_json_object(response.choices[0].message.content)
        corrected_code = payload.get("corrected_code") or script_content
        is_valid = bool(payload.get("is_valid", False))
        repaired = corrected_code if corrected_code.strip() else script_content

        syntax_ok, syntax_error = _validate_python_syntax(repaired)
        if not syntax_ok:
            print(f"[WARNING] LLM-repaired executor still has syntax issues: {syntax_error}")
            return script_content

        if not is_valid:
            print("[WARNING] LLM repair returned a corrected executor that was marked invalid; using repaired code after syntax check.")

        return repaired
    except Exception as exc:
        print(f"[WARNING] Workflow executor repair failed: {exc}")
        return script_content


def generate_workflow_executor(composite_task: Dict, output_dir: str = None) -> str:
    """Generate an executable Python script for a complex task and save it.

    Returns path to generated script or None on error.
    """
    if output_dir is None:
        output_dir = BASE_DIR / "generated_tasks" / "complex"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_name = composite_task.get("task_name", "complex_task").strip().replace(" ", "_").lower()
    script_path = output_dir / f"{script_name}_executor.py"

    try:
        script_content = _generate_executor_script(composite_task)
        repaired_content = _repair_workflow_executor_with_llm(script_content, composite_task)
        syntax_ok, syntax_error = _validate_python_syntax(repaired_content)
        if not syntax_ok:
            print(f"[ERROR] Generated executor failed syntax validation: {syntax_error}")
            return None

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(repaired_content)
        print(f"[OK] Generated executor: {script_path}")

        try:
            import validator as task_validator

            print(f"[Validator] Checking generated executor: {script_path}")
            validation_result = task_validator.validate_and_fix_task(
                str(script_path),
                {
                    "task_name": composite_task.get("task_name", "complex_task"),
                    "description": composite_task.get("description", ""),
                    "data_type": "complex",
                },
                str(output_dir),
            )
            if validation_result.get("status") != "passed":
                print(f"[WARNING] Executor validation did not pass: {validation_result.get('message', 'unknown reason')}")
            else:
                print(f"[OK] Executor validation passed for {script_path}")
        except Exception as validation_error:
            print(f"[WARNING] Executor validation step failed: {validation_error}")

        return str(script_path)
    except Exception as e:
        print(f"[ERROR] Failed to generate executor: {e}")
        return None


def _generate_executor_script(composite_task: Dict) -> str:
    """Return the text content of the executor script for a composite task."""
    task_name = composite_task.get("task_name", "complex_task")
    description = composite_task.get("description", "")
    domains = composite_task.get("domains", [])
    subtasks = composite_task.get("subtasks", [])

    subtask_imports = _generate_subtask_imports(subtasks)
    subtask_execution = _generate_subtask_execution(subtasks)
    decision_logic = _generate_decision_logic(task_name, domains, subtasks)
    exec_order_json = json.dumps(_get_execution_order(subtasks), indent=4)
    resource_defaults = load_resource_constraints()

    template = '''"""
Auto-generated Complex Task Executor
Task: {TASK_NAME}
Description: {DESCRIPTION}
Domains: {DOMAINS}

Generated: {GENERATED_AT}
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

# IST helper not required at runtime, but we keep timestamp format

# Resource constraints (populated at generation time)
RESOURCE_CONSTRAINTS = {RESOURCE_CONSTRAINTS}

{SUBTASK_IMPORTS}

def execute_subtasks():
    """Execute all subtasks in defined order and collect outputs."""
    results = {{}}
    execution_order = {EXEC_ORDER}

    print(f"[WORKFLOW] Executing {{len(execution_order)}} subtasks in order...")
    for idx, task_info in enumerate(execution_order, 1):
        task_id = task_info.get("task_id")
        task_name = task_info.get("task_name")
        domain = task_info.get("domain")
        print(f"\n[{{idx}}] Executing: {{task_name}} ({{task_id}}) from {{domain}}")
        try:
{SUBTASK_EXECUTION}
        except Exception as e:
            print(f"[ERROR] Failed to execute {{task_name}}: {{e}}")
            results[task_id] = {{"status": "error", "error": str(e)}}
    return results

{DECISION_LOGIC}

def check_resource_constraints():
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        if mem.available / (1024**2) < RESOURCE_CONSTRAINTS.get("min_available_memory_mb", 100):
            return False, f"Low memory: {{mem.available // (1024**2)}}MB"
        if cpu > RESOURCE_CONSTRAINTS.get("max_cpu_percent", 80):
            return False, f"High CPU: {{cpu}}%"
        return True, "Resources OK"
    except Exception:
        return True, "psutil unavailable - skipping resource check"


def main():
    print('\n' + '=' * 80)
    print('[WORKFLOW] {TASK_DISPLAY}')
    print('=' * 80)
    print('[DOMAINS] {DOMAINS}')
    print('[TIME] ' + datetime.now().isoformat())

    ok, msg = check_resource_constraints()
    print('[RESOURCES] ' + msg)
    if not ok and RESOURCE_CONSTRAINTS.get('skip_if_insufficient', True):
        print('[SKIP] Insufficient resources - aborting')
        return {{'task_name': '{TASK_NAME}', 'status': 'skipped', 'reason': msg, 'timestamp': datetime.now().isoformat()}}

    results = execute_subtasks()
    analysis = analyze_and_combine_results(results)

    final = {{
        'task_name': '{TASK_NAME}',
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'subtask_results': results,
        'analysis': analysis,
        'result_summary': [{{'key': k, 'value': v}} for k, v in analysis.items()]
    }}

    print('\n' + '=' * 80)
    print('[RESULT] FINAL ANALYSIS')
    print('=' * 80)
    for k, v in analysis.items():
        print(f"  {{k:30}} → {{v}}")
    print('=' * 80)
    print('\n' + json.dumps(final, indent=2, ensure_ascii=False))
    return final


if __name__ == '__main__':
    res = main()
    sys.exit(0 if res.get('status') == 'success' else 1)
'''

    filled = template.replace('{TASK_NAME}', task_name.replace("'", "\\'"))
    filled = filled.replace('{DESCRIPTION}', description.replace("'", "\\'"))
    filled = filled.replace('{DOMAINS}', ', '.join(domains))
    filled = filled.replace('{GENERATED_AT}', datetime.now(IST).isoformat())
    filled = filled.replace('{SUBTASK_IMPORTS}', subtask_imports)
    filled = filled.replace('{EXEC_ORDER}', exec_order_json)
    filled = filled.replace('{SUBTASK_EXECUTION}', subtask_execution)
    filled = filled.replace('{DECISION_LOGIC}', decision_logic)
    filled = filled.replace('{RESOURCE_CONSTRAINTS}', json.dumps(resource_defaults))
    filled = filled.replace('{TASK_DISPLAY}', task_name.upper())

    return filled


def _generate_subtask_imports(subtasks: List[Dict]) -> str:
    """Generate helper functions that run each subtask as a subprocess and return parsed JSON."""
    parts = [
        "def ensure_generated_subtask_script(task_path, task_name, domain):\n"
        "    if task_path.exists():\n"
        "        return task_path\n"
        "    task_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    fallback_code = f'''\n"
        "import csv\n"
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "BASE_DIR = Path(__file__).parent.parent\n"
        "\n"
        "def main():\n"
        "    sample_path = BASE_DIR / 'data' / '{domain}' / 'sample_data.csv'\n"
        "    row_count = 0\n"
        "    sample_preview = []\n"
        "    if sample_path.exists():\n"
        "        try:\n"
        "            with open(sample_path, 'r', encoding='utf-8') as f:\n"
        "                rows = list(csv.reader(f))\n"
        "            row_count = max(len(rows) - 1, 0)\n"
        "            sample_preview = rows[:2]\n"
        "        except Exception:\n"
        "            pass\n"
        "\n"
        "    result = {{\n"
        "        'task_name': '{task_name}',\n"
        "        'status': 'success',\n"
        "        'result_summary': [\n"
        "            {{'key': 'domain', 'value': '{domain}'}},\n"
        "            {{'key': 'row_count', 'value': row_count}},\n"
        "            {{'key': 'sample_preview', 'value': sample_preview[:2]}},\n"
        "            {{'key': 'mode', 'value': 'auto_generated_fallback'}},\n"
        "        ],\n"
        "    }}\n"
        "    print(json.dumps(result, ensure_ascii=False))\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
        "'''\n"
        "    task_path.write_text(fallback_code, encoding='utf-8')\n"
        "    return task_path\n"
    ]

    for idx, s in enumerate(subtasks):
        task_id = s.get('task_id', '')
        domain = s.get('domain', '')
        task_name = s.get('subtask_name', task_id or 'generated_subtask')
        fn_name = f"run_subtask_{idx}"
        code = (
            f"def {fn_name}():\n"
            f"    task_path = BASE_DIR / 'generated_tasks' / '{domain}' / '{task_id}.py'\n"
            f"    task_path = ensure_generated_subtask_script(task_path, {task_name!r}, {domain!r})\n"
            f"    try:\n"
            f"        proc = subprocess.run([sys.executable, str(task_path)], capture_output=True, text=True, timeout=120)\n"
            f"        if proc.returncode == 0 and proc.stdout:\n"
            f"            try:\n"
            f"                return json.loads(proc.stdout.strip())\n"
            f"            except Exception:\n"
            f"                return {{'status':'error','output': proc.stdout}}\n"
            f"        return {{'status':'error','stderr': proc.stderr}}\n"
            f"    except subprocess.TimeoutExpired:\n"
            f"        return {{'status':'timeout'}}\n"
            f"    except Exception as e:\n"
            f"        return {{'status':'error','error': str(e)}}\n"
        )
        parts.append(code)
    return '\n'.join(parts)


def _generate_subtask_execution(subtasks: List[Dict]) -> str:
    """Generate code invoked inside execute_subtasks to call helper functions and store results."""
    lines = []
    for idx, s in enumerate(subtasks):
        task_id = s.get('task_id', '')
        fn_name = f"run_subtask_{idx}"
        lines.append(f"        output = {fn_name}()")
        lines.append(f"        results['{task_id}'] = output")
    return '\n'.join(lines)


def _generate_decision_logic(task_name: str, domains: List[str], subtasks: List[Dict]) -> str:
    """Return a string containing a Python function analyze_and_combine_results(results)."""
    header = '''def analyze_and_combine_results(subtask_results):
    analysis = {'workflow_status':'completed','subtasks_executed': len(subtask_results)}
    metrics = {}
    for tid, res in subtask_results.items():
        if isinstance(res, dict) and res.get('status') == 'success' and 'result_summary' in res:
            for item in res.get('result_summary', []):
                key = f"{tid}_{item.get('key')}"
                metrics[key] = item.get('value')
    analysis['metrics'] = metrics
'''
    body = ''
    if 'air_quality' in domains and 'wind' in domains:
        body += '''
    # Air Quality + Wind rules
    pm25 = None
    wind = None
    for k, v in metrics.items():
        kl = k.lower()
        if 'pm2' in kl and '5' in kl:
            try:
                pm25 = float(v)
            except:
                pass
        if 'wind' in kl and ('speed' in kl or 'spd' in kl):
            try:
                wind = float(v)
            except:
                pass
    analysis['pm25_level'] = pm25
    analysis['wind_speed'] = wind
    if pm25 is not None and wind is not None:
        if pm25 > 100 and wind < 3:
            analysis['conclusion'] = 'POLLUTION TRAP: High PM2.5 with low wind'
            analysis['severity'] = 'HIGH'
            analysis['recommendation'] = 'Alert: pollution likely to accumulate.'
        elif pm25 > 50 and wind < 5:
            analysis['conclusion'] = 'MODERATE POLLUTION with low wind'
            analysis['severity'] = 'MEDIUM'
            analysis['recommendation'] = 'Caution advised.'
        elif wind > 10:
            analysis['conclusion'] = 'GOOD DISPERSION'
            analysis['severity'] = 'LOW'
            analysis['recommendation'] = 'Wind favors dispersion.'
'''
    if 'temp_humidity' in domains and 'wind' in domains:
        body += '''
    # Temp/Humidity + Wind rules
    temp = None
    hum = None
    for k, v in metrics.items():
        kl = k.lower()
        if 'temp' in kl:
            try:
                temp = float(v)
            except:
                pass
        if 'humid' in kl:
            try:
                hum = float(v)
            except:
                pass
    analysis['temperature'] = temp
    analysis['humidity'] = hum
    if temp is not None and hum is not None:
        if 20 <= temp <= 25 and 30 <= hum <= 65:
            analysis['comfort_level'] = 'OPTIMAL'
            analysis['recommendation'] = 'Good for outdoor activities.'
        else:
            analysis['comfort_level'] = 'UNCOMFORTABLE'
'''
    footer = '\n    return analysis\n'
    return header + body + footer


def _get_execution_order(subtasks: List[Dict]) -> List[Dict]:
    """Return execution order; currently preserves given order. Replace with topological sort if needed."""
    return [
        {"task_id": s.get('task_id', ''), "task_name": s.get('subtask_name', ''), "domain": s.get('domain', '')}
        for s in subtasks
    ]


if __name__ == '__main__':
    print('[INFO] generation module loaded')


# --- LLM-driven composite task generator helpers (merged from complex_task_generator_llm.py) ---

# Paths and directories
DATA_DIR = BASE_DIR / "data"
GENERATED_TASKS_DIR = BASE_DIR / "generated_tasks"
OUTPUT_DIR = BASE_DIR / "output" / "complex_tasks_generated"
COMPOSITE_TASKS_PATH = GENERATED_TASKS_DIR / "complex" / "complex_tasks_list.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
COMPOSITE_TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)

# Environment helpers
env_vars = get_environment_vars()
RUN_ID = env_vars.get("RUN_ID", datetime.now().strftime("run_%Y%m%d%H%M%S"))
RUN_COUNT = env_vars.get("RUN_COUNT", 1)


def discover_domains_with_tasks():
    """Discover all domains and their available tasks."""
    from .analysis import TaskAnalyzer

    analyzer = TaskAnalyzer(generated_tasks_dir=str(GENERATED_TASKS_DIR))
    domains = analyzer.discover_all_domains()

    domains_info = {}
    for domain in domains:
        domain_analysis = analyzer.analyze_domain_tasks(domain)
        domains_info[domain] = {
            "task_count": domain_analysis.get("task_count", len(domain_analysis.get("tasks", {}))),
            "tasks": [
                {
                    "task_id": name,
                    "description": info.get("docstring", "")[:100],
                    "primary_function": info.get("primary_function", "unknown"),
                    "complexity": info.get("complexity", 5),
                }
                for name, info in list(domain_analysis.get("tasks", {}).items())[:15]
            ],
            "capabilities": list(domain_analysis.get("capabilities", [])),
        }

    return domains_info


def load_domain_samples():
    """Load sample data and metadata for each domain."""
    samples = {}

    for domain_dir in DATA_DIR.iterdir():
        if not domain_dir.is_dir() or domain_dir.name.startswith("_"):
            continue

        domain = domain_dir.name
        samples[domain] = {}

        # Load sample data
        sample_path = domain_dir / "sample_data.csv"
        if sample_path.exists():
            try:
                with open(sample_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[:3]
                samples[domain]["sample_data"] = "".join(lines)
            except Exception:
                pass

        # Load metadata
        metadata_path = domain_dir / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    samples[domain]["metadata"] = json.load(f)
            except Exception:
                pass

        # Load context
        context_path = domain_dir / "context.txt"
        if context_path.exists():
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    samples[domain]["context"] = f.read()[:300]
            except Exception:
                pass

    return samples


def load_resource_stats():
    """Load resource usage statistics."""
    resource_path = BASE_DIR / "resource_stat" / "resource_usage_summary.json"

    if resource_path.exists():
        try:
            with open(resource_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {"status": "unavailable", "message": "Resource stats not yet generated"}


def load_existing_composite_tasks():
    """Load previously generated composite tasks."""
    if COMPOSITE_TASKS_PATH.exists():
        try:
            with open(COMPOSITE_TASKS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("composite_tasks", [])
        except Exception:
            pass

    return []


def format_domains_info(domains_info):
    """Format domains info for LLM prompt."""
    formatted = []

    for domain, info in domains_info.items():
        formatted.append(f"\n{domain.upper()}:")
        formatted.append(f"  Total tasks: {info['task_count']}")
        formatted.append(f"  Capabilities: {', '.join(info.get('capabilities', [])[:5])}")
        formatted.append(f"  Sample tasks:")

        for task in info['tasks'][:5]:
            desc = task['description'][:60] if task['description'] else "No description"
            formatted.append(f"    - {task['task_id']}: {desc}")

    return "\n".join(formatted)


def format_samples(samples):
    """Format domain samples for LLM prompt."""
    formatted = []

    for domain, sample_data in samples.items():
        formatted.append(f"\n{domain.upper()}:")

        if "metadata" in sample_data:
            try:
                if isinstance(sample_data["metadata"], dict):
                    fields = list(sample_data["metadata"].keys())[:8]
                    formatted.append(f"  Fields: {', '.join(fields)}")
            except Exception:
                pass

        if "context" in sample_data:
            formatted.append(f"  Context: {sample_data['context'][:150]}...")

    return "\n".join(formatted)


def format_domain_metadata(samples):
    """Format per-domain metadata for the LLM prompt."""
    formatted = []

    for domain, sample_data in samples.items():
        formatted.append(f"\n{domain.upper()}:" )
        metadata = sample_data.get("metadata", {})
        if isinstance(metadata, dict) and metadata:
            for key, value in list(metadata.items())[:12]:
                if isinstance(value, (dict, list)):
                    value_text = json.dumps(value, ensure_ascii=False)[:180]
                else:
                    value_text = str(value)[:180]
                formatted.append(f"  - {key}: {value_text}")
        else:
            formatted.append("  - No metadata available")

    return "\n".join(formatted)


def format_domain_contexts(samples):
    """Format per-domain operational context for the LLM prompt."""
    formatted = []

    for domain, sample_data in samples.items():
        formatted.append(f"\n{domain.upper()}:" )
        context = sample_data.get("context", "")
        if context:
            formatted.append(f"  - {context[:300]}")
        else:
            formatted.append("  - No operational context available")

    return "\n".join(formatted)


def format_existing_composite_tasks(existing_tasks, max_items=12):
    """Format existing composite tasks compactly so the LLM can avoid repeating them."""
    if not existing_tasks:
        return "No existing composite tasks."

    lines = []
    lines.append(f"Existing composite tasks: {len(existing_tasks)}")

    pair_counts = {}
    for task in existing_tasks:
        domains = tuple(sorted([d.strip().lower() for d in (task.get("domains") or [])]))
        if domains:
            pair_counts[domains] = pair_counts.get(domains, 0) + 1

    if pair_counts:
        lines.append("Existing domain pairs:")
        for domains, count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))[:max_items]:
            lines.append(f"- {', '.join(domains)} ({count})")

    lines.append("Existing task names:")
    for task in existing_tasks[:max_items]:
        name = task.get("task_name", "Unnamed task")
        domains = ", ".join(task.get("domains", [])[:3])
        lines.append(f"- {name} [{domains}]")

    return "\n".join(lines)


def _parse_complex_tasks_response(response_text: str) -> Dict[str, Any]:
    """Parse a complex-task LLM response into the expected payload shape."""
    payload = extract_first_json_object(response_text)
    composite_tasks = payload.get("composite_tasks", [])
    if not isinstance(composite_tasks, list):
        composite_tasks = []
    payload["composite_tasks"] = composite_tasks
    return payload


def _request_complex_tasks_json(client, request_kwargs: Dict[str, Any], repair_prompt: str = None):
    """Request a JSON response, optionally using a repair prompt for invalid output."""
    kwargs = dict(request_kwargs)
    if repair_prompt is not None:
        kwargs["messages"] = [
            {"role": "system", "content": "Return only valid JSON object. No markdown, no prose, no code fences."},
            {"role": "user", "content": repair_prompt},
        ]
        kwargs["temperature"] = 0.0

    try:
        return client.chat.completions.create(**kwargs, response_format={"type": "json_object"})
    except Exception:
        return client.chat.completions.create(**kwargs)


def _serialize_token_usage(usage: Any) -> Any:
    """Convert LLM usage objects into JSON-safe data."""
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    if hasattr(usage, "model_dump"):
        try:
            return usage.model_dump()
        except Exception:
            pass
    if hasattr(usage, "dict"):
        try:
            return usage.dict()
        except Exception:
            pass
    if hasattr(usage, "__dict__"):
        return {k: v for k, v in vars(usage).items() if not k.startswith("_")}
    return str(usage)


def get_existing_domain_combinations(existing_tasks):
    """Return counts for existing composite domain combinations."""
    pair_counts = {}

    for task in existing_tasks or []:
        domains = tuple(sorted({d.strip().lower() for d in (task.get("domains") or []) if d}))
        if len(domains) >= 2:
            pair_counts[domains] = pair_counts.get(domains, 0) + 1

    return pair_counts


def select_target_domain_combinations(
    domains_info,
    existing_tasks,
    max_combinations=6,
    min_domains=2,
    max_domains=5,
    valid_domains=None,
):
    """Choose underused multi-domain combinations for the next composite-task request."""
    allowed_domain_set = {d.strip().lower() for d in (valid_domains or domains_info.keys()) if d}
    available_domains = sorted(
        domain.strip().lower()
        for domain, info in domains_info.items()
        if domain
        and domain.strip().lower() in allowed_domain_set
        and domain.strip().lower() != "complex"
        and int(info.get("task_count", 0) or 0) > 0
    )
    combination_counts = get_existing_domain_combinations(existing_tasks)

    upper_bound = min(max_domains, len(available_domains))
    candidate_combinations = []
    for size in range(upper_bound, min_domains - 1, -1):
        candidate_combinations.extend(combinations(available_domains, size))

    if not candidate_combinations:
        return [], combination_counts

    unused_combinations = [combo for combo in candidate_combinations if combo not in combination_counts]

    if unused_combinations:
        return unused_combinations[:max_combinations], combination_counts

    ranked_combinations = sorted(
        candidate_combinations,
        key=lambda combo: (combination_counts.get(combo, 0), -len(combo), combo),
    )
    return ranked_combinations[:max_combinations], combination_counts


def format_domain_combinations(combinations_list, label):
    """Format domain combinations for prompt instructions."""
    if not combinations_list:
        return f"{label}: none"

    lines = [f"{label}:"]
    for combo in combinations_list:
        lines.append(f"- {', '.join(combo)}")
    return "\n".join(lines)


def format_combination_objective_bank(combinations_list):
    """Provide combination-specific objective ideas to improve task diversity."""
    if not combinations_list:
        return "No pair-specific objectives available."

    objective_bank = {
        ("air_quality", "wind"): [
            "pollution dispersion analysis",
            "downwind exposure estimation",
            "pollutant transport nowcasting",
            "source attribution under changing wind conditions",
            "wind-speed and PM2.5 lag correlation",
            "stagnant-air pollution persistence detection",
            "wind corridor risk mapping",
            "pollution dilution potential scoring",
        ],
        ("soil", "temp_humidity"): [
            "irrigation stress assessment",
            "root-zone comfort analysis",
            "soil evaporation risk estimation",
            "moisture retention versus temperature response",
        ],
        ("soil", "wind"): [
            "surface drying risk analysis",
            "dust emission potential estimation",
            "wind-driven soil moisture loss analysis",
        ],
        ("air_quality", "soil"): [
            "pollution deposition impact assessment",
            "soil contamination risk analysis",
        ],
        ("temp_humidity", "wind"): [
            "comfort loss under ventilation changes",
            "humidity exchange analysis",
        ],
    }

    lines = ["Combination-specific objective bank:"]
    for combo in combinations_list:
        normalized = tuple(sorted(combo))
        if len(normalized) == 2:
            objectives = objective_bank.get(normalized, ["cross-domain correlation analysis", "joint anomaly detection"])
        else:
            objectives = [
                f"joint analysis across {', '.join(normalized)}",
                f"multi-domain dependency mapping for {', '.join(normalized)}",
                f"cross-domain anomaly detection spanning {', '.join(normalized)}",
                f"combined risk assessment using {', '.join(normalized)}",
            ]
        lines.append(f"- {', '.join(normalized)}:")
        for objective in objectives:
            lines.append(f"  - {objective}")

    return "\n".join(lines)


def filter_composite_tasks_by_combinations(tasks, allowed_combinations):
    """Keep only tasks whose domain combinations match one of the allowed combinations."""
    if not allowed_combinations:
        return tasks or []

    allowed = {tuple(sorted(combo)) for combo in allowed_combinations}
    filtered = []

    for task in tasks or []:
        domains = tuple(sorted({d.strip().lower() for d in (task.get("domains") or []) if d}))
        if 2 <= len(domains) <= 5 and domains in allowed:
            filtered.append(task)

    return filtered


def call_llm_for_complex_tasks(domains_info, samples, resource_stats, existing_tasks):
    """Call LLM to generate complex task specifications."""

    # Lazy import of OpenAI client to avoid hard dependency at import-time
    try:
        from openai import OpenAI
    except Exception as e:
        print(f"[ERROR] openai SDK import failed: {e}")
        return {"composite_tasks": [], "status": "failed", "error": "openai import failed"}

    # Format information for prompt
    domains_and_tasks = format_domains_info(domains_info)
    domain_samples = format_samples(samples)
    domain_metadata = format_domain_metadata(samples)
    domain_contexts = format_domain_contexts(samples)
    resource_info = json.dumps(resource_stats, indent=2)[:500]
    existing_info = format_existing_composite_tasks(existing_tasks)
    target_domain_combinations, existing_combination_counts = select_target_domain_combinations(
        domains_info,
        existing_tasks,
        valid_domains=samples.keys(),
    )
    print(f"[DEBUG] Selected target domain combinations: {target_domain_combinations}")
    target_combinations_info = format_domain_combinations(target_domain_combinations, "Target domain combinations")
    blocked_combinations = [combo for combo, count in existing_combination_counts.items() if count > 0]
    print(f"[DEBUG] Blocked domain combinations: {blocked_combinations}")
    blocked_combinations_info = format_domain_combinations(blocked_combinations, "Already used domain combinations")
    combination_objective_bank = format_combination_objective_bank(target_domain_combinations)

    # Build user prompt
    try:
        from prompts.get_complex_tasks import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
    except Exception:
        SYSTEM_PROMPT = "You are a helpful assistant."
        USER_PROMPT_TEMPLATE = "Generate composite tasks."

    user_prompt = Template(USER_PROMPT_TEMPLATE).substitute(
        DOMAINS_AND_TASKS=domains_and_tasks,
        DOMAIN_METADATA=domain_metadata,
        DOMAIN_SAMPLES=domain_samples,
        DOMAIN_CONTEXTS=domain_contexts,
        RESOURCE_STATS=resource_info,
        EXISTING_COMPOSITE_TASKS=existing_info,
        TARGET_DOMAIN_COMBINATIONS=target_combinations_info,
        BLOCKED_DOMAIN_COMBINATIONS=blocked_combinations_info,
        COMBINATION_OBJECTIVE_BANK=combination_objective_bank,
    )
    print(f"[DEBUG] User prompt length: {len(user_prompt)} characters")

    print("\n[LLM] Calling LLM for complex task generation...")
    print(f"[LLM] Model: {DEFAULT_MODEL}")

    start_time = datetime.now(IST).isoformat()
    start_perf = time.perf_counter()

    try:
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        request_kwargs = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
            "top_p": 0.95,
        }

        response = _request_complex_tasks_json(client, request_kwargs)

        elapsed = time.perf_counter() - start_perf
        end_time = datetime.now(IST).isoformat()

        print(f"[LLM] Completed in {elapsed:.2f}s")

        # Extract JSON from response
        response_text = response.choices[0].message.content
        try:
            composite_tasks_payload = _parse_complex_tasks_response(response_text)
        except Exception as parse_error:
            print(f"[LLM] Initial JSON parse failed: {parse_error}")
            print("[LLM] Raw response (pre-repair):")
            print(response_text[:2000])
            repair_prompt = (
                "Rewrite the following model output as a strict JSON object with the exact shape {\"composite_tasks\": [...]} . "
                "Use only the allowed target domain pairs and return no extra text.\n\n"
                f"MODEL OUTPUT:\n{response_text}"
            )
            repair_response = _request_complex_tasks_json(client, request_kwargs, repair_prompt=repair_prompt)
            repair_text = repair_response.choices[0].message.content
            print("[LLM] Raw repair response:")
            print(repair_text[:2000])
            composite_tasks_payload = _parse_complex_tasks_response(repair_text)
            response = repair_response

        composite_tasks_list = composite_tasks_payload.get("composite_tasks", [])

        if not isinstance(composite_tasks_list, list):
            composite_tasks_list = []

        # Only apply strict domain-combination filtering if we actually provided targets
        if target_domain_combinations:
            composite_tasks_list = filter_composite_tasks_by_combinations(composite_tasks_list, target_domain_combinations)
        else:
            # keep whatever the model returned
            composite_tasks_list = composite_tasks_list or []

        if not composite_tasks_list:
            print("[WARN] No composite tasks remain after parsing/filtering. Response payload keys: " + ",".join(composite_tasks_payload.keys() if isinstance(composite_tasks_payload, dict) else []))
            # log some of the raw response for diagnostics
            try:
                print("[WARN] Full LLM response (truncated):")
                print(response_text[:3000])
            except Exception:
                pass

        generated_data = {
            "composite_tasks": composite_tasks_list,
            "status": "success",
            "llm_model": DEFAULT_MODEL,
            "start_time": start_time,
            "end_time": end_time,
            "duration_sec": elapsed,
            "token_usage": _serialize_token_usage(getattr(response, 'usage', {})),
        }

        generated_count = save_complex_tasks(generated_data)
        generated_data["saved_count"] = generated_count
        return generated_data

    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        return {"composite_tasks": [], "status": "failed", "error": str(e)}


def save_complex_tasks(generated_data):
    """Save generated complex task specifications."""
    output_file = OUTPUT_DIR / f"complex_tasks_{sanitize_model_name(DEFAULT_MODEL)}_{RUN_ID}.json"
    complex_output_dir = GENERATED_TASKS_DIR / "complex"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(generated_data, f, indent=2, ensure_ascii=False)

        print(f"[OK] Saved complex tasks to {output_file}")
    except Exception as e:
        print(f"[ERROR] Failed to save complex tasks: {e}")
        return 0

    # Update master list with deduplication by signature
    existing = []
    if COMPOSITE_TASKS_PATH.exists():
        try:
            with open(COMPOSITE_TASKS_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f).get("composite_tasks", [])
        except Exception:
            pass

    def task_signature(t):
        name = (t.get("task_name") or "").strip().lower()
        domains = tuple(sorted([d.strip().lower() for d in (t.get("domains") or [])]))
        subtasks = tuple(sorted([s.get("task_id", "").strip().lower() for s in (t.get("subtasks") or [])]))
        return (name, domains, subtasks)

    existing_sigs = {task_signature(t): t for t in existing}
    new_tasks_raw = generated_data.get("composite_tasks", []) or []
    new_tasks = []
    for t in new_tasks_raw:
        sig = task_signature(t)
        if sig in existing_sigs:
            continue
        existing_sigs[sig] = t
        new_tasks.append(t)

    existing = list(existing_sigs.values())

    try:
        with open(COMPOSITE_TASKS_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "composite_tasks": existing,
                "updated_at": datetime.now(IST).isoformat(),
                "total_count": len(existing)
            }, f, indent=2, ensure_ascii=False)

        print(f"[OK] Master list updated: {len(existing)} total composite tasks")
    except Exception as e:
        print(f"[ERROR] Failed to update master list: {e}")

    # Create a validator manifest only for composite tasks that have executors on disk.
    try:
        tasks_manifest_path = complex_output_dir / "new_tasks.json"
        manifest = {"tasks": []}
        for t in existing:
            safe_name = (t.get("task_name") or "").strip()
            script_base = safe_name.replace(" ", "_").replace("-", "_").lower()
            script_filename = f"{script_base}_executor.py"
            script_path = complex_output_dir / script_filename

            if not script_path.exists():
                print(f"[INFO] Skipping manifest entry for missing executor: {script_filename}")
                continue

            manifest["tasks"].append({
                "task_name": safe_name,
                "script_filename": script_filename,
                "description": t.get("description", ""),
                "data_type": "complex",
            })

        with open(tasks_manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2, ensure_ascii=False)

        print(f"[OK] Validator manifest written: {tasks_manifest_path}")

        if manifest["tasks"]:
            try:
                import validator as task_validator
                print("[Validator] Running validator on complex tasks...")
                val_result = task_validator.validate_all_generated_tasks(str(tasks_manifest_path), str(complex_output_dir))
                print(f"[Validator] Validation summary: {val_result.get('summary', {})}")
            except Exception as ve:
                print(f"[WARNING] Validator run failed: {ve}")
        else:
            print("[INFO] No executable composite tasks found; skipping validator run.")

    except Exception as e:
        print(f"[ERROR] Failed to write validator manifest: {e}")

    # Clear the per-run new_tasks.json after validation to avoid re-processing
    try:
        if tasks_manifest_path.exists():
            with open(tasks_manifest_path, 'w', encoding='utf-8') as mf:
                json.dump({"tasks": []}, mf, indent=2)
            print(f"[OK] Cleared validator manifest: {tasks_manifest_path}")
    except Exception as e:
        print(f"[WARNING] Failed to clear validator manifest: {e}")

    return len(new_tasks)


def generate_complex_tasks_llm():
    """Main function to generate complex tasks using LLM."""

    print("\n" + "=" * 80)
    print("COMPLEX TASK SYNTHESIS - LLM-DRIVEN GENERATION")
    print("=" * 80)

    print("\n[1] Discovering available domains and tasks...")
    domains_info = discover_domains_with_tasks()
    print(f"    Found {len(domains_info)} domains")
    for domain, info in domains_info.items():
        print(f"      [{domain:15}] {info['task_count']:3} tasks | {len(info.get('capabilities', []))} capabilities")

    if not domains_info:
        print("[INFO] No domains found. Generate tasks first using task_generator.py")
        return

    print("\n[2] Loading domain samples and metadata...")
    samples = load_domain_samples()
    print(f"    Loaded data for {len(samples)} domains")

    print("\n[3] Loading resource constraints...")
    resource_stats = load_resource_stats()

    print("\n[4] Checking for existing composite tasks...")
    existing_tasks = load_existing_composite_tasks()
    print(f"    Found {len(existing_tasks)} existing composite tasks")

    print("\n[5] Generating composite task specifications...")
    generated_data = call_llm_for_complex_tasks(domains_info, samples, resource_stats, existing_tasks)

    if generated_data.get("status") == "success":
        num_tasks = len(generated_data.get("composite_tasks", []))
        print(f"\n[OK] Generated {num_tasks} composite tasks")

        if num_tasks > 0:
            saved_count = generated_data.get("saved_count", 0)
            print(f"[OK] Added {saved_count} new composite tasks")

            print("\n" + "=" * 80)
            print("GENERATED COMPOSITE TASK SPECIFICATIONS")
            print("=" * 80)

            for i, task in enumerate(generated_data.get("composite_tasks", []), 1):
                print(f"\n[{i}] {task.get('task_name', 'Unknown')}")
                print(f"    Description: {task.get('description', 'N/A')[:80]}")
                print(f"    Business Value: {task.get('business_value', 'N/A')[:60]}")
                print(f"    Domains: {', '.join(task.get('domains', []))}")
                print(f"    Subtasks: {len(task.get('subtasks', []))}")

                for subtask in task.get("subtasks", [])[:5]:
                    task_id = subtask.get("task_id", "?")
                    status = "[AVAILABLE]" if task_id != "needs_generation" else "[GENERATE]"
                    print(f"      {status} {subtask.get('subtask_name', 'Unknown'):40} ({task_id})")
        else:
            print("\n[INFO] No new composite tasks generated")

    else:
        print(f"\n[ERROR] Failed to generate: {generated_data.get('error', 'Unknown error')}")

    return generated_data.get("saved_count", 0) if generated_data.get("status") == "success" else 0


__all__ = ["CompositeTaskGenerator", "generate_workflow_executor", "generate_complex_tasks_llm"]
