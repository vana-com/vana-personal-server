from typing import Annotated, Optional, Dict, Any, Literal
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
    kind: str = Field(default="PersonalServer", description="Resource type identifier")
    address: EthereumAddress
    public_key: PublicKey

class IdentityResponseModel(BaseModel):
    kind: str = Field(default="Identity", description="Resource type identifier")
    user_address: EthereumAddress
    personal_server: PersonalServerModel

class CreateOperationRequest(BaseModel):
    app_signature: str
    operation_request_json: str

class CreateOperationResponse(BaseModel):
    kind: str = Field(default="OperationCreated", description="Resource type identifier")
    id: str
    created_at: str

class GetOperationResponse(BaseModel):
    kind: str = Field(default="OperationStatus", description="Resource type identifier")
    id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    result: str | None = None

class ErrorResponse(BaseModel):
    kind: str = Field(default="Error", description="Resource type identifier")
    detail: str
    error_code: str
    field: str | None = None