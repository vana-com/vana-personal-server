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