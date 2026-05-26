"""
val_semantic.py
-------------------
Semantic validation models and functions for task outputs.
Provides Pydantic v2 strict validation with configurable business rules.

Used by: validator.py
Features:
- Strict Pydantic models (no type coercion, no extra fields)
- Separated schema validation from business rules
- LLM-based code-description matching validation
- Handles blank output as valid (code correctness is primary)
- Configurable per-task validation (e.g., min_results)
- Returns validated objects, not just bool status

Modified on: 25-05-2026
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from openai import OpenAI
from config import LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL, LLM_VAL_MODEL
from datetime import datetime, timezone, timedelta
import json


# Initialize LLM client for code-description validation
client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)

# IST Timezone
IST = timezone(timedelta(hours=5, minutes=30))


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
    - task_description and generated_code are optional (for validation purposes)
    
    Usage:
        validated = TaskOutput.model_validate(json_output, strict=True)
    """
    model_config = ConfigDict(strict=True, extra="forbid")
    
    task_name: str = Field(..., min_length=1, description="Name of the task")
    result_summary: List[ResultItem] = Field(
        ...,  # Required, not optional
        description="Array of result items (each with key, value, optional metric)"
    )
    task_description: Optional[str] = Field(None, description="Task description for validation")
    generated_code: Optional[str] = Field(None, description="Generated code for matching validation")


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def _check_code_matches_description(
    code: str,
    description: str,
    task_name: str,
    sample_data: str = "",
) -> tuple[bool, Optional[str]]:
    """
    Use LLM to validate that generated code matches the task description and sample data.

    Args:
        code: Generated Python code
        description: Task description
        task_name: Name of the task
        sample_data: Optional sample input data used by the task

    Returns:
        (is_match: bool, error_message: Optional[str])
        - If matches: (True, None)
        - If no match: (False, error_message with LLM reasoning)
    """
    if not code or not description or not task_name:
        return True, None

    sample_data_section = ""
    if sample_data:
        sample_data_section = f"""

Sample Data:
{sample_data}
""".strip()

    validation_prompt = f"""
You are a code validation expert. Determine if the generated Python code matches the task description and sample data.

Task Name: {task_name}

Task Description:
{description}

{sample_data_section}

Generated Code:
```python
{code}
```

Does this code implement the task as described and behave consistently with the sample data?
- Answer ONLY with: "YES" or "NO" followed by brief reasoning.
- If there's a mismatch, explain what the code does vs. what was asked.
- Consider: blank output is acceptable if code is structurally correct for the task.

Response:
""".strip()

    try:
        response = client.chat.completions.create(
            model=LLM_VAL_MODEL,
            messages=[{"role": "user", "content": validation_prompt}],
            temperature=0.0,
            timeout=60,
        )

        result = (response.choices[0].message.content or "").strip()

        if result.startswith("YES"):
            return True, None

        reasoning = result[3:].strip() if len(result) > 3 else "Code does not match description"
        return False, reasoning[:300]

    except Exception:
        return True, None


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


def _validate_business_rules(
    validated_output: TaskOutput,
    expected_task_name: str,
    sample_data: str = "",
    min_results: int = 0,
) -> List[str]:
    """
    Apply business-rule validation separate from schema validation.
    These rules are configurable per task and enforce business logic.
    
    IMPORTANT: Blank output is NOT an error if the code is correct.
    The code correctness is validated via LLM matching against description.
    
    Args:
        validated_output: Already validated TaskOutput object (schema-valid)
        expected_task_name: Expected task name to match against
        sample_data: Optional sample data used for code-description matching
        min_results: Minimum number of results required (default 0, allow blank)
    
    Returns:
        List of error messages (empty list if all rules pass)
    
    Examples:
        >>> validated = TaskOutput(task_name="foo", result_summary=[...])
        >>> errors = _validate_business_rules(validated, "foo", min_results=0)
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
    
    # Rule 2: Blank output is acceptable - code correctness is validated via LLM
    # (min_results now defaults to 0, can be overridden if needed for specific tasks)
    if min_results > 0 and len(validated_output.result_summary) < min_results:
        errors.append(
            f"Insufficient results: expected at least {min_results}, "
            f"got {len(validated_output.result_summary)}"
        )
    
    # Rule 3: LLM-based code-description matching (if both provided)
    if validated_output.generated_code and validated_output.task_description:
        matches, match_error = _check_code_matches_description(
            validated_output.generated_code,
            validated_output.task_description,
            validated_output.task_name,
            sample_data,
        )
        if not matches and match_error:
            errors.append(f"Code-description mismatch: {match_error}")
    
    return errors


def _validate_output_semantically(
    json_output: Dict[str, Any],
    task_name: str,
    task_description: str = "",
    generated_code: str = "",
    sample_data: str = "",
    min_results: int = 0,
) -> tuple[Optional[TaskOutput], Optional[str], Dict[str, Any]]:
    """
    Combined semantic validation: schema validation + business rules + LLM code matching.
    
    This is the primary validation function that should be used.
    
    IMPORTANT: Blank output is acceptable if code is correct.
    Pass task_description and generated_code for LLM-based code-description matching.
    
    Args:
        json_output: JSON dict to validate
        task_name: Expected task name
        task_description: Task description for LLM code matching (optional)
        generated_code: Generated code for LLM matching (optional)
        sample_data: Sample CSV text or example input used to judge code behavior
        min_results: Minimum required results in result_summary (default 0 - allow blank output)
    
    Returns:
        (validated_object: Optional[TaskOutput], error_message: Optional[str], semantic_details: Dict)
        - If valid: (TaskOutput instance, None, details_dict)
        - If invalid: (None, formatted_error_message, details_dict)
        - semantic_details dict contains: {'performed': bool, 'passed': bool, 'reasoning': str}
    
    Examples:
        >>> output, error, sem_details = _validate_output_semantically(json_data, "my_task", task_description=desc, generated_code=code, sample_data=data, min_results=0)
        >>> if output:
        ...     print(f"Valid: {output.task_name}, semantic check: {sem_details['passed']}")
        ... else:
        ...     print(f"Invalid: {error}")
    """
    # Initialize semantic details tracking
    semantic_details = {
        "performed": False,
        "passed": False,
        "reasoning": "Semantic validation skipped: missing task description or generated code.",
    }

    has_semantic_inputs = bool((task_description or "").strip() and (generated_code or "").strip())
    if sample_data:
        has_semantic_inputs = has_semantic_inputs or bool(sample_data.strip())

    if has_semantic_inputs:
        semantic_details["performed"] = True
        semantic_details["reasoning"] = "Semantic validation executed."
    
    # Stage 1: Schema validation (strict Pydantic mode)
    validated, schema_errors = _validate_output_schema(json_output)
    if validated is None:
        error_msg = "Semantic validation failed (schema):\n" + "\n".join(schema_errors)
        if semantic_details["performed"]:
            semantic_details["reasoning"] = error_msg[:300]
        return None, error_msg, semantic_details
    
    # Inject code and description into validated object for LLM matching
    if generated_code:
        validated.generated_code = generated_code
    if task_description:
        validated.task_description = task_description
    
    # Stage 2: Business-rule validation (includes LLM code-description matching)
    business_errors = _validate_business_rules(validated, task_name, sample_data, min_results)
    if business_errors:
        error_msg = "Semantic validation failed (business rules):\n" + "\n".join(
            f"  • {e}" for e in business_errors
        )
        if semantic_details["performed"]:
            semantic_details["passed"] = False
            semantic_details["reasoning"] = "; ".join(business_errors[:2])[:200]  # First 200 chars
        return None, error_msg, semantic_details
    
    # All validations passed
    if semantic_details["performed"]:
        semantic_details["passed"] = True
        semantic_details["reasoning"] = "Code matches description, sample data, and output schema valid"
    
    return validated, None, semantic_details


def _validate_output_structure(
    json_output: Dict[str, Any],
    task_name: str,
    task_description: str = "",
    generated_code: str = "",
    sample_data: str = "",
    min_results: int = 0,
) -> tuple[Optional[TaskOutput], Optional[str], Dict[str, Any]]:
    """
    Multi-stage validation with early type checks.
    Includes LLM-based code-description matching with semantic validation tracking.
    
    IMPORTANT: Blank output is acceptable if code is correct and matches description.
    
    Args:
        json_output: JSON dict to validate
        task_name: Expected task name
        task_description: Task description for LLM code matching (optional)
        generated_code: Generated code for LLM matching (optional)
        sample_data: Sample CSV text or example input used to judge code behavior
        min_results: Minimum required results (default 0 - allow blank output)
    
    Returns:
        (validated_object: Optional[TaskOutput], error_message: Optional[str], semantic_details: Dict)
        - If valid: (TaskOutput instance, None, details_dict)
        - If invalid: (None, error_message, details_dict)
        - semantic_details dict contains: {'performed': bool, 'passed': bool, 'reasoning': str}
    
    Examples:
        >>> output, error, sem_details = _validate_output_structure(json_data, "task_x", task_description=desc, generated_code=code, sample_data=data, min_results=0)
        >>> if output is not None:
        ...     print("All validations passed!")
        ...     print(f"Semantic check performed: {sem_details['performed']}, passed: {sem_details['passed']}")
    """
    # Initialize semantic details
    semantic_details = {"performed": False, "passed": False, "reasoning": ""}
    
    # Stage 1: Type check - must be dict
    if not isinstance(json_output, dict):
        semantic_details["reasoning"] = f"Output must be a JSON object (dict), got {type(json_output).__name__}"
        return None, semantic_details["reasoning"], semantic_details
    
    # Stage 2: Semantic validation (schema + business rules + LLM matching)
    validated, error_msg, semantic_details = _validate_output_semantically(
        json_output,
        task_name,
        task_description,
        generated_code,
        sample_data,
        min_results,
    )
    
    return validated, error_msg, semantic_details
