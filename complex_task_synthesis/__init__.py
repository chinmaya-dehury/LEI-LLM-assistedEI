"""
Complex Task Synthesis Module
Extends LEI framework with autonomous composite task generation.
"""

from .task_analyzer import TaskAnalyzer
from .dependency_resolver import DependencyResolver
from .composite_task_generator import CompositeTaskGenerator
from .workflow_executor_generator import generate_workflow_executor
from .utils import load_task_metadata, extract_task_capabilities

__version__ = "1.0.0"
__all__ = [
    "TaskAnalyzer",
    "DependencyResolver",
    "CompositeTaskGenerator",
    "generate_workflow_executor",
    "load_task_metadata",
    "extract_task_capabilities",
]
