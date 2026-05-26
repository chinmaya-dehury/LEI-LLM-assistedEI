"""
Task Analyzer - Analyzes existing validated tasks and extracts metadata.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from datetime import datetime

class TaskAnalyzer:
    """Analyzes existing tasks to extract capabilities, inputs, outputs, and dependencies."""
    
    def __init__(self, generated_tasks_dir: str = "generated_tasks"):
        self.generated_tasks_dir = Path(generated_tasks_dir)
        self.tasks_by_domain = {}
        self.task_capabilities = {}
        self.task_metadata = {}
    
    def discover_all_domains(self) -> List[str]:
        """Discover all available domains with generated tasks."""
        if not self.generated_tasks_dir.exists():
            return []
        
        domains = [
            d.name for d in self.generated_tasks_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
        return sorted(domains)
    
    def analyze_domain_tasks(self, domain: str) -> Dict[str, Any]:
        """Analyze all tasks in a domain."""
        domain_path = self.generated_tasks_dir / domain
        task_files = sorted(domain_path.glob("*.py"))
        
        domain_info = {
            "domain": domain,
            "task_count": 0,
            "tasks": {},
            "capabilities": set(),
            "data_types_produced": set(),
            "data_types_consumed": set(),
        }
        
        for task_file in task_files:
            task_name = task_file.stem
            if task_name in ("failed", "__pycache__"):
                continue
            
            task_info = self._extract_task_info(task_file, domain)
            if task_info:
                domain_info["tasks"][task_name] = task_info
                domain_info["task_count"] += 1
                domain_info["capabilities"].add(task_info.get("primary_function", "unknown"))
                if "output_type" in task_info:
                    domain_info["data_types_produced"].add(task_info["output_type"])
                if "input_type" in task_info:
                    domain_info["data_types_consumed"].add(task_info["input_type"])
        
        return domain_info
    
    def _extract_task_info(self, task_file: Path, domain: str) -> Dict[str, Any]:
        """Extract metadata from a task Python file."""
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract docstring
            docstring = ""
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    docstring = content[start:end].strip()
            
            # Infer task characteristics
            task_info = {
                "task_name": task_file.stem,
                "domain": domain,
                "file_path": str(task_file),
                "docstring": docstring[:200],
                "size_lines": len(content.split("\n")),
                "primary_function": self._infer_function(task_file.stem),
                "output_type": self._infer_output_type(content),
                "input_type": self._infer_input_type(content),
                "complexity": self._estimate_complexity(content),
            }
            
            self.task_metadata[task_file.stem] = task_info
            return task_info
        
        except Exception as e:
            print(f"[WARNING] Could not extract info from {task_file}: {e}")
            return None
    
    def _infer_function(self, task_name: str) -> str:
        """Infer primary function from task name."""
        keywords = {
            "trend": "trend_analysis",
            "cluster": "clustering",
            "forecast": "forecasting",
            "correlation": "correlation_analysis",
            "detection": "anomaly_detection",
            "classification": "classification",
            "average": "aggregation",
            "variation": "pattern_analysis",
            "decomposition": "decomposition",
            "assessment": "assessment",
        }
        
        for key, func in keywords.items():
            if key in task_name.lower():
                return func
        
        return "general_analysis"
    
    def _infer_output_type(self, content: str) -> str:
        """Infer output data type."""
        if "json.dumps" in content or "JSON" in content:
            return "json"
        if "DataFrame" in content or "csv" in content:
            return "dataframe/csv"
        if "plot" in content or "matplotlib" in content:
            return "visualization"
        return "structured_data"
    
    def _infer_input_type(self, content: str) -> str:
        """Infer input data type."""
        if "csv" in content or "read_csv" in content:
            return "csv"
        if "json" in content:
            return "json"
        if "DataFrame" in content:
            return "dataframe"
        return "structured_data"
    
    def _estimate_complexity(self, content: str) -> int:
        """Estimate task complexity (1-10)."""
        lines = len(content.split("\n"))
        functions = content.count("def ")
        loops = content.count("for ") + content.count("while ")
        imports = content.count("import ")
        
        complexity = min(10, max(1, (lines // 50) + (functions * 2) + (loops) + (imports // 2)))
        return complexity
    
    def print_domain_analysis(self, domain: str):
        """Print analysis of a domain in terminal."""
        domain_info = self.analyze_domain_tasks(domain)
        
        print(f"\n{'=' * 80}")
        print(f"DOMAIN ANALYSIS: {domain.upper()}")
        print(f"{'=' * 80}")
        print(f"Total Tasks: {domain_info['task_count']}")
        print(f"Capabilities: {', '.join(sorted(domain_info['capabilities']))}")
        print(f"Output Types Produced: {', '.join(sorted(domain_info['data_types_produced']))}")
        print(f"Input Types Consumed: {', '.join(sorted(domain_info['data_types_consumed']))}")
        print(f"\nTasks:")
        for task_name, task_info in sorted(domain_info["tasks"].items()):
            complexity_bar = "█" * task_info["complexity"] + "░" * (10 - task_info["complexity"])
            print(f"  • {task_name:40} [{complexity_bar}] {task_info['primary_function']}")
        print()
    
    def print_all_domains_summary(self):
        """Print summary of all domains."""
        domains = self.discover_all_domains()
        
        print(f"\n{'=' * 80}")
        print(f"LEI FRAMEWORK - DOMAIN SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Domains: {len(domains)}\n")
        
        for domain in domains:
            domain_info = self.analyze_domain_tasks(domain)
            if domain_info['task_count'] > 0:
                avg_complexity = sum(t['complexity'] for t in domain_info['tasks'].values()) / domain_info['task_count']
            else:
                avg_complexity = 0
            print(f"[{domain.upper():15}] Tasks: {domain_info['task_count']:3}  |  "
                  f"Capabilities: {len(domain_info['capabilities']):2}  |  "
                  f"Avg Complexity: {avg_complexity:.1f}")
        print()
