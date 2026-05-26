"""
Auto-generated Complex Task Executor
Task: Air Quality and Wind Trend Analysis
Description: This composite task integrates air quality and wind data to analyze trends and correlations between the two domains.
Domains: AIR_QUALITY, WIND

Generated: 2026-05-26T16:27:35.939527+05:30
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

# IST helper not required at runtime, but we keep timestamp format

# Resource constraints (populated at generation time)
RESOURCE_CONSTRAINTS = {"min_available_memory_mb": 100, "max_cpu_percent": 80, "skip_if_insufficient": true}

def run_subtask_0():
    task_path = BASE_DIR / 'generated_tasks' / 'AIR_QUALITY' / 'aqi_level_trend_analysis.py'
    if not task_path.exists():
        return {'status':'not_found','error': str(task_path)}
    try:
        proc = subprocess.run([sys.executable, str(task_path)], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            try:
                return json.loads(proc.stdout.strip())
            except Exception:
                return {'status':'error','output': proc.stdout}
        return {'status':'error','stderr': proc.stderr}
    except subprocess.TimeoutExpired:
        return {'status':'timeout'}
    except Exception as e:
        return {'status':'error','error': str(e)}

def run_subtask_1():
    task_path = BASE_DIR / 'generated_tasks' / 'WIND' / 'diurnal_wind_patterns.py'
    if not task_path.exists():
        return {'status':'not_found','error': str(task_path)}
    try:
        proc = subprocess.run([sys.executable, str(task_path)], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            try:
                return json.loads(proc.stdout.strip())
            except Exception:
                return {'status':'error','output': proc.stdout}
        return {'status':'error','stderr': proc.stderr}
    except subprocess.TimeoutExpired:
        return {'status':'timeout'}
    except Exception as e:
        return {'status':'error','error': str(e)}

def run_subtask_2():
    task_path = BASE_DIR / 'generated_tasks' / 'WIND' / 'cross_correlation_wind_analysis.py'
    if not task_path.exists():
        return {'status':'not_found','error': str(task_path)}
    try:
        proc = subprocess.run([sys.executable, str(task_path)], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            try:
                return json.loads(proc.stdout.strip())
            except Exception:
                return {'status':'error','output': proc.stdout}
        return {'status':'error','stderr': proc.stderr}
    except subprocess.TimeoutExpired:
        return {'status':'timeout'}
    except Exception as e:
        return {'status':'error','error': str(e)}


def execute_subtasks():
    """Execute all subtasks in defined order and collect outputs."""
    results = {{}}
    execution_order = [
    {
        "task_id": "aqi_level_trend_analysis",
        "task_name": "Air Quality Trend Analysis",
        "domain": "AIR_QUALITY"
    },
    {
        "task_id": "diurnal_wind_patterns",
        "task_name": "Wind Trend Analysis",
        "domain": "WIND"
    },
    {
        "task_id": "cross_correlation_wind_analysis",
        "task_name": "Correlation Analysis",
        "domain": "WIND"
    }
]

    print(f"[WORKFLOW] Executing {{len(execution_order)}} subtasks in order...")
    for idx, task_info in enumerate(execution_order, 1):
        task_id = task_info.get("task_id")
        task_name = task_info.get("task_name")
        domain = task_info.get("domain")
        print(f"\n[{idx}] Executing: {{task_name}} ({{task_id}}) from {{domain}}")
        try:
        output = run_subtask_0()
        results['aqi_level_trend_analysis'] = output
        output = run_subtask_1()
        results['diurnal_wind_patterns'] = output
        output = run_subtask_2()
        results['cross_correlation_wind_analysis'] = output
        except Exception as e:
            print(f"[ERROR] Failed to execute {{task_name}}: {{e}}")
            results[task_id] = {{"status": "error", "error": str(e)}}
    return results

def analyze_and_combine_results(subtask_results):
    analysis = {'workflow_status':'completed','subtasks_executed': len(subtask_results)}
    metrics = {}
    for tid, res in subtask_results.items():
        if isinstance(res, dict) and res.get('status') == 'success' and 'result_summary' in res:
            for item in res.get('result_summary', []):
                key = f"{tid}_{item.get('key')}"
                metrics[key] = item.get('value')
    analysis['metrics'] = metrics

    return analysis


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
    print('
' + '=' * 80)
    print('[WORKFLOW] AIR QUALITY AND WIND TREND ANALYSIS')
    print('=' * 80)
    print('[DOMAINS] AIR_QUALITY, WIND')
    print('[TIME] ' + datetime.now().isoformat())

    ok, msg = check_resource_constraints()
    print('[RESOURCES] ' + msg)
    if not ok and RESOURCE_CONSTRAINTS.get('skip_if_insufficient', True):
        print('[SKIP] Insufficient resources - aborting')
        return {{'task_name': 'Air Quality and Wind Trend Analysis', 'status': 'skipped', 'reason': msg, 'timestamp': datetime.now().isoformat()}}

    results = execute_subtasks()
    analysis = analyze_and_combine_results(results)

    final = {{
        'task_name': 'Air Quality and Wind Trend Analysis',
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'subtask_results': results,
        'analysis': analysis,
        'result_summary': [{{'key': k, 'value': v}} for k, v in analysis.items()]
    }}

    print('
' + '=' * 80)
    print('[RESULT] FINAL ANALYSIS')
    print('=' * 80)
    for k, v in analysis.items():
        print(f"  {{k:30}} → {{v}}")
    print('=' * 80)
    print('
' + json.dumps(final, indent=2, ensure_ascii=False))
    return final


if __name__ == '__main__':
    res = main()
    sys.exit(0 if res.get('status') == 'success' else 1)
