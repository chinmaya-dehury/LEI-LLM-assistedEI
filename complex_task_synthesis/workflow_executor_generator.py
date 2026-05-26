"""
Workflow Executor Generator
Generates executable Python scripts for complex tasks.

Each generated script:
- Loads and executes subtasks
- Combines outputs with business logic
- Considers resource constraints
- Returns actionable insights
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from shared_utils import IST


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
            # Map some common fields if available
            if isinstance(stats, dict):
                if "available_memory_mb" in stats:
                    defaults["min_available_memory_mb"] = stats.get("available_memory_mb", defaults["min_available_memory_mb"])
                if "cpu_percent" in stats:
                    defaults["max_cpu_percent"] = stats.get("cpu_percent", defaults["max_cpu_percent"])
        except Exception:
            pass
    return defaults


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
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        print(f"[OK] Generated executor: {script_path}")
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

    # Use a safe template and simple replacements (avoid nested f-strings in this file)
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
        print(f"\\n[{idx}] Executing: {{task_name}} ({{task_id}}) from {{domain}}")
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

    # Prepare replacements
    filled = template.replace('{TASK_NAME}', task_name.replace("'", "\'"))
    filled = filled.replace('{DESCRIPTION}', description.replace("'", "\'"))
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
    parts = []
    for idx, s in enumerate(subtasks):
        task_id = s.get('task_id', '')
        domain = s.get('domain', '')
        fn_name = f"run_subtask_{idx}"
        if task_id == 'needs_generation':
            code = f"def {fn_name}():\n    return {{'status':'pending','message':'needs_generation'}}\n"
        else:
            code = (
                f"def {fn_name}():\n"
                f"    task_path = BASE_DIR / 'generated_tasks' / '{domain}' / '{task_id}.py'\n"
                f"    if not task_path.exists():\n"
                f"        return {{'status':'not_found','error': str(task_path)}}\n"
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
        if task_id == 'needs_generation':
            lines.append(f"        results['{task_id}'] = {{'status':'pending','message':'needs_generation'}}")
        else:
            lines.append(f"        output = {fn_name}()")
            lines.append(f"        results['{task_id}'] = output")
    return '\n'.join(lines)


def _generate_decision_logic(task_name: str, domains: List[str], subtasks: List[Dict]) -> str:
    """Return a string containing a Python function analyze_and_combine_results(results).
    This is a minimal set of decision rules; extend as needed.
    """
    # Base function header
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
    print('[INFO] workflow_executor_generator module loaded')
