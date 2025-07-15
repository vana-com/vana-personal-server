import json
import time
from typing import Any, Dict, List, Optional, Union
import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from .grant_models import (
    GrantFile,
    GrantValidationOptions,
    GrantValidationResult,
    GrantValidationError,
    GrantExpiredError,
    GranteeMismatchError,
    OperationNotAllowedError,
    GrantSchemaError,
)
from .grant_files import retrieve_grant_file

# Load the grant file schema
GRANT_FILE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Vana Data Permission Grant",
    "description": "User-signed permission that authorizes a specific application to perform operations via a personal server",
    "type": "object",
    "required": ["grantee", "operation", "parameters"],
    "properties": {
        "grantee": {
            "type": "string",
            "pattern": "^0x[0-9a-fA-F]{40}$",
            "description": "EVM address of the application authorized to use this grant",
        },
        "operation": {
            "type": "string",
            "minLength": 1,
            "description": "Operation the grantee is authorized to perform",
        },
        "parameters": {
            "type": "object",
            "description": "Operation-specific parameters",
            "additionalProperties": True,
        },
        "expires": {
            "type": "integer",
            "minimum": 0,
            "description": "Optional Unix timestamp when grant expires (seconds since epoch per POSIX.1-2008)",
        },
    },
    "additionalProperties": False,
}


def validate_grant_schema(data: Any) -> bool:
    """
    Validates grant data against JSON schema

    Args:
        data: The grant data to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        jsonschema.validate(instance=data, schema=GRANT_FILE_SCHEMA)
        return True
    except JsonSchemaValidationError:
        return False


def validate_grantee_access(grant_file: GrantFile, requesting_address: str) -> None:
    """
    Validates that a grant file allows access for a specific grantee

    Args:
        grant_file: The grant file to validate
        requesting_address: The address requesting access

    Raises:
        GranteeMismatchError: When the grantee doesn't match the requesting address
    """
    if grant_file.grantee.lower() != requesting_address.lower():
        raise GranteeMismatchError(
            "Permission denied: requesting address does not match grantee",
            grant_file.grantee,
            requesting_address,
        )


def validate_grant_expiry(
    grant_file: GrantFile, current_time: Optional[int] = None
) -> None:
    """
    Validates that a grant has not expired

    Args:
        grant_file: The grant file to validate
        current_time: Override current time for testing (Unix timestamp)

    Raises:
        GrantExpiredError: When the grant has expired
    """
    if grant_file.expires:
        now = current_time or int(time.time())

        if now > grant_file.expires:
            raise GrantExpiredError(
                "Permission denied: grant has expired", grant_file.expires, now
            )


def validate_operation_access(grant_file: GrantFile, requested_operation: str) -> None:
    """
    Validates that a grant allows a specific operation

    Args:
        grant_file: The grant file to validate
        requested_operation: The operation being requested

    Raises:
        OperationNotAllowedError: When the requested operation is not allowed
    """
    if grant_file.operation != requested_operation:
        raise OperationNotAllowedError(
            "Permission denied: operation not allowed by grant",
            grant_file.operation,
            requested_operation,
        )


def extract_field_from_business_error(error: Exception) -> Optional[str]:
    """
    Helper function to extract field name from business validation errors

    Args:
        error: The validation error

    Returns:
        Field name if applicable, None otherwise
    """
    if isinstance(error, GrantExpiredError):
        return "expires"
    elif isinstance(error, GranteeMismatchError):
        return "grantee"
    elif isinstance(error, OperationNotAllowedError):
        return "operation"
    return None


def validate_grant(
    data: Any, options: Optional[GrantValidationOptions] = None
) -> Union[GrantFile, GrantValidationResult]:
    """
    Validates a grant file with comprehensive schema and business rule checking.

    This function provides flexible validation:
    - When throw_on_error is True (default), returns a validated GrantFile or throws specific errors
    - When throw_on_error is False, returns a detailed validation result

    Args:
        data: The grant file data to validate
        options: Validation options including grantee, operation, etc.

    Returns:
        Either a GrantFile (when throwing) or GrantValidationResult (when not throwing)

    Raises:
        GrantSchemaError: When the grant file structure is invalid
        GrantExpiredError: When the grant has expired
        GranteeMismatchError: When the grantee doesn't match the requesting address
        OperationNotAllowedError: When the requested operation is not allowed
    """
    if options is None:
        options = GrantValidationOptions()

    errors: List[Dict[str, Any]] = []
    grant: Optional[GrantFile] = None

    # 1. Schema Validation
    if options.schema:
        try:
            if validate_grant_schema(data):
                grant = GrantFile(
                    grantee=data["grantee"],
                    operation=data["operation"],
                    parameters=data["parameters"],
                    expires=data.get("expires"),
                )
            else:
                raise GrantValidationError("Invalid grant file schema")
        except Exception as e:
            if isinstance(e, GrantValidationError):
                schema_error = GrantSchemaError(
                    str(e),
                    [],  # Schema errors would be available from jsonschema
                    data,
                )
                errors.append(
                    {"type": "schema", "message": str(e), "error": schema_error}
                )
            else:
                errors.append(
                    {
                        "type": "schema",
                        "message": f"Schema validation failed: {str(e)}",
                        "error": e
                        if isinstance(e, Exception)
                        else Exception("Unknown error"),
                    }
                )
    else:
        # If schema validation is skipped, assume data is already a GrantFile
        if isinstance(data, GrantFile):
            grant = data
        else:
            # Fallback: try to create GrantFile from dict
            grant = GrantFile(
                grantee=data["grantee"],
                operation=data["operation"],
                parameters=data["parameters"],
                expires=data.get("expires"),
            )

    # 2. Business Logic Validation (only if we have a valid grant)
    if grant:
        # Check grantee access
        if options.grantee:
            try:
                validate_grantee_access(grant, options.grantee)
            except Exception as e:
                field = extract_field_from_business_error(e)
                errors.append(
                    {"type": "business", "field": field, "message": str(e), "error": e}
                )

        # Check expiration
        try:
            validate_grant_expiry(grant, options.current_time)
        except Exception as e:
            field = extract_field_from_business_error(e)
            errors.append(
                {"type": "business", "field": field, "message": str(e), "error": e}
            )

        # Check operation access
        if options.operation:
            try:
                validate_operation_access(grant, options.operation)
            except Exception as e:
                field = extract_field_from_business_error(e)
                errors.append(
                    {"type": "business", "field": field, "message": str(e), "error": e}
                )

    # 3. Return Results
    if errors:
        if options.throw_on_error:
            # Throw the most specific error we have
            first_error = errors[0]
            if "error" in first_error and isinstance(first_error["error"], Exception):
                raise first_error["error"]
            else:
                combined_message = "; ".join(e["message"] for e in errors)
                raise GrantValidationError(
                    f"Grant validation failed: {combined_message}",
                    {"errors": errors, "data": data},
                )

        return GrantValidationResult(valid=False, errors=errors, grant=grant)

    if options.throw_on_error:
        return grant
    else:
        return GrantValidationResult(valid=True, errors=[], grant=grant)


def check_grant_access(
    grant_url: str,
    requesting_address: str,
    operation: str,
    file_ids: List[int],
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Checks if a grant allows access for a specific request

    Args:
        grant_url: URL of the grant file
        requesting_address: Address requesting access
        operation: Operation being requested
        file_ids: File IDs being accessed
        timeout: Request timeout in seconds

    Returns:
        Dictionary with 'allowed' boolean and optional 'reason' and 'grantFile'
    """
    try:
        grant_file = retrieve_grant_file(grant_url, timeout)

        # Validate the grant for the request
        validate_grant(
            grant_file,
            GrantValidationOptions(grantee=requesting_address, operation=operation),
        )

        return {"allowed": True, "grantFile": grant_file}
    except GrantValidationError as e:
        return {"allowed": False, "reason": str(e)}
    except Exception as e:
        return {"allowed": False, "reason": f"Grant access check failed: {str(e)}"}


def retrieve_and_validate_grant(grant_url: str, timeout: int = 10) -> GrantFile:
    """
    Retrieves and validates a grant file

    Args:
        grant_url: URL of the grant file
        timeout: Request timeout in seconds

    Returns:
        Validated GrantFile

    Raises:
        NetworkError: When grant file cannot be retrieved
        GrantValidationError: When grant file is invalid
    """
    grant_file = retrieve_grant_file(grant_url, timeout)

    # Additional validation can be added here if needed
    return grant_file
