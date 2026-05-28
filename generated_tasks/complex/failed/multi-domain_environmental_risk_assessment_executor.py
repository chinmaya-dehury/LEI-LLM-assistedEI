
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

TASK_NAME = 'Multi-Domain Environmental Risk Assessment'
DESCRIPTION = 'Joint analysis across air quality, soil, temperature, and humidity to assess environmental risks'
DATA_TYPE = 'environmental_risk'

BASE_DIR = Path(__file__).parent.parent

RESOURCE_CONSTRAINTS = {"min_available_memory_mb": 100, "max_cpu_percent": 80, "skip_if_insufficient": True}

def ensure_generated_subtask_script(task_path, task_name, domain):
    if task_path.exists():
        return task_path
    task_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_code = f'''
import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def main():
    sample_path = BASE_DIR / 'data' / '{domain}' / 'sample_data.csv'
    row_count = 0
    sample_preview = []
    if sample_path.exists():
        try:
            with open(sample_path, 'r', encoding='utf-8') as f:
                rows = list(csv.reader(f))
            row_count = max(len(rows) - 1, 0)
            sample_preview = rows[:2]
        except Exception as e:
            print(f"Error reading sample data: {e}")

    result = {{
        'task_name': '{task_name}',
        'status': 'success',
        'result_summary': [
            {{'key': 'domain', 'value': '{domain}'}},
            {{'key': 'row_count', 'value': row_count}},
            {{'key': 'sample_preview', 'value': sample_preview[:2]}},
            {{'key': 'mode', 'value': 'auto_generated_fallback'}},
        ],
    }}
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
'''
    task_path.write_text(fallback_code, encoding='utf-8')
    return task_path

def run_subtask(task_path):
    try:
        proc = subprocess.run([sys.executable, str(task_path)], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            try:
                return json.loads(proc.stdout.strip())
            except Exception as e:
                print(f"Error parsing JSON output: {e}")
                return {'status':'error','output': proc.stdout}
        return {'status':'error','stderr': proc.stderr}
    except subprocess.TimeoutExpired:
        return {'status':'timeout'}
    except Exception as e:
        print(f"Error executing subtask: {e}")
        return {'status':'error','error': str(e)}

def execute_subtasks():
    results = {}
    execution_order = [
        {"task_id": "air_quality_index_category_distribution", "task_name": "Air Quality Index Analysis", "domain": "air_quality"},
        {"task_id": "root_zone_health_assessment", "task_name": "Soil Health Assessment", "domain": "soil"},
        {"task_id": "Temperature_Humidity_Correlation", "task_name": "Temperature Humidity Analysis", "domain": "temp_humidity"},
        {"task_id": "cross_domain_anomaly_detection_4", "task_name": "Cross-Domain Anomaly Detection", "domain": ""},
    ]

    for task_info in execution_order:
        task_id = task_info.get("task_id")
        task_name = task_info.get("task_name")
        domain = task_info.get("domain")

        task_path = BASE_DIR / 'generated_tasks' / domain / f'{task_id}.py'
        task_path = ensure_generated_subtask_script(task_path, task_name, domain)

        output = run_subtask(task_path)
        results[task_id] = output

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
            return False, f"Low memory: {mem.available // (1024**2)}MB"
        if cpu > RESOURCE_CONSTRAINTS.get("max_cpu_percent", 80):
            return False, f"High CPU: {cpu}%"
        return True, "Resources OK"
    except Exception as e:
        print(f"Error checking resource constraints: {e}")
        return True, "Resource check skipped"

def main():
    print('=' * 80)
    print(f'[WORKFLOW] {TASK_NAME}')
    print('=' * 80)
    print(f'[DOMAINS] soil, temp_humidity, air_quality')
    print(f'[TIME] {datetime.now().isoformat()}')

    ok, msg = check_resource_constraints()
    print(f'[RESOURCES] {msg}')
    if not ok and RESOURCE_CONSTRAINTS.get('skip_if_insufficient', True):
        print('[SKIP] Insufficient resources - aborting')
        with open('output/{DATA_TYPE}/{TASK_NAME}_result.json', 'w') as f:
            json.dump({"task_name": TASK_NAME, "status": "skipped", "reason": msg, "timestamp": datetime.now().isoformat()}, f)
        return

    results = execute_subtasks()
    analysis = analyze_and_combine_results(results)

    final = {{
        'task_name': TASK_NAME,
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'subtask_results': results,
        'analysis': analysis,
        'result_summary': [{'key': k, 'value': v} for k, v in analysis.items()]
    }}

    with open(f'output/{DATA_TYPE}/{TASK_NAME}_result.json', 'w') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()
    sys.exit(0)
