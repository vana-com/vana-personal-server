from typing import Optional


class VanaAPIError(Exception):
    """Base exception for Vana API errors"""
    
    def __init__(self, message: str, error_code: str, status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class ValidationError(VanaAPIError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        error_code = f"VALIDATION_ERROR_{field.upper()}" if field else "VALIDATION_ERROR"
        super().__init__(message, error_code, 400)
        self.field = field


class AuthenticationError(VanaAPIError):
    """Raised when signature verification fails"""
    
    def __init__(self, message: str = "Invalid signature"):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(VanaAPIError):
    """Raised when permission checks fail"""
    
    def __init__(self, message: str):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class NotFoundError(VanaAPIError):
    """Raised when requested resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} '{resource_id}' not found"
        super().__init__(message, "NOT_FOUND_ERROR", 404)


class BlockchainError(VanaAPIError):
    """Raised when blockchain operations fail"""
    
    def __init__(self, message: str):
        super().__init__(message, "BLOCKCHAIN_ERROR", 500)


class FileAccessError(VanaAPIError):
    """Raised when file operations fail"""
    
    def __init__(self, message: str):
        super().__init__(message, "FILE_ACCESS_ERROR", 500)


class ComputeError(VanaAPIError):
    """Raised when compute operations fail"""
    
    def __init__(self, message: str):
        super().__init__(message, "COMPUTE_ERROR", 500)


class DecryptionError(VanaAPIError):
    """Raised when decryption fails"""
    
    def __init__(self, message: str):
        super().__init__(message, "DECRYPTION_ERROR", 500)


class GrantValidationError(VanaAPIError):
    """Raised when grant validation fails"""
    
    def __init__(self, message: str):
        super().__init__(message, "GRANT_VALIDATION_ERROR", 400)


class OperationError(VanaAPIError):
    """Raised when operation processing fails"""
    
    def __init__(self, message: str, operation_id: Optional[str] = None):
        super().__init__(message, "OPERATION_ERROR", 500)
        self.operation_id = operation_id


class SubgraphError(VanaAPIError):
    """Base exception for subgraph-related errors"""
    
    def __init__(self, message: str, error_code: str = "SUBGRAPH_ERROR", status_code: int = 500):
        super().__init__(message, error_code, status_code)


class SubgraphQueryError(SubgraphError):
    """Raised when GraphQL query fails"""
    
    def __init__(self, message: str, query: Optional[str] = None, variables: Optional[dict] = None):
        super().__init__(message, "SUBGRAPH_QUERY_ERROR", 502)
        self.query = query
        self.variables = variables


class SubgraphConnectionError(SubgraphError):
    """Raised when subgraph connection fails"""
    
    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(message, "SUBGRAPH_CONNECTION_ERROR", 502)
        self.url = url


class SubgraphOwnerMismatchError(AuthorizationError):
    """Raised when file owner doesn't match requested owner"""
    
    def __init__(self, file_id: int, expected_owner: str, actual_owner: str):
        message = f"File {file_id} owner mismatch: expected {expected_owner}, got {actual_owner}"
        super().__init__(message)
        self.file_id = file_id
        self.expected_owner = expected_owner
        self.actual_owner = actual_owner