"""
Composite Task Generator - Generates complex tasks by combining simple tasks.
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

class CompositeTaskGenerator:
    """Generates complex composite tasks from basic tasks."""
    
    def __init__(self, dependency_resolver, config: Dict = None):
        self.resolver = dependency_resolver
        self.config = config or {}
        self.generated_tasks = []
    
    def generate_composite_task(self, task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a composite task based on specification."""
        
        # Extract subtasks and check availability
        subtasks_info = self._analyze_subtasks(task_definition["subtasks"])
        
        # Determine execution order
        execution_order = self.resolver.topological_sort_tasks(subtasks_info["subtasks"])
        
        # Build data flow
        data_flow = self._build_data_flow(subtasks_info["subtasks"], execution_order)
        
        # Create composite task definition
        composite_task = {
            "task_name": task_definition["task_name"],
            "task_type": "composite",
            "description": task_definition["description"],
            "domains": list(set(t["domain"] for t in subtasks_info["subtasks"])),
            "subtasks": subtasks_info["subtasks"],
            "execution_order": execution_order,
            "data_flow": data_flow,
            "output_schema": task_definition.get("output_schema", {}),
            "summary": {
                "total_subtasks": len(subtasks_info["subtasks"]),
                "available": subtasks_info["available_count"],
                "pending_generation": subtasks_info["pending_count"],
                "missing": subtasks_info["missing_count"],
            },
            "complexity_score": self._calculate_complexity(subtasks_info["subtasks"]),
            "generated_at": datetime.now().isoformat(),
            "generation_metadata": {
                "generator": "CompositeTaskGenerator v1.0",
                "algorithm": "dependency_based_composition",
                "confidence": self._calculate_confidence(subtasks_info),
            }
        }
        
        self.generated_tasks.append(composite_task)
        return composite_task
    
    def _analyze_subtasks(self, subtasks: List[Dict]) -> Dict[str, Any]:
        """Analyze availability of subtasks."""
        analyzer = self.resolver.analyzer
        analysis = {
            "subtasks": subtasks,
            "available_count": 0,
            "pending_count": 0,
            "missing_count": 0,
            "details": [],
        }
        
        for subtask in subtasks:
            domain = subtask["domain"]
            task_id = subtask["task_id"]
            
            # Check if task exists in analyzed tasks
            domain_info = analyzer.analyze_domain_tasks(domain)
            
            if task_id in domain_info["tasks"]:
                subtask["status"] = "available"
                analysis["available_count"] += 1
                analysis["details"].append({
                    "task": task_id,
                    "status": "available",
                    "file_path": domain_info["tasks"][task_id]["file_path"],
                })
            else:
                subtask["status"] = "pending_generation"
                analysis["pending_count"] += 1
                analysis["details"].append({
                    "task": task_id,
                    "status": "pending_generation",
                })
        
        return analysis
    
    def _build_data_flow(self, subtasks: List[Dict], execution_order: List[str]) -> List[Dict]:
        """Build data flow connections between subtasks."""
        data_flow = []
        
        for i in range(len(execution_order) - 1):
            from_task = execution_order[i]
            to_task = execution_order[i + 1]
            
            # Find outputs of from_task and inputs of to_task
            from_outputs = next((t.get("outputs", []) for t in subtasks if t["subtask_name"] == from_task), [])
            to_inputs = next((t.get("inputs", []) for t in subtasks if t["subtask_name"] == to_task), [])
            
            if from_outputs and to_inputs:
                data_flow.append({
                    "from": from_task,
                    "to": to_task,
                    "data": from_outputs[0] if from_outputs else "output",
                })
        
        return data_flow
    
    def _calculate_complexity(self, subtasks: List[Dict]) -> float:
        """Calculate overall complexity of composite task."""
        analyzer = self.resolver.analyzer
        complexities = []
        
        for subtask in subtasks:
            domain = subtask["domain"]
            task_id = subtask["task_id"]
            domain_info = analyzer.analyze_domain_tasks(domain)
            
            if task_id in domain_info["tasks"]:
                complexities.append(domain_info["tasks"][task_id].get("complexity", 5))
        
        if not complexities:
            return 5.0
        
        return min(10, max(1, sum(complexities) / len(complexities) * 1.5))
    
    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate confidence in the generated composite task."""
        total = analysis["available_count"] + analysis["pending_count"] + analysis["missing_count"]
        if total == 0:
            return 0.0
        
        # Confidence is higher when more tasks are available
        available_ratio = analysis["available_count"] / total
        pending_penalty = analysis["pending_count"] * 0.1
        missing_penalty = analysis["missing_count"] * 0.2
        
        confidence = max(0, min(1, available_ratio - pending_penalty - missing_penalty))
        return round(confidence, 2)
    
    def print_composite_task_details(self, composite_task: Dict):
        """Print detailed information about generated composite task."""
        summary = composite_task["summary"]
        
        print(f"\n{'=' * 80}")
        print(f"COMPOSITE TASK GENERATED: {composite_task['task_name'].upper()}")
        print(f"{'=' * 80}")
        print(f"Description: {composite_task['description']}")
        print(f"Task Type: {composite_task['task_type']}")
        print(f"Domains: {', '.join(composite_task['domains'])}")
        print(f"Complexity Score: {composite_task['complexity_score']:.1f}/10")
        print(f"Confidence: {composite_task['generation_metadata']['confidence']:.1%}")
        
        print(f"\n{'SUBTASK INVENTORY':^80}")
        print(f"{'-' * 80}")
        print(f"Total Subtasks: {summary['total_subtasks']}")
        print(f"  [AVAILABLE]         {summary['available']:3} ({summary['available']/summary['total_subtasks']*100:.1f}%)")
        print(f"  [PENDING]           {summary['pending_generation']:3} ({summary['pending_generation']/summary['total_subtasks']*100:.1f}%)")
        print(f"  [MISSING]           {summary['missing']:3} ({summary['missing']/summary['total_subtasks']*100:.1f}%)")
        
        print(f"\n{'EXECUTION ORDER':^80}")
        print(f"{'-' * 80}")
        for i, task_name in enumerate(composite_task["execution_order"], 1):
            print(f"  {i}. {task_name}")
        
        print(f"\n{'DATA FLOW':^80}")
        print(f"{'-' * 80}")
        for flow in composite_task["data_flow"]:
            print(f"  {flow['from']:30} --> {flow['to']:30} ({flow['data']})")
        
        print(f"\n{'SUBTASK DETAILS':^80}")
        print(f"{'-' * 80}")
        for subtask in composite_task["subtasks"]:
            status_icon = "[OK]" if subtask["status"] == "available" else "[PENDING]" if subtask["status"] == "pending_generation" else "[MISSING]"
            print(f"  {status_icon} {subtask['subtask_name']:35} ({subtask['domain']:15}) - {subtask['status']}")
        
        print(f"\nGenerated: {composite_task['generated_at']}")
        print()
