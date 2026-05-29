"""
Generation module for complex task synthesis.
Handles composite task blueprint structuring and dynamic workflow script execution generation.
"""

import os
import sys
import json
import ast
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from string import Template
from .analysis import TaskAnalyzer
import subprocess

# semantic validator
try:
    from val_semantic import _validate_output_structure
except Exception:
    _validate_output_structure = None

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

TEMPLATE_DIR = BASE_DIR / "template"
EXECUTOR_TEMPLATE_PATH = TEMPLATE_DIR / "executor_template.txt"
EXECUTOR_FALLBACK_TEMPLATE_PATH = TEMPLATE_DIR / "executor_template_fallback.txt"
VALIDATOR_COMPLEX_DIR = BASE_DIR / "validator" / "complex"


def _write_validation_record(script_name: str, payload: Dict[str, Any]) -> None:
    """Persist validation metadata under validator/complex."""
    VALIDATOR_COMPLEX_DIR.mkdir(parents=True, exist_ok=True)
    out_val_path = VALIDATOR_COMPLEX_DIR / f"val_{script_name}.json"
    out_val_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_complex_error_log(script_name: str, message: str) -> None:
    """Persist exact complex-generation failures under generated_tasks/complex/error.txt."""
    error_path = BASE_DIR / "generated_tasks" / "complex" / "error.txt"
    error_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] SCRIPT: {script_name}\n{message.strip()}\n{'-' * 60}\n"
    with open(error_path, "a", encoding="utf-8") as handle:
        handle.write(entry)


class CompositeTaskGenerator:
    """Generates complex composite tasks from basic tasks dynamically using true DAG dependencies."""

    def __init__(self, dependency_resolver, config: Dict = None):
        self.resolver = dependency_resolver
        self.config = config or {}
        self.generated_tasks = []

    def generate_composite_task(self, task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a composite task blueprint based on explicit data flow dependencies."""
        subtasks_info = self._analyze_subtasks(task_definition["subtasks"])
        execution_order = self.resolver.topological_sort_tasks(subtasks_info["subtasks"])
        data_flow = self._build_data_flow(subtasks_info["subtasks"], execution_order)

        domains = [d for d in (t.get("domain", "") for t in subtasks_info["subtasks"]) if d and d != "complex"]

        composite_task = {
            "task_name": task_definition["task_name"],
            "task_type": "composite",
            "description": task_definition["description"],
            "business_value": task_definition.get("business_value", ""),
            "final_insight": task_definition.get("final_insight", ""),
            "decision_rules": task_definition.get("decision_rules", []) or [],
            "recommended_action": task_definition.get("recommended_action", ""),
            "domains": sorted(set(domains)),
            "data_type": "complex",
            "subtasks": subtasks_info["subtasks"],
            "execution_order": execution_order,
            "data_flow": data_flow,
            "output_schema": task_definition.get("output_schema", {}),
            "generated_at": datetime.now().isoformat()
        }

        self.generated_tasks.append(composite_task)
        return composite_task

    def print_composite_task_details(self, composite_task: Dict[str, Any]) -> None:
        """Print a concise summary of the generated composite task for logging."""
        name = composite_task.get("task_name", "<unnamed>")
        domains = composite_task.get("domains", [])
        subtasks = composite_task.get("subtasks", []) or []
        execution_order = composite_task.get("execution_order", []) or []

        print(f"[COMPOSITE] {name} | domains={','.join(domains)} | subtasks={len(subtasks)} | execution_order={execution_order}")

    def _analyze_subtasks(self, subtasks: List[Dict]) -> Dict[str, Any]:
        """Analyze availability of subtasks on disk."""
        analyzer = self.resolver.analyzer
        analysis = {"subtasks": subtasks}

        for index, subtask in enumerate(subtasks):
            domain = (subtask.get("domain") or "complex").strip() or "complex"
            subtask["domain"] = domain
            task_id = subtask["task_id"]
            domain_info = analyzer.analyze_domain_tasks(domain)

            if task_id in domain_info["tasks"]:
                subtask["status"] = "available"
            else:
                if task_id == "needs_generation" or not task_id.strip():
                    base_name = subtask.get("subtask_name", "generated_subtask")
                    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in base_name).strip("_") or "generated_subtask"
                    task_id = f"{slug}_{index + 1}"
                    subtask["task_id"] = task_id

                subtask["status"] = "pending_generation"

        return analysis

    def _build_data_flow(self, subtasks: List[Dict], execution_order: List[str]) -> List[Dict]:
        """Build precise data flow dependency links mapping from specific source keys to destination keys."""
        data_flow = []
        for i in range(len(execution_order) - 1):
            from_task = execution_order[i]
            to_task = execution_order[i + 1]

            from_subtask = next((t for t in subtasks if t["subtask_name"] == from_task), {})
            to_subtask = next((t for t in subtasks if t["subtask_name"] == to_task), {})

            from_outputs = from_subtask.get("outputs", [])
            to_inputs = to_subtask.get("inputs", [])

            if from_outputs and to_inputs:
                data_flow.append({
                    "from_subtask_id": from_subtask.get("task_id"),
                    "from_subtask_name": from_task,
                    "to_subtask_id": to_subtask.get("task_id"),
                    "to_subtask_name": to_task,
                    "mapped_variable": from_outputs[0]
                })
        return data_flow


def _validate_python_syntax(code: str) -> tuple[bool, str]:
    """Check whether the supplied Python code parses successfully."""
    if not isinstance(code, str) or not code.strip():
        return False, "Python source is empty"
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"Syntax error at line {exc.lineno}: {exc.msg}"


def _load_executor_template() -> str:
    """Load the executor script template from disk, falling back to a template file."""
    if EXECUTOR_TEMPLATE_PATH.exists():
        return EXECUTOR_TEMPLATE_PATH.read_text(encoding="utf-8")

    if EXECUTOR_FALLBACK_TEMPLATE_PATH.exists():
        return EXECUTOR_FALLBACK_TEMPLATE_PATH.read_text(encoding="utf-8")

    raise FileNotFoundError(
        "Missing executor templates: expected template/executor_template.txt or template/executor_template_fallback.txt"
    )


def _generate_executor_script(composite_task: Dict) -> str:
    """Return the text content of a fully decoupled workflow script."""
    task_name = composite_task.get("task_name", "complex_task")
    description = composite_task.get("description", "")
    domains = composite_task.get("domains", [])
    final_insight = str(composite_task.get("final_insight", "") or "")
    decision_rules = composite_task.get("decision_rules", []) or []
    recommended_action = str(composite_task.get("recommended_action", "") or "")
    subtasks = composite_task.get("subtasks", [])
    data_flow = composite_task.get("data_flow", [])

    subtask_imports = _generate_subtask_imports(subtasks)
    subtask_execution = _generate_subtask_execution(subtasks, data_flow)
    exec_order_json = json.dumps([
        {"task_id": s.get('task_id', ''), "task_name": s.get('subtask_name', ''), "domain": s.get('domain', '')}
        for s in subtasks
    ], indent=4)

    template = _load_executor_template()

    filled = template.replace('{TASK_NAME}', task_name.replace("'", "\\'"))
    filled = filled.replace('{DESCRIPTION}', description.replace("'", "\\'"))
    filled = filled.replace('{DOMAINS}', ', '.join(domains))
    filled = filled.replace('{FINAL_INSIGHT}', final_insight.replace("'", "\\'"))
    filled = filled.replace('{DECISION_RULES}', json.dumps(decision_rules, ensure_ascii=False, indent=4))
    filled = filled.replace('{RECOMMENDED_ACTION}', recommended_action.replace("'", "\\'"))
    filled = filled.replace('{SUBTASK_IMPORTS}', subtask_imports)
    filled = filled.replace('{SUBTASK_EXECUTION}', subtask_execution)
    filled = filled.replace('{EXEC_ORDER}', exec_order_json)
    filled = filled.replace('{TASK_DISPLAY}', task_name.upper())

    return filled


def generate_workflow_executor(composite_task: Dict, output_dir: str = None) -> str:
    """Generate an executable, self-contained Python orchestration script for a composite task."""
    if output_dir is None:
        output_dir = BASE_DIR / "generated_tasks" / "complex"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_name = composite_task.get("task_name", "complex_task").strip().replace(" ", "_").lower()
    script_path = output_dir / f"{script_name}_executor.py"

    try:
        script_content = _generate_executor_script(composite_task)
        syntax_ok, syntax_error = _validate_python_syntax(script_content)
        if not syntax_ok:
            print(f"[ERROR] Generated executor failed basic syntax validation: {syntax_error}")
            # write validation file with error details
            try:
                _write_validation_record(script_name, {
                    'validated_at': datetime.now().isoformat(),
                    'syntax_ok': False,
                    'semantic_passed': False,
                    'repair_attempted': False,
                    'error': syntax_error,
                })
            except Exception:
                pass
            try:
                _append_complex_error_log(script_name, f"Generated executor failed basic syntax validation:\n{syntax_error}")
            except Exception:
                pass
            return None

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        print(f"[OK] Generated dynamic workflow script: {script_path}")
        # run semantic validation up to 3 attempts if semantic validator is available
        validation_record = {
            'validated_at': datetime.now().isoformat(),
            'syntax_ok': True,
            'script_path': str(script_path),
            'semantic_passed': False,
            'repair_attempted': False,
            'semantic': {
                'performed': False,
                'passed': False,
                'attempts': []
            }
        }

        if _validate_output_structure is None:
            # write record saying semantic validator missing
            try:
                validation_record['semantic']['reason'] = 'semantic validator unavailable'
                _write_validation_record(script_name, validation_record)
            except Exception:
                pass
            return str(script_path)

        # attempt execution + semantic validation up to 3 times
        last_error = None
        for attempt in range(1, 4):
            attempt_entry = {'attempt': attempt, 'runtime': None, 'stdout': None, 'stderr': None, 'semantic_passed': False, 'error': None}
            try:
                proc = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, timeout=120)
                attempt_entry['runtime'] = proc.returncode
                attempt_entry['stdout'] = proc.stdout
                attempt_entry['stderr'] = proc.stderr

                parsed = None
                try:
                    if proc.stdout and proc.stdout.strip():
                        parsed = json.loads(proc.stdout.strip())
                except Exception:
                    parsed = None

                # fallback: check expected result file under output/complex/
                if parsed is None:
                    result_path = BASE_DIR / 'output' / 'complex' / f"{script_name}_result.json"
                    if result_path.exists():
                        try:
                            parsed = json.loads(result_path.read_text(encoding='utf-8'))
                        except Exception as e:
                            attempt_entry['error'] = f"Failed to parse result file: {e}"

                if parsed is None:
                    attempt_entry['error'] = attempt_entry.get('error') or 'No JSON output produced'
                    last_error = attempt_entry['error']
                    validation_record['semantic']['attempts'].append(attempt_entry)
                    continue

                # run semantic validator
                try:
                    validated_obj, sem_error, sem_details = _validate_output_structure(
                        parsed,
                        composite_task.get('task_name', script_name),
                        composite_task.get('description', ''),
                        script_content,
                        sample_data='',
                        min_results=0,
                    )
                    attempt_entry['semantic_passed'] = validated_obj is not None and sem_error is None
                    attempt_entry['semantic_details'] = sem_details
                    if validated_obj is not None and sem_error is None:
                        validation_record['semantic']['performed'] = True
                        validation_record['semantic']['passed'] = True
                        validation_record['semantic_passed'] = True
                        validation_record['semantic']['attempts'].append(attempt_entry)
                        # write validation file and return
                        try:
                            _write_validation_record(script_name, validation_record)
                        except Exception:
                            pass
                        return str(script_path)
                    else:
                        attempt_entry['error'] = sem_error or 'Semantic validation failed'
                        last_error = attempt_entry['error']
                        validation_record['semantic']['attempts'].append(attempt_entry)
                        continue
                except Exception as e:
                    attempt_entry['error'] = f"Semantic validator exception: {e}"
                    last_error = attempt_entry['error']
                    validation_record['semantic']['attempts'].append(attempt_entry)
                    continue

            except subprocess.TimeoutExpired:
                attempt_entry['error'] = 'Execution timed out'
                last_error = attempt_entry['error']
                validation_record['semantic']['attempts'].append(attempt_entry)
                continue
            except Exception as e:
                attempt_entry['error'] = f'Execution failed: {e}'
                last_error = attempt_entry['error']
                validation_record['semantic']['attempts'].append(attempt_entry)
                continue

        # all attempts exhausted, write validation record with last error
        validation_record['semantic']['performed'] = True
        validation_record['semantic']['passed'] = False
        validation_record['semantic_passed'] = False
        validation_record['semantic']['last_error'] = last_error
        try:
            _write_validation_record(script_name, validation_record)
        except Exception:
            pass
        try:
            _append_complex_error_log(script_name, f"Executor validation exhausted all attempts:\n{last_error or 'unknown error'}")
        except Exception:
            pass

        return str(script_path)
    except Exception as e:
        print(f"[ERROR] Failed to generate executor payload: {e}")
        return None


def _generate_subtask_imports(subtasks: List[Dict]) -> str:
    """Generate dynamic wrapper functions that pipe data to scripts, processing system standard streams natively."""
    parts = []
    parts.append(
        "def ensure_generated_subtask_script(task_path, task_name, domain):\n"
        "    # If the script already exists and is not inside the complex folder, use it.\n"
        "    if task_path.exists() and task_path.parent.name != 'complex':\n"
        "        return task_path\n"
        "    # Place missing/auto-generated complex subtasks into generated_tasks/complex/missing\n"
        "    if str(domain).strip() in ('complex', '') or task_path.parent.name == 'complex':\n"
        "        task_path = BASE_DIR / 'generated_tasks' / 'complex' / 'missing' / task_path.name\n"
        "    task_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "    fallback_template_path = TEMPLATE_DIR / 'subtask_fallback_template.txt'\n"
        "    fallback_code = Template(fallback_template_path.read_text(encoding='utf-8')).safe_substitute(domain=domain, task_name=task_name)\n"
        "    task_path.write_text(fallback_code, encoding='utf-8')\n"
        "    return task_path\n"
    )

    for idx, s in enumerate(subtasks):
        task_id = s.get('task_id', '')
        domain = s.get('domain', '')
        task_name = s.get('subtask_name', task_id or 'generated_subtask')
        fn_name = f"run_subtask_{idx}"
        
        parts.append(
            f"def {fn_name}(specific_dependencies=None):\n"
            f"    task_path = BASE_DIR / 'generated_tasks' / '{domain}' / '{task_id}.py'\n"
            f"    task_path = ensure_generated_subtask_script(task_path, {task_name!r}, {domain!r})\n"
            f"    try:\n"
            f"        input_str = json.dumps(specific_dependencies) if specific_dependencies else None\n"
            f"        proc = subprocess.run([sys.executable, str(task_path)], input=input_str, capture_output=True, text=True, timeout=120)\n"
            f"        if proc.returncode == 0 and proc.stdout:\n"
            f"            try:\n"
            f"                return json.loads(proc.stdout.strip())\n"
            f"            except Exception:\n"
            f"                pass\n"
            f"        result_path = BASE_DIR / 'output' / '{domain}' / '{task_id}_result.json'\n"
            f"        if result_path.exists():\n"
            f"            try:\n"
            f"                return json.loads(result_path.read_text(encoding='utf-8'))\n"
            f"            except Exception as file_error:\n"
            f"                return {{'status':'error','error': f'Invalid result file JSON: {{file_error}}', 'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}}\n"
            f"        return {{'status':'error','stderr': proc.stderr, 'returncode': proc.returncode, 'stdout': proc.stdout}}\n"
            f"    except Exception as e:\n"
            f"        return {{'status':'error','error': str(e)}}\n"
        )
    return '\n'.join(parts)


def _generate_subtask_execution(subtasks: List[Dict], data_flow: List[Dict]) -> str:
    """Generate sequential execution code that forwards upstream results into downstream subtasks."""
    lines = []
    task_name_to_id = {
        s.get('subtask_name', ''): s.get('task_id', '')
        for s in subtasks
        if s.get('subtask_name', '')
    }
    data_flow_json = json.dumps(data_flow, indent=4)

    lines.append(f"    task_name_to_id = {json.dumps(task_name_to_id, indent=4)}")
    lines.append(f"    data_flow = {data_flow_json}")

    for idx, s in enumerate(subtasks):
        task_id = s.get('task_id', '')
        task_name = s.get('subtask_name', '')
        fn_name = f"run_subtask_{idx}"

        lines.append(f"    # --- Node Step {idx + 1}: {task_name} ---")
        lines.append(f"    dependencies_{idx} = {{}}")
        lines.append(f"    inbound_links_{idx} = [link for link in data_flow if link.get('to_subtask_id') == {task_id!r} or link.get('to_subtask_name') == {task_name!r}]")
        lines.append(f"    for link in inbound_links_{idx}:")
        lines.append("        source_task_id = link.get('from_subtask_id') or task_name_to_id.get(link.get('from_subtask_name'), link.get('from_subtask_name'))")
        lines.append("        source_result = results.get(source_task_id, {})")
        lines.append("        if source_result.get('status') == 'error':")
        lines.append("            print(f\"[DEPENDENCY BLOCKED] {link.get('from_subtask_name')} failed; downstream task will receive no propagated payload.\")")
        lines.append("            continue")
        lines.append("        if source_result.get('status') == 'mock_fallback_active':")
        lines.append("            print(f\"[DATA REJECTION] {link.get('from_subtask_name')} returned placeholder output; forwarding metadata only.\")")
        lines.append(f"        dependencies_{idx}[link.get('mapped_variable', 'upstream_output')] = source_result")
        lines.append(f"    output_{idx} = {fn_name}(specific_dependencies=dependencies_{idx})")
        lines.append(f"    results['{task_id}'] = output_{idx}\n")

    return '\n'.join(lines)


__all__ = ["CompositeTaskGenerator", "generate_workflow_executor", "generate_complex_tasks_llm"]


def generate_complex_tasks_llm(*args, **kwargs):
    """Generate composite task specs by calling the configured LLM.

    The function collects domain/task summaries and prompts the LLM using
    `template/get_complex_task_template.txt`. Expected output is a JSON
    array following the template schema. Returns True and writes the
    canonical file on success, otherwise returns False.
    """
    try:
        # Lazy import LLM client to avoid import-time config issues
        # Prefer repo llm_client but fall back to openai package if needed
        chat_completion = None
        _config = None
        try:
            from archive.llm_client import chat_completion as _repo_chat
            chat_completion = _repo_chat
            import config as _cfg
            _config = _cfg
        except Exception:
            try:
                import openai
                import config as _cfg
                _config = _cfg

                def _openai_chat_completion(*, model: str, messages: List[Dict], **kwargs):
                    # messages: list of {role, content}
                    chat_resp = openai.ChatCompletion.create(model=model, messages=messages, **kwargs)
                    return chat_resp

                chat_completion = _openai_chat_completion
            except Exception as e:
                print(f"[WARNING] LLM client not available: {e}")
                return False

        # Build analyzer and domain summaries
        analyzer = TaskAnalyzer(generated_tasks_dir=str(BASE_DIR / "generated_tasks"))
        domains = analyzer.discover_all_domains()

        domains_and_tasks_lines = []
        domain_metadata = []
        domain_samples = []

        for d in domains:
            info = analyzer.analyze_domain_tasks(d)
            tasks_list = []
            for tid, tinfo in info.get("tasks", {}).items():
                tasks_list.append(f"- {tid}: {tinfo.get('primary_function','')}")

            domains_and_tasks_lines.append(f"{d}:\n" + "\n".join(tasks_list) if tasks_list else f"{d}: (no tasks)")

            domain_metadata.append(f"{d}: tasks={info.get('task_count',0)}, capabilities={','.join(sorted(info.get('capabilities',[]))) }")

            # sample row counts
            sample_path = BASE_DIR / 'data' / d / 'sample_data.csv'
            row_count = -1
            try:
                if sample_path.exists():
                    with open(sample_path, 'r', encoding='utf-8') as sf:
                        row_count = max(len(list(sf)) - 1, 0)
            except Exception:
                row_count = -1
            domain_samples.append(f"{d}: sample_rows={row_count}")

        domains_and_tasks = "\n\n".join(domains_and_tasks_lines)
        domain_metadata_text = "\n".join(domain_metadata)
        domain_samples_text = "\n".join(domain_samples)

        # load prompt template
        prompt_tpl_path = TEMPLATE_DIR / 'get_complex_task_template.txt'
        if not prompt_tpl_path.exists():
            print("[ERROR] Missing prompt template: template/get_complex_task_template.txt")
            return False

        raw = prompt_tpl_path.read_text(encoding='utf-8')
        # extract triple-quoted USER_PROMPT_TEMPLATE content
        start = raw.find('USER_PROMPT_TEMPLATE')
        if start != -1:
            first_quote = raw.find('"""', start)
            last_quote = raw.rfind('"""')
            if first_quote != -1 and last_quote != -1 and last_quote > first_quote:
                user_prompt = raw[first_quote+3:last_quote]
            else:
                user_prompt = raw
        else:
            user_prompt = raw

        filled = user_prompt.replace('$DOMAINS_AND_TASKS', domains_and_tasks)
        filled = filled.replace('$DOMAIN_METADATA', domain_metadata_text)
        filled = filled.replace('$DOMAIN_SAMPLES', domain_samples_text)
        filled = filled.replace('$DOMAIN_CONTEXTS', '')
        filled = filled.replace('$RESOURCE_STATS', '')
        filled = filled.replace('$EXISTING_COMPOSITE_TASKS', '[]')

        messages = [
            {"role": "user", "content": filled}
        ]

        model = getattr(_config, 'DEFAULT_MODEL', 'gpt-4o-mini')
        try:
            resp = chat_completion(model=model, messages=messages, temperature=0.0, max_tokens=1024)
        except Exception as e:
            print(f"[WARNING] LLM call failed: {e}")
            return False

        # extract text
        text = ""
        try:
            if getattr(resp, 'choices', None):
                choice0 = resp.choices[0]
                msg = getattr(choice0, 'message', None)
                if msg:
                    text = getattr(msg, 'content', '') or getattr(msg, 'reasoning', '') or ''
            if not text and hasattr(resp, 'model_dump'):
                dump = resp.model_dump()
                ch0 = (dump.get('choices') or [{}])[0]
                md = ch0.get('message') or {}
                text = (md.get('content') or md.get('reasoning') or '')
        except Exception:
            text = ''

        if not text:
            print('[WARNING] LLM returned empty response')
            return False

        # try to extract JSON array from text
        try:
            # find first '['
            start_idx = text.find('[')
            if start_idx == -1:
                print('[WARNING] No JSON array found in LLM response')
                return False
            json_blob = text[start_idx:]
            composite_list = json.loads(json_blob)
            if not isinstance(composite_list, list):
                print('[WARNING] LLM output is not a JSON array')
                return False
        except Exception as e:
            print(f"[WARNING] Failed to parse LLM JSON output: {e}")
            return False

        def _slugify(text: str) -> str:
            return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(text)).strip("_") or "generated_subtask"

        def _normalize_data_flow(entries, subtasks):
            normalized = []
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        normalized.append(entry)
                        continue
                    if not isinstance(entry, str):
                        continue
                    parts = [p.strip() for p in entry.split("->") if p.strip()]
                    if len(parts) != 2:
                        continue
                    left, right = parts
                    from_name = left.split(".")[0].strip()
                    to_name = right.split(".")[0].strip()
                    mapped_variable = left.split(".")[-1].strip() if "." in left else "output"
                    from_task = next((s for s in subtasks if s.get("subtask_name") == from_name), {})
                    to_task = next((s for s in subtasks if s.get("subtask_name") == to_name), {})
                    normalized.append({
                        "from_subtask_id": from_task.get("task_id", ""),
                        "from_subtask_name": from_name,
                        "to_subtask_id": to_task.get("task_id", ""),
                        "to_subtask_name": to_name,
                        "mapped_variable": mapped_variable,
                    })
            return normalized

        normalized_list = []
        for idx, item in enumerate(composite_list):
            if not isinstance(item, dict):
                continue

            task_name = str(item.get("task_name", f"composite_task_{idx + 1}")).strip()
            domains = item.get("domains", [])
            if isinstance(domains, str):
                domains = [d.strip() for d in domains.split(",") if d.strip()]
            domains = [d for d in domains if d]

            subtasks = []
            for sub_idx, subtask in enumerate(item.get("subtasks", []) or []):
                if not isinstance(subtask, dict):
                    continue
                subtask_name = str(subtask.get("subtask_name", f"subtask_{sub_idx + 1}")).strip() or f"subtask_{sub_idx + 1}"
                task_id = str(subtask.get("task_id", "")).strip()
                if not task_id:
                    task_id = "needs_generation"
                domain = str(subtask.get("domain", "")).strip()
                if not domain:
                    domain = "complex" if task_id == "needs_generation" else (domains[0] if domains else "complex")
                depends_on = subtask.get("depends_on", [])
                if not isinstance(depends_on, list):
                    depends_on = [depends_on] if depends_on else []
                subtasks.append({
                    "subtask_name": subtask_name,
                    "task_id": task_id,
                    "domain": domain,
                    "depends_on": depends_on,
                })

            normalized_item = {
                "task_name": task_name,
                "description": str(item.get("description", "")).strip(),
                "business_value": str(item.get("business_value", "")).strip(),
                "final_insight": str(item.get("final_insight", "")).strip(),
                "decision_rules": item.get("decision_rules", []) if isinstance(item.get("decision_rules", []), list) else [str(item.get("decision_rules", "")).strip()] if str(item.get("decision_rules", "")).strip() else [],
                "recommended_action": str(item.get("recommended_action", "")).strip(),
                "domains": domains,
                "data_type": item.get("data_type", "complex"),
                "subtasks": subtasks,
                "missing_capabilities": [],
                "data_flow": _normalize_data_flow(item.get("data_flow", []), subtasks),
            }

            missing_capabilities = []
            raw_missing = item.get("missing_capabilities", []) or []
            if isinstance(raw_missing, str):
                raw_missing = [raw_missing]
            for cap in raw_missing:
                cap_text = str(cap).strip()
                if cap_text and cap_text != "needs_generation":
                    missing_capabilities.append(cap_text)

            if not missing_capabilities:
                missing_capabilities = [
                    sub.get("subtask_name", "")
                    for sub in subtasks
                    if sub.get("task_id") == "needs_generation" and sub.get("subtask_name", "")
                ]

            normalized_item["missing_capabilities"] = missing_capabilities
            normalized_list.append(normalized_item)

        # persist to generated_tasks/complex/complex_tasks_list.json
        out_dir = BASE_DIR / 'generated_tasks' / 'complex'
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'complex_tasks_list.json'
        payload = {
            'generated_at': datetime.now().isoformat(),
            'composite_tasks': normalized_list
        }
        try:
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"[OK] Wrote composite tasks to: {out_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write composite tasks file: {e}")
            return False

    except Exception as exc:
        print(f"[ERROR] generate_complex_tasks_llm unexpected error: {exc}")
        return False