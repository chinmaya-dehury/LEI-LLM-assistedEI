"""
Dependency Resolver - Discovers task dependencies and data flows.
"""

from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, deque
import json

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
        
        # Find compatible data flows
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
        
        # Identify which tasks can connect
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
        # Tasks can connect if output type is compatible with input type
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
        # Build dependency graph
        graph = {t["subtask_name"]: t.get("depends_on", []) for t in subtasks}
        in_degree = {node: len(deps) for node, deps in graph.items()}
        
        # Topological sort using Kahn's algorithm
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
