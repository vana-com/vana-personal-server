import pytest
from pydantic import ValidationError, BaseModel
from api.schemas import EthereumAddress

class TestModel(BaseModel):
    address: EthereumAddress

def test_valid_ethereum_address():
    valid = "0x1234567890abcdef1234567890abcdef12345678"
    m = TestModel(address=valid)
    assert m.address == valid

def test_invalid_ethereum_address_format():
    with pytest.raises(ValidationError):
        TestModel(address="0x1234")
    with pytest.raises(ValidationError):
        TestModel(address="1234567890abcdef1234567890abcdef12345678")
    with pytest.raises(ValidationError):
        TestModel(address="0xGHIJKL7890abcdef1234567890abcdef12345678")
    with pytest.raises(ValidationError):
        TestModel(address="0x1234567890abcdef1234567890abcdef1234567890") 