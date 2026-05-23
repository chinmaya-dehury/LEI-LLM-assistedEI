"""
val_semantic.py
-------------------
Semantic validation models and functions for task outputs.
Provides Pydantic v2 strict validation with configurable business rules.

Used by: validator.py
Features:
- Strict Pydantic models (no type coercion, no extra fields)
- Separated schema validation from business rules
- Configurable per-task validation (e.g., min_results)
- Returns validated objects, not just bool status

Modified on: 23-05-2026
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError, ConfigDict


# ============================================================================
# PYDANTIC MODELS FOR SEMANTIC VALIDATION (STRICT MODE)
# ============================================================================

class ResultValue(BaseModel):
    """
    Represents a result value (can be string, number, bool, nested object, etc.).
    Strict mode enforces no type coercion: "123" stays string, not int.
    """
    model_config = ConfigDict(strict=True, extra="forbid")


class ResultItem(BaseModel):
    """
    Individual result item in result_summary array.
    Strict schema with no extra fields allowed.
    
    Fields:
        key: Unique identifier for the result (required, non-empty string)
        value: Result value (any type, no coercion)
        metric: Optional metric name associated with result
    """
    model_config = ConfigDict(strict=True, extra="forbid")
    
    key: str = Field(..., min_length=1, description="Result key/identifier")
    value: Any = Field(..., description="Result value (any type)")
    metric: Optional[str] = Field(None, description="Metric name if applicable")


class TaskOutput(BaseModel):
    """
    Strict semantic schema for task output.
    
    Enforces:
    - Exactly two fields required: task_name and result_summary
    - No extra fields allowed (rejects hallucinations)
    - Strict type checking (no coercion: "123" stays string)
    - result_summary must be list of ResultItem objects with key/value pairs
    
    Usage:
        validated = TaskOutput.model_validate(json_output, strict=True)
    """
    model_config = ConfigDict(strict=True, extra="forbid")
    
    task_name: str = Field(..., min_length=1, description="Name of the task")
    result_summary: List[ResultItem] = Field(
        ...,  # Required, not optional
        description="Array of result items (each with key, value, optional metric)"
    )


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def _validate_output_schema(json_output: Dict[str, Any]) -> tuple[Optional[TaskOutput], List[str]]:
    """
    Validate JSON output against strict Pydantic schema (TaskOutput).
    This is schema validation only - no business rules.
    
    Args:
        json_output: JSON dict to validate
    
    Returns:
        (validated_object: Optional[TaskOutput], error_messages: List[str])
        - If valid: (TaskOutput instance, [])
        - If invalid: (None, [formatted_error_messages])
    
    Examples:
        >>> result, errors = _validate_output_schema({"task_name": "foo", "result_summary": []})
        >>> if result:
        ...     print(f"Valid: {result.task_name}")
        ... else:
        ...     print("Errors:", errors)
    """
    try:
        # Validate in strict mode: no type coercion, no extra fields
        validated = TaskOutput.model_validate(json_output, strict=True)
        return validated, []
    
    except ValidationError as e:
        # Format Pydantic validation errors with invalid input values
        error_details = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            input_val = error.get("input", "<unknown>")
            
            # Include input value in error message for debugging
            error_details.append(f"  • {loc}: {msg} (got: {repr(input_val)})")
        
        formatted_errors = "\n".join(error_details)
        return None, [formatted_errors]


def _validate_business_rules(validated_output: TaskOutput, expected_task_name: str, min_results: int = 1) -> List[str]:
    """
    Apply business-rule validation separate from schema validation.
    These rules are configurable per task and enforce business logic.
    
    Args:
        validated_output: Already validated TaskOutput object (schema-valid)
        expected_task_name: Expected task name to match against
        min_results: Minimum number of results required (default 1)
    
    Returns:
        List of error messages (empty list if all rules pass)
    
    Examples:
        >>> validated = TaskOutput(task_name="foo", result_summary=[...])
        >>> errors = _validate_business_rules(validated, "foo", min_results=2)
        >>> if errors:
        ...     print("Business rule violations:", errors)
    """
    errors = []
    
    # Rule 1: Task name must match expected
    if validated_output.task_name != expected_task_name:
        errors.append(
            f"Task name mismatch: expected '{expected_task_name}', "
            f"got '{validated_output.task_name}'"
        )
    
    # Rule 2: Minimum results requirement
    if len(validated_output.result_summary) < min_results:
        errors.append(
            f"Insufficient results: expected at least {min_results}, "
            f"got {len(validated_output.result_summary)}"
        )
    
    return errors


def _validate_output_semantically(json_output: Dict[str, Any], task_name: str, min_results: int = 1) -> tuple[Optional[TaskOutput], Optional[str]]:
    """
    Combined semantic validation: schema validation + business rules.
    
    This is the primary validation function that should be used.
    
    Args:
        json_output: JSON dict to validate
        task_name: Expected task name
        min_results: Minimum required results in result_summary (default 1, configurable)
    
    Returns:
        (validated_object: Optional[TaskOutput], error_message: Optional[str])
        - If valid: (TaskOutput instance, None)
        - If invalid: (None, formatted_error_message)
    
    Examples:
        >>> output, error = _validate_output_semantically(json_data, "my_task", min_results=2)
        >>> if output:
        ...     print(f"Valid: {output.task_name}, {len(output.result_summary)} results")
        ... else:
        ...     print(f"Invalid: {error}")
    """
    # Stage 1: Schema validation (strict Pydantic mode)
    validated, schema_errors = _validate_output_schema(json_output)
    if validated is None:
        error_msg = "Semantic validation failed (schema):\n" + "\n".join(schema_errors)
        return None, error_msg
    
    # Stage 2: Business-rule validation
    business_errors = _validate_business_rules(validated, task_name, min_results)
    if business_errors:
        error_msg = "Semantic validation failed (business rules):\n" + "\n".join(
            f"  • {e}" for e in business_errors
        )
        return None, error_msg
    
    # All validations passed
    return validated, None


def _validate_output_structure(json_output: Dict[str, Any], task_name: str, min_results: int = 1) -> tuple[Optional[TaskOutput], Optional[str]]:
    """
    Multi-stage validation with early type checks.
    
    This is a wrapper that adds type checking before semantic validation.
    
    Args:
        json_output: JSON dict to validate
        task_name: Expected task name
        min_results: Minimum required results (default 1, configurable)
    
    Returns:
        (validated_object: Optional[TaskOutput], error_message: Optional[str])
        - If valid: (TaskOutput instance, None)
        - If invalid: (None, error_message)
    
    Examples:
        >>> output, error = _validate_output_structure(json_data, "task_x", min_results=2)
        >>> if output is not None:
        ...     print("All validations passed!")
        ...     print(f"Results: {[r.key for r in output.result_summary]}")
    """
    # Stage 1: Type check - must be dict
    if not isinstance(json_output, dict):
        return None, f"Output must be a JSON object (dict), got {type(json_output).__name__}"
    
    # Stage 2: Semantic validation (schema + business rules)
    validated, error_msg = _validate_output_semantically(json_output, task_name, min_results)
    
    return validated, error_msg
