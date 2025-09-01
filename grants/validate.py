import json
import os
import time
from typing import Any, Optional

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from domain.entities import GrantFile

SUPPORTED_OPERATIONS = {
    "llm_inference",
    "prompt_gemini_agent", 
    "prompt_qwen_agent"
}


def validate(data: Any, app_address: str) -> GrantFile:
    grant: Optional[GrantFile] = None

    if _validate_grant_schema(data):
        grant = GrantFile(
            grantee=data["grantee"],
            operation=data["operation"],
            parameters=data["parameters"],
            expires=data.get("expires"),
        )

    if grant.operation not in SUPPORTED_OPERATIONS:
        raise ValueError(
            f"Unsupported operation: {grant.operation}. "
            f"Supported operations are: {', '.join(sorted(SUPPORTED_OPERATIONS))}"
        )

    if grant.grantee != app_address:
        raise ValueError(
            "App address does not match the app address in the access permissions"
        )

    if grant.expires and int(time.time()) > grant.expires:
        raise ValueError("Grant has expired")
    
    return grant


def _validate_grant_schema(data: Any) -> bool:
    """
    Validates grant data against JSON schema

    Args:
        data: The grant data to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        # Load the grant file schema
        schema_path = os.path.join(os.path.dirname(__file__), "schema", "grantFile.schema.json")
        with open(schema_path, "r") as f:
            grant_file_schema = json.load(f)

        jsonschema.validate(instance=data, schema=grant_file_schema)
        return True
    except JsonSchemaValidationError:
        return False
