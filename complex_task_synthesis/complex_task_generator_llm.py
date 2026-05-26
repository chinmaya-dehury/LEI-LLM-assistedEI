"""
Complex Task Generator using LLM
Dynamically generates composite task specifications by analyzing available domains.
Similar to task_generator.py but for complex tasks.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from openai import OpenAI

# Add parent directory to path for imports
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL
from shared_utils import (
    extract_first_json_object,
    get_environment_vars,
    setup_timing_paths,
    sanitize_model_name,
    IST,
)

# Setup paths
DATA_DIR = BASE_DIR / "data"
GENERATED_TASKS_DIR = BASE_DIR / "generated_tasks"
OUTPUT_DIR = BASE_DIR / "output" / "complex_tasks_generated"
COMPOSITE_TASKS_PATH = GENERATED_TASKS_DIR / "complex" / "complex_tasks_list.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
COMPOSITE_TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)

# Setup environment
env_vars = get_environment_vars()
RUN_ID = env_vars["RUN_ID"]
RUN_COUNT = env_vars["RUN_COUNT"]

# Import prompt
sys.path.insert(0, str(BASE_DIR / "prompts"))
from get_complex_tasks import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def discover_domains_with_tasks():
    """Discover all domains and their available tasks."""
    # Import from current package
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    from task_analyzer import TaskAnalyzer
    
    analyzer = TaskAnalyzer(generated_tasks_dir=str(GENERATED_TASKS_DIR))
    domains = analyzer.discover_all_domains()
    
    domains_info = {}
    for domain in domains:
        domain_analysis = analyzer.analyze_domain_tasks(domain)
        domains_info[domain] = {
            "task_count": domain_analysis["task_count"],
            "tasks": [
                {
                    "task_id": name,
                    "description": info.get("docstring", "")[:100],
                    "primary_function": info.get("primary_function", "unknown"),
                    "complexity": info.get("complexity", 5),
                }
                for name, info in list(domain_analysis["tasks"].items())[:15]
            ],
            "capabilities": list(domain_analysis["capabilities"]),
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
        formatted.append(f"  Capabilities: {', '.join(info['capabilities'][:5])}")
        formatted.append(f"  Sample tasks:")
        
        for task in info["tasks"][:5]:
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


def call_llm_for_complex_tasks(domains_info, samples, resource_stats, existing_tasks):
    """Call LLM to generate complex task specifications."""
    
    # Format information for prompt
    domains_and_tasks = format_domains_info(domains_info)
    domain_samples = format_samples(samples)
    resource_info = json.dumps(resource_stats, indent=2)[:500]
    existing_info = json.dumps(existing_tasks, indent=2)[:500] if existing_tasks else "[]"
    
    # Build user prompt
    user_prompt = Template(USER_PROMPT_TEMPLATE).substitute(
        DOMAINS_AND_TASKS=domains_and_tasks,
        DOMAIN_SAMPLES=domain_samples,
        RESOURCE_STATS=resource_info,
        EXISTING_COMPOSITE_TASKS=existing_info,
    )
    
    print("\n[LLM] Calling LLM for complex task generation...")
    print(f"[LLM] Model: {DEFAULT_MODEL}")
    
    start_time = datetime.now(IST).isoformat()
    start_perf = time.perf_counter()
    
    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
            top_p=0.95,
        )
        
        elapsed = time.perf_counter() - start_perf
        end_time = datetime.now(IST).isoformat()
        
        print(f"[LLM] Completed in {elapsed:.2f}s")
        
        # Extract JSON from response
        response_text = response.choices[0].message.content
        composite_tasks_list = extract_first_json_object(response_text)
        
        if not isinstance(composite_tasks_list, list):
            if isinstance(composite_tasks_list, dict):
                composite_tasks_list = [composite_tasks_list]
            else:
                composite_tasks_list = []
        
        return {
            "composite_tasks": composite_tasks_list,
            "status": "success",
            "llm_model": DEFAULT_MODEL,
            "start_time": start_time,
            "end_time": end_time,
            "duration_sec": elapsed,
            "token_usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        }
    
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        return {
            "composite_tasks": [],
            "status": "failed",
            "error": str(e),
        }


def save_complex_tasks(generated_data):
    """Save generated complex task specifications."""
    output_file = OUTPUT_DIR / f"complex_tasks_{sanitize_model_name(DEFAULT_MODEL)}_{RUN_ID}.json"
    
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
        # Create a normalized signature to detect near-duplicates
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
            # skip near-duplicate
            continue
        existing_sigs[sig] = t
        new_tasks.append(t)

    # Rebuild existing list from signatures to keep deterministic order
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

    # Create a validator manifest for all known composite tasks (so existing code in complex/ is validated)
    try:
        tasks_manifest_path = GENERATED_TASKS_DIR / "complex" / "new_tasks.json"
        manifest = {"tasks": []}
        for t in existing:
            safe_name = (t.get("task_name") or "").strip()
            manifest["tasks"].append({
                "task_name": safe_name,
                "description": t.get("description", ""),
                "data_type": "complex",
            })

        with open(tasks_manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2, ensure_ascii=False)

        print(f"[OK] Validator manifest written: {tasks_manifest_path}")

        # Attempt to run validator on the complex tasks (importing validator)
        try:
            import validator as task_validator
            print("[Validator] Running validator on complex tasks...")
            val_result = task_validator.validate_all_generated_tasks(str(tasks_manifest_path), str(GENERATED_TASKS_DIR / "complex"))
            print(f"[Validator] Validation summary: {val_result.get('summary', {})}")
        except Exception as ve:
            print(f"[WARNING] Validator run failed: {ve}")

    except Exception as e:
        print(f"[ERROR] Failed to write validator manifest: {e}")

    return len(new_tasks)


def generate_complex_tasks_llm():
    """Main function to generate complex tasks using LLM."""
    
    print("\n" + "=" * 80)
    print("COMPLEX TASK SYNTHESIS - LLM-DRIVEN GENERATION")
    print("=" * 80)
    
    # Discover domains and tasks
    print("\n[1] Discovering available domains and tasks...")
    domains_info = discover_domains_with_tasks()
    print(f"    Found {len(domains_info)} domains")
    for domain, info in domains_info.items():
        print(f"      [{domain:15}] {info['task_count']:3} tasks | {len(info['capabilities'])} capabilities")
    
    if not domains_info:
        print("[INFO] No domains found. Generate tasks first using task_generator.py")
        return
    
    # Load samples and metadata
    print("\n[2] Loading domain samples and metadata...")
    samples = load_domain_samples()
    print(f"    Loaded data for {len(samples)} domains")
    
    # Load resource stats
    print("\n[3] Loading resource constraints...")
    resource_stats = load_resource_stats()
    
    # Load existing composite tasks
    print("\n[4] Checking for existing composite tasks...")
    existing_tasks = load_existing_composite_tasks()
    print(f"    Found {len(existing_tasks)} existing composite tasks")
    
    # Call LLM
    print("\n[5] Generating composite task specifications...")
    generated_data = call_llm_for_complex_tasks(domains_info, samples, resource_stats, existing_tasks)
    
    if generated_data["status"] == "success":
        num_tasks = len(generated_data["composite_tasks"])
        print(f"\n[OK] Generated {num_tasks} composite tasks")
        
        if num_tasks > 0:
            # Save to file
            saved_count = save_complex_tasks(generated_data)
            print(f"[OK] Added {saved_count} new composite tasks")
            
            # Display generated tasks
            print("\n" + "=" * 80)
            print("GENERATED COMPOSITE TASK SPECIFICATIONS")
            print("=" * 80)
            
            for i, task in enumerate(generated_data["composite_tasks"], 1):
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


if __name__ == "__main__":
    generate_complex_tasks_llm()
