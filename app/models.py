from typing import Annotated
from pydantic import BaseModel, Field, BeforeValidator
import re

def validate_ethereum_address(value: str) -> str:
    if not re.match(r'^0x[a-fA-F0-9]{40}$', value):
        raise ValueError('Invalid Ethereum address format')
    return value

def validate_public_key(value: str) -> str:
    if not re.match(r'^0x[a-fA-F0-9]{128}$', value):
        raise ValueError('Invalid public key format')
    return value

EthereumAddress = Annotated[str, BeforeValidator(validate_ethereum_address)]
PublicKey = Annotated[str, BeforeValidator(validate_public_key)]

class IdentityRequestModel(BaseModel):
    user_address: EthereumAddress

class PersonalServerModel(BaseModel):
    address: EthereumAddress
    public_key: PublicKey

class IdentityResponseModel(BaseModel):
    user_address: EthereumAddress
    personal_server: PersonalServerModel

class OperationModel(BaseModel):
    permission_id: int = Field(gt=0)

class CreateOperationRequest(BaseModel):
    app_signature: str
    operation: OperationModel

class OperationLinks(BaseModel):
    get: str
    cancel: str

class CreateOperationResponse(BaseModel):
    id: str
    created_at: str

class GetOperationResponse(BaseModel):
    id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    result: str | None = None

class ErrorResponse(BaseModel):
    detail: str