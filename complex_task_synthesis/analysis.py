"""
Analysis module for complex task synthesis.

Combines task analysis and dependency resolution into one boundary.
"""

from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List, Any


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

            docstring = ""
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    docstring = content[start:end].strip()

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


class DependencyResolver:
    """Resolves dependencies between tasks across domains."""

    def __init__(self, task_analyzer):
        self.analyzer = task_analyzer
        self.dependency_graph = defaultdict(set)
        self.data_flow_graph = defaultdict(list)

    def discover_dependencies(self, domain1: str, domain2: str) -> Dict[str, Any]:
        """Discover dependencies between two domains."""
        domain1_info = self.analyzer.analyze_domain_tasks(domain1)
        domain2_info = self.analyzer.analyze_domain_tasks(domain2)

        dependencies = {
            "domain1": domain1,
            "domain2": domain2,
            "potential_connections": [],
            "data_compatibility": {},
            "execution_constraints": [],
        }

        for out_type in domain1_info["data_types_produced"]:
            for in_type in domain2_info["data_types_consumed"]:
                if self._are_compatible(out_type, in_type):
                    dependencies["potential_connections"].append({
                        "from_domain": domain1,
                        "to_domain": domain2,
                        "output_type": out_type,
                        "input_type": in_type,
                        "compatibility": "high" if out_type == in_type else "medium",
                    })

        for task1_name, task1_info in domain1_info["tasks"].items():
            for task2_name, task2_info in domain2_info["tasks"].items():
                if self._can_tasks_connect(task1_info, task2_info):
                    dependencies["potential_connections"].append({
                        "from_task": task1_name,
                        "to_task": task2_name,
                        "from_domain": domain1,
                        "to_domain": domain2,
                    })

        return dependencies

    def _are_compatible(self, output_type: str, input_type: str) -> bool:
        """Check if output and input types are compatible."""
        compatible_pairs = [
            ("json", "structured_data"),
            ("dataframe/csv", "structured_data"),
            ("dataframe/csv", "csv"),
            ("structured_data", "json"),
            ("structured_data", "dataframe/csv"),
        ]

        return (output_type, input_type) in compatible_pairs or output_type == input_type

    def _can_tasks_connect(self, task1: Dict, task2: Dict) -> bool:
        """Check if two tasks can be connected in a workflow."""
        return self._are_compatible(task1.get("output_type", ""), task2.get("input_type", ""))

    def find_missing_capabilities(self, required_capabilities: List[str],
                                  available_tasks: Dict[str, Any]) -> Dict[str, List[str]]:
        """Find which capabilities are missing."""
        available_capabilities = set()
        for task_info in available_tasks.values():
            available_capabilities.add(task_info.get("primary_function", "unknown"))

        missing = {
            "capabilities": [cap for cap in required_capabilities if cap not in available_capabilities],
            "available": list(available_capabilities),
        }

        return missing

    def topological_sort_tasks(self, subtasks: List[Dict]) -> List[str]:
        """Return execution order of subtasks respecting dependencies."""
        graph = {t["subtask_name"]: t.get("depends_on", []) for t in subtasks}
        in_degree = {node: len(deps) for node, deps in graph.items()}

        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for other_node, deps in graph.items():
                if node in deps:
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)

        return result if len(result) == len(graph) else list(graph.keys())

    def print_dependency_analysis(self, domain1: str, domain2: str):
        """Print dependency analysis between domains."""
        deps = self.discover_dependencies(domain1, domain2)

        print(f"\n{'=' * 80}")
        print(f"DEPENDENCY ANALYSIS: {domain1.upper()} <-> {domain2.upper()}")
        print(f"{'=' * 80}")
        print(f"Potential Connections: {len(deps['potential_connections'])}")

        for conn in deps["potential_connections"][:10]:
            if "from_task" in conn:
                print(f"  • {conn['from_task']:30} ({conn['from_domain']}) → "
                      f"{conn['to_task']:30} ({conn['to_domain']})")
            else:
                print(f"  • {conn['output_type']:20} → {conn['input_type']:20} "
                      f"(Compatibility: {conn['compatibility']})")

        if len(deps["potential_connections"]) > 10:
            print(f"  ... and {len(deps['potential_connections']) - 10} more connections")
        print()


__all__ = ["TaskAnalyzer", "DependencyResolver"]
