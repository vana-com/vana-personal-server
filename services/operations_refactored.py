"""
Refactored operations service following SOLID principles.
Split into focused services with single responsibilities.
"""
from typing import Dict, List, Optional, Any
import json
import logging

from compute.base import ExecuteResponse, GetResponse
from compute.provider_factory import get_compute_factory
from domain.entities import GrantFile, PermissionData, FileMetadata
from domain.exceptions import (
    VanaAPIError, ValidationError, AuthenticationError,
    AuthorizationError, NotFoundError, BlockchainError,
    FileAccessError, ComputeError, GrantValidationError
)
from services.task_store import get_task_store
from utils.auth import signature_auth

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Handles signature verification and authentication (SRP)."""
    
    def verify_request_signature(self, request_json: str, signature: str) -> str:
        """
        Verify request signature and return the app address.
        
        Args:
            request_json: The signed request JSON
            signature: The signature to verify
            
        Returns:
            The recovered app address
            
        Raises:
            AuthenticationError: If signature verification fails
        """
        try:
            return signature_auth.verify_signature(request_json, signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            raise AuthenticationError("Invalid signature or unable to recover app address")


class PermissionService:
    """Handles blockchain permission operations (SRP)."""
    
    def __init__(self, chain):
        self.chain = chain
    
    async def fetch_permission(self, permission_id: int, app_address: str) -> PermissionData:
        """
        Fetch permission from blockchain.
        
        Args:
            permission_id: The permission ID to fetch
            app_address: The app address requesting the permission
            
        Returns:
            PermissionData containing the permission details
            
        Raises:
            NotFoundError: If permission not found
            AuthorizationError: If app not authorized
        """
        # This would contain the blockchain fetching logic
        # Simplified for illustration
        pass


class FileService:
    """Handles file operations including download and decryption (SRP)."""
    
    async def fetch_and_decrypt_files(
        self, 
        file_metadata_list: List[FileMetadata],
        server_private_key: bytes
    ) -> List[str]:
        """
        Download and decrypt files.
        
        Args:
            file_metadata_list: List of file metadata
            server_private_key: Private key for decryption
            
        Returns:
            List of decrypted file contents
            
        Raises:
            FileAccessError: If file download fails
            DecryptionError: If decryption fails
        """
        # This would contain file download and decryption logic
        # Simplified for illustration
        pass


class GrantValidationService:
    """Handles grant file validation (SRP)."""
    
    def validate_grant(self, grant_file: GrantFile, permission: PermissionData) -> None:
        """
        Validate grant file against permission.
        
        Args:
            grant_file: The grant file to validate
            permission: The permission to validate against
            
        Raises:
            GrantValidationError: If validation fails
        """
        # Validation logic here
        pass


class ComputeRouter:
    """Routes operations to appropriate compute providers (SRP)."""
    
    def __init__(self, factory=None):
        self.factory = factory or get_compute_factory()
    
    async def route_operation(
        self, 
        operation_type: str,
        grant_file: GrantFile,
        files_content: List[str]
    ) -> ExecuteResponse:
        """
        Route operation to appropriate compute provider.
        
        Args:
            operation_type: Type of operation
            grant_file: Grant file with parameters
            files_content: Decrypted file contents
            
        Returns:
            ExecuteResponse from the compute provider
            
        Raises:
            ComputeError: If operation fails
        """
        provider = self.factory.create_provider(operation_type)
        
        if not provider:
            raise ComputeError(f"Unsupported operation type: {operation_type}")
        
        try:
            # Check if provider has async execute
            if hasattr(provider, 'execute') and asyncio.iscoroutinefunction(provider.execute):
                return await provider.execute(grant_file, files_content)
            else:
                # Fallback for sync providers
                return provider.execute(grant_file, files_content)
        except Exception as e:
            logger.error(f"Compute operation failed: {e}")
            raise ComputeError(f"Operation failed: {str(e)}")


class RefactoredOperationsService:
    """
    Orchestrates operations using composed services.
    This is much simpler than the original monolithic service.
    """
    
    def __init__(
        self,
        auth_service: AuthenticationService,
        permission_service: PermissionService,
        file_service: FileService,
        grant_validator: GrantValidationService,
        compute_router: ComputeRouter
    ):
        """
        Initialize with injected dependencies.
        All services are injected, making testing and modification easy.
        """
        self.auth = auth_service
        self.permissions = permission_service
        self.files = file_service
        self.validator = grant_validator
        self.router = compute_router
    
    async def create(self, request_json: str, signature: str) -> ExecuteResponse:
        """
        Create and execute an operation.
        
        This method orchestrates the various services but doesn't
        implement the logic itself (following SRP).
        """
        # 1. Authenticate request
        app_address = self.auth.verify_request_signature(request_json, signature)
        
        # 2. Parse request
        request_data = json.loads(request_json)
        permission_id = request_data.get("permission_id")
        
        if not permission_id:
            raise ValidationError("Missing permission_id", "permission_id")
        
        # 3. Fetch permission from blockchain
        permission = await self.permissions.fetch_permission(permission_id, app_address)
        
        # 4. Fetch and validate grant file
        grant_file = await self._fetch_grant_file(permission.grant_file_url)
        self.validator.validate_grant(grant_file, permission)
        
        # 5. Fetch and decrypt files if needed
        files_content = []
        if permission.file_metadata_list:
            files_content = await self.files.fetch_and_decrypt_files(
                permission.file_metadata_list,
                permission.server_private_key
            )
        
        # 6. Route to compute provider
        return await self.router.route_operation(
            grant_file.operation,
            grant_file,
            files_content
        )
    
    async def get(self, operation_id: str) -> GetResponse:
        """Get operation status and results."""
        # Delegate to task store or compute provider
        task_store = get_task_store()
        task_info = await task_store.get_task(operation_id)
        
        if task_info:
            # Format response from task info
            return self._format_task_response(task_info)
        
        # Fallback to compute provider (for backward compatibility)
        provider = self.router.factory.create_from_operation_id(operation_id)
        if provider and hasattr(provider, 'get'):
            return await provider.get(operation_id)
        
        raise NotFoundError(f"Operation {operation_id} not found")
    
    async def cancel(self, operation_id: str) -> bool:
        """Cancel an operation."""
        # Try task store first
        task_store = get_task_store()
        success = await task_store.cancel_task(operation_id)
        
        if not success:
            # Fallback to compute provider
            provider = self.router.factory.create_from_operation_id(operation_id)
            if provider and hasattr(provider, 'cancel'):
                return await provider.cancel(operation_id)
        
        return success
    
    async def _fetch_grant_file(self, grant_url: str) -> GrantFile:
        """Fetch and parse grant file from URL."""
        # Implementation would fetch from IPFS/URL
        # Simplified for illustration
        pass
    
    def _format_task_response(self, task_info) -> GetResponse:
        """Format task info into GetResponse."""
        # Implementation would format the response
        # Simplified for illustration
        pass


def create_operations_service(chain, settings=None):
    """
    Factory function to create operations service with all dependencies.
    This makes it easy to swap implementations or add decorators.
    """
    return RefactoredOperationsService(
        auth_service=AuthenticationService(),
        permission_service=PermissionService(chain),
        file_service=FileService(),
        grant_validator=GrantValidationService(),
        compute_router=ComputeRouter()
    )