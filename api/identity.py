from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Request, status
from api.schemas import IdentityRequestModel, IdentityResponseModel, PersonalServerModel, EVMAddress, ErrorResponse
from domain.exceptions import VanaAPIError
from dependencies import IdentityServiceDep
from utils.rate_limit import check_rate_limit_sync

router = APIRouter(tags=["identity"])

@router.get(
    '/identity',
    summary="Get user identity",
    description=(
        "Retrieve identity information for a user including their personal server details. "
        "The personal server address and public key are deterministically derived from the user's address."
    ),
    response_model=IdentityResponseModel,
    responses={
        200: {
            "description": "Identity information retrieved successfully",
            "model": IdentityResponseModel,
            "content": {
                "application/json": {
                    "example": {
                        "kind": "Identity",
                        "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
                        "personal_server": {
                            "kind": "PersonalServer",
                            "address": "0x742d35Cc6558Fd4D9e9E0E888F0462ef6919Bd36",
                            "public_key": "0x04bcdf3e094f5c9a7819baedfabe81c235b8e6c8a5b26b62a98fa685deaac1e488090fa3c6b2667c1bf3a6e593bc0fb3e670f78a72e9fe0b1c40e2f9dda957f61a"
                        }
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid EVM address format"
        },
        429: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded - retry with exponential backoff"
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error during identity derivation"
        }
    }
)
async def get_identity(
    request: Request,
    address: str = Query(
        ...,
        description="User's EVM wallet address (EIP-55 checksum format)",
        example="0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
        pattern="^0x[a-fA-F0-9]{40}$"
    ),
    identity_service: IdentityServiceDep = None
):
    """
    Retrieve identity information for a user.
    
    Derives the personal server identity deterministically from the user's
    EVM address. The personal server has its own address and public key
    used for encryption and authentication.
    
    Args:
        request: Raw HTTP request for rate limiting
        address: User's EVM wallet address in EIP-55 checksum format
        identity_service: Injected identity service dependency
        
    Returns:
        IdentityResponseModel with user and personal server details
        
    Raises:
        HTTPException(400): Invalid address format
        HTTPException(429): Rate limit exceeded
        HTTPException(500): Identity derivation failed
        
    Note:
        Personal server derivation is deterministic - same address always
        produces same personal server identity. Public key is in SEC1
        uncompressed format (65 bytes, 0x04-prefixed).
    """
    # Check rate limit
    check_rate_limit_sync(request, "identity", address)

    try:
        identity = identity_service.derive_server_identity(address)
        return IdentityResponseModel(
            user_address=identity.user_address,
            personal_server=PersonalServerModel(
                address=identity.personal_server.address,
                public_key=identity.personal_server.public_key
            )
        )

    except VanaAPIError as e:
        error_response = ErrorResponse(
            detail=e.message,
            error_code=e.error_code,
            field=getattr(e, 'field', None)
        )
        raise HTTPException(status_code=e.status_code, detail=error_response.dict())
    except Exception as e:
        error_response = ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_SERVER_ERROR"
        )
        raise HTTPException(status_code=500, detail=error_response.dict())