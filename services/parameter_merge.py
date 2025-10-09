"""
Parameter merging service for operation requests.

Handles merging of runtime parameters with grant-defined parameters,
with extensibility for future complex merge strategies (e.g., regex validation,
constraints, schema validation).
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def merge_parameters(
    grant_parameters: Dict[str, Any],
    runtime_parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Merge runtime parameters with grant parameters.

    Strategy:
    - Grant parameters take precedence (they define the permission scope)
    - Runtime parameters fill in missing values (wildcards/optional params)
    - Future: Add validation, regex matching, constraint checking

    Args:
        grant_parameters: Parameters from the blockchain grant file
        runtime_parameters: Parameters provided at runtime by the client

    Returns:
        Merged parameters dictionary with grant taking precedence

    Examples:
        >>> merge_parameters({"model": "gpt-4"}, {"prompt": "hello", "model": "gpt-3.5"})
        {"model": "gpt-4", "prompt": "hello"}

        >>> merge_parameters({}, {"goal": "analyze data"})
        {"goal": "analyze data"}

        >>> merge_parameters({"temperature": 0.7}, None)
        {"temperature": 0.7}
    """
    if runtime_parameters is None:
        runtime_parameters = {}

    # Start with runtime parameters as base
    merged = dict(runtime_parameters)

    # Grant parameters override (they define the permission boundary)
    merged.update(grant_parameters)

    logger.debug(
        f"Parameter merge: grant={grant_parameters}, "
        f"runtime={runtime_parameters}, merged={merged}"
    )

    return merged


def validate_operation_match(
    grant_operation: str,
    request_operation: Optional[str] = None
) -> None:
    """
    Validate that request operation matches grant operation (if provided).

    Args:
        grant_operation: Operation from the grant file
        request_operation: Operation from the client request (optional)

    Raises:
        ValueError: If operations don't match
    """
    if request_operation and request_operation != grant_operation:
        raise ValueError(
            f"Operation mismatch: grant specifies '{grant_operation}', "
            f"but request specifies '{request_operation}'"
        )
