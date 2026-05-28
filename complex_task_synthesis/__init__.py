"""
Complex Task Synthesis Module
Extends LEI framework with autonomous composite task generation.
"""

from .analysis import TaskAnalyzer, DependencyResolver
from .generation import CompositeTaskGenerator, generate_workflow_executor
from .orchestration import run_complex_task_synthesis_workflow
from .utils import load_task_metadata, extract_task_capabilities

__version__ = "1.0.0"
__all__ = [
    "TaskAnalyzer",
    "DependencyResolver",
    "CompositeTaskGenerator",
    "generate_workflow_executor",
    "run_complex_task_synthesis_workflow",
    "load_task_metadata",
    "extract_task_capabilities",
]
