from fastapi import APIRouter, HTTPException, Query
from services.identity import IdentityService
from models import IdentityRequestModel, IdentityResponseModel, PersonalServerModel, EthereumAddress, ErrorResponse
from exceptions import VanaAPIError

router = APIRouter()

identity_service = IdentityService()

@router.get(
    '/identity',
    response_model=IdentityResponseModel,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid address"},
        500: {"model": ErrorResponse, "description": "Server error"}
    }
)
async def get_identity(address: EthereumAddress = Query(..., description="EIP-55 checksum address")):
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