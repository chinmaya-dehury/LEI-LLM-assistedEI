"""
Utility functions for complex task synthesis.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

def load_task_metadata(task_path: str) -> Dict[str, Any]:
    """Load metadata from a task file."""
    try:
        with open(task_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract docstring and basic metadata
        docstring = ""
        if '"""' in content:
            start = content.find('"""') + 3
            end = content.find('"""', start)
            docstring = content[start:end].strip()
        
        return {
            "file_path": task_path,
            "size": len(content),
            "lines": len(content.split("\n")),
            "docstring": docstring,
        }
    except Exception as e:
        print(f"[ERROR] Could not load metadata: {e}")
        return {}

def extract_task_capabilities(task_file: Path) -> List[str]:
    """Extract capabilities from a task file."""
    capabilities = []
    try:
        with open(task_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for common patterns
        if "json.dumps" in content or "to_json" in content:
            capabilities.append("json_export")
        if "plot" in content or "matplotlib" in content:
            capabilities.append("visualization")
        if "correlation" in content or "pearson" in content:
            capabilities.append("correlation_analysis")
        if "forecast" in content or "predict" in content:
            capabilities.append("forecasting")
        if "clustering" in content or "cluster" in content:
            capabilities.append("clustering")
        if "trend" in content:
            capabilities.append("trend_analysis")
        if "anomaly" in content or "outlier" in content:
            capabilities.append("anomaly_detection")
        
    except Exception:
        pass
    
    return capabilities

def save_composite_task_config(composite_task: Dict, output_dir: str = "generated_tasks/complex"):
    """Save composite task configuration."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    filepath = Path(output_dir) / f"{composite_task['task_name'].replace(' ', '_').lower()}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(composite_task, f, indent=2, ensure_ascii=False)
    
    return filepath

def load_composite_task_config(filepath: str) -> Dict[str, Any]:
    """Load composite task configuration."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
