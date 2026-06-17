import re
"""
Auto-generated Complex Task Executor
Task: Predictive Irrigation
Description: Predict optimal irrigation schedules based on weather forecasts and soil moisture data.
Domains: lab-data, meteo-data
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from string import Template


def find_project_root() -> Path:
    """Find the absolute project root independent of script execution location."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / 'requirements.txt').exists() or (parent / 'config.py').exists() or (parent / '.git').exists():
            return parent
    return current.parent.parent


BASE_DIR = find_project_root()
TEMPLATE_DIR = BASE_DIR / "template"

FINAL_INSIGHT = 'Recommend irrigation volume based on predicted rainfall and current soil moisture levels.'
DECISION_RULES = [
    "If meteo_data_analyze_temperature predicts rain within 24 hours, reduce irrigation volume.",
    "If soil moisture levels are above a threshold, reduce or suspend irrigation.",
    "If soil moisture levels are below a threshold, increase irrigation volume."
]
RECOMMENDED_ACTION = 'Adjust irrigation system settings.'


def _metric_label(item, fallback_prefix):
    label = str(item.get('name') or item.get('key') or '').strip()
    if not label:
        label = f'{fallback_prefix}_metric'
    return label


def _pretty_metric_key(label):
    return label.lower().replace(' ', '_').replace('/', '_')

def ensure_generated_subtask_script(task_path, task_name, domain):
    # If the script already exists and is not inside the complex folder, use it.
    if task_path.exists() and task_path.parent.name != 'complex':
        return task_path
    # Place missing/auto-generated complex subtasks into generated_tasks/complex/missing
    if str(domain).strip() in ('complex', '') or task_path.parent.name == 'complex':
        task_path = BASE_DIR / 'generated_tasks' / 'complex' / 'missing' / task_path.name
    if task_path.exists():
        return task_path
    task_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_template_path = TEMPLATE_DIR / 'subtask_fallback_template.txt'
    fallback_code = Template(fallback_template_path.read_text(encoding='utf-8')).safe_substitute(domain=domain, task_name=task_name)
    task_path.write_text(fallback_code, encoding='utf-8')
    return task_path

def run_subtask_0(specific_dependencies=None):
    task_path = BASE_DIR / 'generated_tasks' / 'meteo-data' / 'meteo_data_analyze_temperature.py'
    task_path = ensure_generated_subtask_script(task_path, 'Analyze Weather Forecast', 'meteo-data')
    try:
        input_str = json.dumps(specific_dependencies) if specific_dependencies else None
        proc = subprocess.run([sys.executable, str(task_path)], input=input_str, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            try:
                return json.loads(proc.stdout.strip())
            except Exception:
                pass
        result_path = BASE_DIR / 'output' / 'meteo-data' / 'meteo_data_analyze_temperature_result.json'
        if result_path.exists():
            try:
                return json.loads(result_path.read_text(encoding='utf-8'))
            except Exception as file_error:
                return {'status':'error','error': f'Invalid result file JSON: {file_error}', 'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}
        return {'status':'error','stderr': proc.stderr, 'returncode': proc.returncode, 'stdout': proc.stdout}
    except Exception as e:
        return {'status':'error','error': str(e)}

def run_subtask_1(specific_dependencies=None):
    task_path = BASE_DIR / 'generated_tasks' / 'lab-data' / 'read_soil_moisture_2.py'
    task_path = ensure_generated_subtask_script(task_path, 'Read Soil Moisture', 'lab-data')
    try:
        input_str = json.dumps(specific_dependencies) if specific_dependencies else None
        proc = subprocess.run([sys.executable, str(task_path)], input=input_str, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout:
            try:
                return json.loads(proc.stdout.strip())
            except Exception:
                pass
        result_path = BASE_DIR / 'output' / 'lab-data' / 'read_soil_moisture_2_result.json'
        if result_path.exists():
            try:
                return json.loads(result_path.read_text(encoding='utf-8'))
            except Exception as file_error:
                return {'status':'error','error': f'Invalid result file JSON: {file_error}', 'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}
        return {'status':'error','stderr': proc.stderr, 'returncode': proc.returncode, 'stdout': proc.stdout}
    except Exception as e:
        return {'status':'error','error': str(e)}



def execute_subtasks():
    """Execute all subtasks dynamically, enforcing isolated dependency data paths."""
    results = {}
    # Attempt to load canonical composite spec to populate execution_order and data_flow.
    try:
        spec_path = BASE_DIR / "generated_tasks" / "complex" / "complex_tasks_list.json"
        if spec_path.exists():
            spec_json = json.loads(spec_path.read_text(encoding="utf-8"))
            comp = next((c for c in spec_json.get("composite_tasks", []) if c.get("task_name") == "Predictive Irrigation"), None)
            if comp:
                # Build execution_order from spec subtasks while preserving any generator-provided order as fallback
                execution_order = []
                for s in comp.get("subtasks", []):
                    execution_order.append({
                        "task_id": s.get("task_id", ""),
                        "task_name": s.get("subtask_name", ""),
                        "domain": s.get("domain", "")
                    })
                data_flow = comp.get("data_flow", [])
                # If IDs in data_flow are empty, fill them from subtasks mapping
                id_map = {s.get("subtask_name").lower().replace(" ", "_"): s.get("task_id") for s in comp.get("subtasks", []) if s.get("task_id")}
                for link in data_flow:
                    if not link.get("from_subtask_id"):
                        key = (link.get("from_subtask_name") or "").lower().replace(" ", "_")
                        link["from_subtask_id"] = id_map.get(key, link.get("from_subtask_id") or "")
                    if not link.get("to_subtask_id"):
                        key = (link.get("to_subtask_name") or "").lower().replace(" ", "_")
                        link["to_subtask_id"] = id_map.get(key, link.get("to_subtask_id") or "")
            else:
                execution_order = [
    {
        "task_id": "meteo_data_analyze_temperature",
        "task_name": "Analyze Weather Forecast",
        "domain": "meteo-data"
    },
    {
        "task_id": "read_soil_moisture_2",
        "task_name": "Read Soil Moisture",
        "domain": "lab-data"
    }
]
                data_flow = []
        else:
            execution_order = [
    {
        "task_id": "meteo_data_analyze_temperature",
        "task_name": "Analyze Weather Forecast",
        "domain": "meteo-data"
    },
    {
        "task_id": "read_soil_moisture_2",
        "task_name": "Read Soil Moisture",
        "domain": "lab-data"
    }
]
            data_flow = []
    except Exception:
        execution_order = [
    {
        "task_id": "meteo_data_analyze_temperature",
        "task_name": "Analyze Weather Forecast",
        "domain": "meteo-data"
    },
    {
        "task_id": "read_soil_moisture_2",
        "task_name": "Read Soil Moisture",
        "domain": "lab-data"
    }
]
        data_flow = []

    print(f"[WORKFLOW] Running {len(execution_order)} subtasks across automated dependency layers...")

    task_name_to_id = {
    "Analyze Weather Forecast": "meteo_data_analyze_temperature",
    "Read Soil Moisture": "read_soil_moisture_2"
}
    data_flow = []
    # --- Node Step 1: Analyze Weather Forecast ---
    dependencies_0 = {}
    inbound_links_0 = [link for link in data_flow if link.get('to_subtask_id') == 'meteo_data_analyze_temperature' or link.get('to_subtask_name') == 'Analyze Weather Forecast']
    for link in inbound_links_0:
        source_task_id = link.get('from_subtask_id') or task_name_to_id.get(link.get('from_subtask_name'), link.get('from_subtask_name'))
        source_result = results.get(source_task_id, {})
        if source_result.get('status') == 'error':
            print(f"[DEPENDENCY BLOCKED] {link.get('from_subtask_name')} failed; downstream task will receive no propagated payload.")
            continue
        if source_result.get('status') == 'mock_fallback_active':
            print(f"[DATA REJECTION] {link.get('from_subtask_name')} returned placeholder output; forwarding metadata only.")
        dependencies_0[link.get('mapped_variable', 'upstream_output')] = source_result
    output_0 = run_subtask_0(specific_dependencies=dependencies_0)
    results['meteo_data_analyze_temperature'] = output_0

    # --- Node Step 2: Read Soil Moisture ---
    dependencies_1 = {}
    inbound_links_1 = [link for link in data_flow if link.get('to_subtask_id') == 'read_soil_moisture_2' or link.get('to_subtask_name') == 'Read Soil Moisture']
    for link in inbound_links_1:
        source_task_id = link.get('from_subtask_id') or task_name_to_id.get(link.get('from_subtask_name'), link.get('from_subtask_name'))
        source_result = results.get(source_task_id, {})
        if source_result.get('status') == 'error':
            print(f"[DEPENDENCY BLOCKED] {link.get('from_subtask_name')} failed; downstream task will receive no propagated payload.")
            continue
        if source_result.get('status') == 'mock_fallback_active':
            print(f"[DATA REJECTION] {link.get('from_subtask_name')} returned placeholder output; forwarding metadata only.")
        dependencies_1[link.get('mapped_variable', 'upstream_output')] = source_result
    output_1 = run_subtask_1(specific_dependencies=dependencies_1)
    results['read_soil_moisture_2'] = output_1


    return results


def analyze_and_combine_results(subtask_results):
    """
    Analyzes subtask results and combines them to determine an irrigation schedule.
    """
    workflow_status = 'completed'
    subtasks_executed = len(subtask_results)
    summary_metrics = {}
    interpreted_conclusion = 'No specific conclusion'
    final_insight = 'No final insight'
    recommended_action = 'No recommended action'

    for task_id, subtask in subtask_results.items():
        if subtask['status'] == 'available':
            if subtask['subtask_name'] == "Analyze Weather Forecast":
                try:
                    if 'result_summary' in subtask and len(subtask['result_summary']) > 0:
                        summary_metrics[f'{subtask["subtask_name"]}_rain_predicted'] = subtask['result_summary'][0].get('key', False)
                    else:
                        summary_metrics[f'{subtask["subtask_name"]}_rain_predicted'] = False
                except:
                    summary_metrics[f'{subtask["subtask_name"]}_rain_predicted'] = False
            elif subtask['subtask_name'] == "Read Soil Moisture":
                try:
                    if 'result_summary' in subtask and len(subtask['result_summary']) > 0:
                        summary_metrics[f'{subtask["subtask_name"]}_soil_moisture'] = subtask['result_summary'][0].get('value', 0.0)
                    else:
                        summary_metrics[f'{subtask["subtask_name"]}_soil_moisture'] = 0.0
                except:
                    summary_metrics[f'{subtask["subtask_name"]}_soil_moisture'] = 0.0

    # Decision Rules Implementation
    rain_predicted = summary_metrics.get(f'meteo_data_analyze_temperature_rain_predicted', False)
    soil_moisture = summary_metrics.get(f'read_soil_moisture_2_soil_moisture', 0.0)

    if rain_predicted:
        interpreted_conclusion = "Rain is predicted within 24 hours."
        final_insight = "Rainfall is expected, adjust irrigation accordingly."
        recommended_action = "Reduce irrigation volume."
    elif soil_moisture > 30.0:
        interpreted_conclusion = "Soil moisture levels are above the threshold."
        final_insight = "High soil moisture, consider reducing or suspending irrigation."
        recommended_action = "Reduce or suspend irrigation."
    elif soil_moisture < 20.0:
        interpreted_conclusion = "Soil moisture levels are below the threshold."
        final_insight = "Low soil moisture, increase irrigation volume."
        recommended_action = "Increase irrigation volume."

    result = {
        'workflow_status': workflow_status,
        'subtasks_executed': subtasks_executed,
        'summary_metrics': summary_metrics,
        'interpreted_conclusion': interpreted_conclusion,
        'final_insight': final_insight,
        'recommended_action': recommended_action
    }

    return result


def main():
    print('
' + '=' * 80)
    print('[WORKFLOW] PREDICTIVE IRRIGATION')
    print('=' * 80)

    results = execute_subtasks()
    analysis = analyze_and_combine_results(results)

    dynamic_insight = analysis.get('final_insight') or FINAL_INSIGHT
    dynamic_action = analysis.get('recommended_action') or RECOMMENDED_ACTION

    final_payload = {
        'task_name': 'Predictive Irrigation',
        'status': 'success' if analysis['workflow_status'] == 'completed' else ('partial_success' if analysis['workflow_status'] == 'hybrid_integrity' else analysis['workflow_status']),
        'timestamp': datetime.now().isoformat(),
        'subtask_results': results,
        'combined_analysis': analysis,
        'final_insight': dynamic_insight,
        'recommended_action': dynamic_action
    }

    result_dir = BASE_DIR / 'output' / 'complex'
    result_dir.mkdir(parents=True, exist_ok=True)
    result_filename = 'Predictive Irrigation'.replace(' ', '_').replace('-', '_').lower() + '_result.json'
    result_path = result_dir / result_filename
    result_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding='utf-8')

    print('
' + '=' * 80)
    print('[RESULT] COMBINED METRICS PAYLOAD')
    print('=' * 80)
    print(f"Status: {final_payload['status']}")
    print(f"Tasks executed: {final_payload['combined_analysis']['subtasks_executed']}")
    print("Metrics:")
    if final_payload['combined_analysis']['summary_metrics']:
        for metric_name, metric_value in final_payload['combined_analysis']['summary_metrics'].items():
            print(f"  - {metric_name}: {metric_value}")
    else:
        print("  - No summary metrics were produced.")
    if dynamic_insight:
        print(f"Final insight: {dynamic_insight}")
    if DECISION_RULES:
        print("Decision rules:")
        for rule in DECISION_RULES:
            print(f"  - {rule}")
    if dynamic_action:
        print(f"Recommended action: {dynamic_action}")
    print(f"Conclusion: {final_payload['combined_analysis']['interpreted_conclusion']}")
    print(f"Result written to: {result_path}")
    print('=' * 80)
    return final_payload


if __name__ == '__main__':
    main()