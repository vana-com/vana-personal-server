from fastapi import APIRouter, HTTPException, Query
from services.identity import IdentityService
from models import IdentityRequestModel, IdentityResponseModel, PersonalServerModel, EthereumAddress, ErrorResponse

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
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail='Invalid address')
    except Exception as e:
        raise HTTPException(status_code=500, detail='Server error')