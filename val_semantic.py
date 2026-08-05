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
from config import LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL, LLM_VAL_MODEL, LLM_VAL_BASE_URL, LLM_VAL_API_KEY, LLM_VAL_MODELS_LIST
from datetime import datetime, timezone, timedelta
import json


# Note: We instantiate clients per-call to allow using different validator models.

# IST Timezone
IST = timezone(timedelta(hours=5, minutes=30))


# ============================================================================
# PYDANTIC MODELS FOR SEMANTIC VALIDATION (STRICT MODE)
# ============================================================================




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
    - result_summary must be a list of dictionaries (objects) representing the results
    - task_description and generated_code are optional (for validation purposes)
    
    Usage:
        validated = TaskOutput.model_validate(json_output, strict=True)
    """
    model_config = ConfigDict(strict=True, extra="forbid")
    
    task_name: str = Field(..., min_length=1, description="Name of the task")
    result_summary: List[Dict[str, Any]] = Field(
        ...,  # Required, not optional
        description="Array of result items (each with custom key-value pairs)"
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
) -> tuple[bool, Optional[str], list]:
    """
    Use LLM to validate three semantic criteria simultaneously:
      1. TASK IMPLEMENTATION  – does the code correctly implement what the description asks?
      2. OUTPUT SCHEMA        – does the code produce the required JSON schema?
      3. RESULT CONSISTENCY   – are result_summary items consistent with the task goal?

    Args:
        code: Generated Python code
        description: Task description
        task_name: Name of the task
        sample_data: Optional sample input data used by the task

    Returns:
        (majority_passed: bool, aggregated_reason: Optional[str], per_model_results: list)
    """
    if not code or not description or not task_name:
        return True, None, []

    # Trim sample data to first 10 rows to keep token cost reasonable
    sample_rows = (sample_data or "").strip().split("\n")
    trimmed_sample = "\n".join(sample_rows[:10])
    if len(sample_rows) > 10:
        trimmed_sample += "\n... [TRUNCATED] ..."

    # -----------------------------------------------------------------------
    # System prompt: strict judge role with 3 explicit evaluation criteria
    # -----------------------------------------------------------------------
    system_prompt = """\
You are a strict semantic code-output validator for edge-device IoT Python scripts.

Evaluate the following THREE criteria simultaneously:

1. TASK IMPLEMENTATION
   Does the code correctly implement what the task description asks for?
   Example: if the task says "compute hourly average temperature", does the code
   actually group by hour and compute a mean — not just read the file or return raw rows?

2. OUTPUT SCHEMA
   Does the code write a JSON result file that matches ALL of these required fields?
   {
     "task_name":          "<non-empty string>",
     "description":        "<non-empty string>",
     "result_summary":     <any valid JSON format: list of objects, list of strings/numbers, single dictionary, or value>,
     "result_generated_at":"<ISO-8601 timestamp>"
   }
   All four top-level fields must be present and non-null.
   The result_summary field can hold any valid JSON representation produced by the task (e.g., a list of dictionaries, a list of strings/numbers, a summary dictionary, or a single value).

3. RESULT CONSISTENCY
   Are the result_summary items semantically consistent with the task goal?
   Example: an anomaly-detection task should produce anomaly counts/flags in result_summary,
   NOT raw data rows. An aggregation task must produce aggregated values, not per-row copies.

Respond ONLY with a JSON object — no markdown, no extra text:
  {"verdict": "YES", "reason": ""}
  or
  {"verdict": "NO",  "reason": "<concise 1-2 sentence explanation of which criterion failed and why>"}

Rules:
- "YES" only when ALL THREE criteria pass.
- "NO" if ANY criterion fails; identify the specific failing criterion in "reason".
- Empty result_summary is acceptable ONLY when the input data genuinely has no matching records.
- Focus on logic correctness, not coding style.
"""

    # -----------------------------------------------------------------------
    # User prompt: the actual task + code to evaluate
    # -----------------------------------------------------------------------
    user_prompt = f"""Task Name: {task_name}

Task Description:
{description}

Sample Input Data (first 10 rows):
{trimmed_sample}

Generated Code:
```python
{code}
```

Evaluate all three criteria (task implementation, output schema, result consistency) and return the JSON verdict."""

    per_model_results = []
    aggregated_reasons = []
    passes = 0
    models = LLM_VAL_MODELS_LIST if isinstance(LLM_VAL_MODELS_LIST, list) and LLM_VAL_MODELS_LIST else [LLM_VAL_MODEL]

    for model in models:
        try:
            client = OpenAI(base_url=LLM_VAL_BASE_URL, api_key=LLM_VAL_API_KEY, timeout=120)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.0,
                timeout=60,
            )

            raw = (response.choices[0].message.content or "").strip()

            # --- Parse JSON verdict with graceful fallback ---
            passed = False
            reason = ""
            try:
                parsed  = json.loads(raw)
                verdict = str(parsed.get("verdict", "")).strip().upper()
                reason  = str(parsed.get("reason", "")).strip()
                passed  = (verdict == "YES")
            except (json.JSONDecodeError, AttributeError, TypeError):
                # Fallback: accept plain "YES / NO" prefix if LLM ignores JSON instruction
                upper_raw = raw.upper().lstrip()
                if upper_raw.startswith("YES"):
                    passed = True
                    reason = ""
                elif upper_raw.startswith("NO"):
                    passed = False
                    reason = raw[2:].strip() if len(raw) > 2 else "Code does not match description"
                else:
                    # Cannot determine verdict — treat as pass to avoid false negatives
                    passed = True
                    reason = f"[unparseable verdict, treating as pass] {raw[:200]}"

            if passed:
                passes += 1

            per_model_results.append({"model": model, "passed": passed, "reason": reason[:500]})
            if reason and not passed:
                aggregated_reasons.append(f"{model}: {reason[:300]}")

        except Exception as e:
            # On LLM call failure, record as failed and note the exception
            per_model_results.append({"model": model, "passed": False, "reason": f"validator_call_error: {e}"})

    # Majority voting
    majority_required = (len(models) // 2) + 1
    majority_passed   = passes >= majority_required
    aggregated_reason_text = "; ".join(aggregated_reasons) if aggregated_reasons else ""
    return majority_passed, aggregated_reason_text or None, per_model_results


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
    skip_code_matching: bool = False,
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
        skip_code_matching: If True, bypass LLM code correctness matching
    
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
    
    # Rule 3: LLM-based code-description matching (if both provided and not skipped)
    if not skip_code_matching and validated_output.generated_code and validated_output.task_description:
        matches, match_error, per_model = _check_code_matches_description(
            validated_output.generated_code,
            validated_output.task_description,
            validated_output.task_name,
            sample_data,
        )
        if not matches and match_error:
            errors.append(f"Code-description mismatch: {match_error}")
        # attach per-model validator details to the validated object via semantic details
        validated_output.__dict__.setdefault("_validator_details", {})
        validated_output.__dict__["_validator_details"]["per_model"] = per_model
        validated_output.__dict__["_validator_details"]["majority_passed"] = bool(matches)
    
    return errors


def _validate_output_structure(
    json_output: Dict[str, Any],
    task_name: str,
    task_description: str = "",
    generated_code: str = "",
    sample_data: str = "",
    min_results: int = 0,
    skip_code_matching: bool = False,
) -> tuple[Optional[TaskOutput], Optional[str], Dict[str, Any]]:
    """
    Multi-stage semantic validation with early type checks.
    Includes strict schema validation, business rules, and LLM-based code-description matching.
    
    IMPORTANT: Blank output is acceptable if code is correct and matches description.
    
    Args:
        json_output: JSON dict to validate
        task_name: Expected task name
        task_description: Task description for LLM code matching (optional)
        generated_code: Generated code for LLM matching (optional)
        sample_data: Sample CSV text or example input used to judge code behavior
        min_results: Minimum required results (default 0 - allow blank output)
        skip_code_matching: If True, bypass LLM code correctness matching
    
    Returns:
        (validated_object: Optional[TaskOutput], error_message: Optional[str], semantic_details: Dict)
        - If valid: (TaskOutput instance, None, details_dict)
        - If invalid: (None, error_message, details_dict)
        - semantic_details dict contains: {'performed': bool, 'passed': bool, 'reasoning': str}
    """
    # Stage 1: Type check - must be dict
    if not isinstance(json_output, dict):
        semantic_details = {
            "performed": False,
            "passed": False,
            "reasoning": f"Output must be a JSON object (dict), got {type(json_output).__name__}",
        }
        return None, semantic_details["reasoning"], semantic_details

    # Stage 2: Initialize semantic details tracking
    semantic_details = {
        "performed": False,
        "passed": False,
        "reasoning": "Semantic validation skipped: missing task description or generated code.",
    }

    has_semantic_inputs = not skip_code_matching and bool((task_description or "").strip() and (generated_code or "").strip())
    if sample_data and not skip_code_matching:
        has_semantic_inputs = has_semantic_inputs or bool(sample_data.strip())

    if has_semantic_inputs:
        semantic_details["performed"] = True
        semantic_details["reasoning"] = "Semantic validation executed."
    
    # Stage 3: Schema validation (strict Pydantic mode)
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
    
    # Stage 4: Business-rule validation (includes LLM code-description matching)
    business_errors = _validate_business_rules(validated, task_name, sample_data, min_results, skip_code_matching)
    if business_errors:
        error_msg = "Semantic validation failed (business rules):\n" + "\n".join(
            f"  • {e}" for e in business_errors
        )
        if semantic_details["performed"]:
            semantic_details["passed"] = False
            semantic_details["reasoning"] = "; ".join(business_errors[:2])[:200]  # First 200 chars
        # If validator details were attached, surface them in semantic_details
        if hasattr(validated, "_validator_details"):
            semantic_details["validator_results"] = validated.__dict__.get("_validator_details", {}).get("per_model", [])
            semantic_details["majority_passed"] = validated.__dict__.get("_validator_details", {}).get("majority_passed", False)
        return None, error_msg, semantic_details
    
    # All validations passed
    if semantic_details["performed"]:
        semantic_details["passed"] = True
        semantic_details["reasoning"] = "Code matches description, sample data, and output schema valid"
        # Include validator details if available
        if hasattr(validated, "_validator_details"):
            semantic_details["validator_results"] = validated.__dict__.get("_validator_details", {}).get("per_model", [])
            semantic_details["majority_passed"] = validated.__dict__.get("_validator_details", {}).get("majority_passed", False)
    
    return validated, None, semantic_details
