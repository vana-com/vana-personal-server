import json
import logging
import sys
import platform

import web3
from compute.base import BaseCompute, ExecuteResponse, GetResponse
from domain.entities import FileMetadata
from domain.value_objects import PersonalServerRequest
from eth_account.messages import encode_defunct
from domain.exceptions import (
    AuthenticationError,
    BlockchainError,
    ComputeError,
    DecryptionError,
    FileAccessError,
    GrantValidationError,
    NotFoundError,
    OperationError,
    ValidationError,
)
from utils.files import decrypt_user_data, decrypt_with_private_key, download_file
from grants import fetch_raw_grant_file, validate
from onchain.chain import Chain
from onchain.data_permissions import DataPermissions
from onchain.data_registry import DataRegistry
from services.identity import IdentityService

logger = logging.getLogger(__name__)


class OperationsService:
    """Service that enforces protocol rules for processing permissions and proxies to compute endpoints."""

    def __init__(self, compute: BaseCompute, chain: Chain):
        logger.info("[OPERATIONS INIT] Starting OperationsService initialization")
        logger.info(f"[OPERATIONS INIT] Python version: {sys.version}")
        logger.info(f"[OPERATIONS INIT] Platform: {platform.platform()}")
        logger.info(f"[OPERATIONS INIT] Web3 module location: {web3.__file__}")
        logger.info(f"[OPERATIONS INIT] Web3 version: {web3.__version__}")
        
        self.compute = compute
        
        logger.info(f"[OPERATIONS INIT] Creating Web3 instance with chain URL: {chain.url}")
        try:
            self.web3 = web3.Web3(web3.HTTPProvider(chain.url))
            logger.info(f"[OPERATIONS INIT] Web3 instance created successfully")
            logger.info(f"[OPERATIONS INIT] Web3 is connected: {self.web3.is_connected()}")
            if self.web3.is_connected():
                logger.info(f"[OPERATIONS INIT] Latest block: {self.web3.eth.block_number}")
        except Exception as e:
            logger.error(f"[OPERATIONS INIT] Failed to create Web3 instance: {e}")
            logger.error(f"[OPERATIONS INIT] Exception type: {type(e).__name__}")
            raise
        
        logger.info("[OPERATIONS INIT] Creating DataRegistry instance")
        self.data_registry = DataRegistry(chain, self.web3)
        logger.info("[OPERATIONS INIT] DataRegistry created successfully")
        
        logger.info("[OPERATIONS INIT] Creating DataPermissions instance")
        self.data_permissions = DataPermissions(chain, self.web3)
        logger.info("[OPERATIONS INIT] DataPermissions created successfully")
        
        logger.info("[OPERATIONS INIT] OperationsService initialization complete")

    def create(self, request_json: str, signature: str) -> ExecuteResponse:
        import uuid
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[REQUEST {request_id}] Starting create operation")
        
        try:
            request = PersonalServerRequest(**json.loads(request_json))
            logger.info(f"[REQUEST {request_id}] Parsed request with permission_id: {request.permission_id}")
        except (json.JSONDecodeError, TypeError) as e:
            raise ValidationError(
                "Invalid JSON format in operation request", "operation_request_json"
            )

        if request.permission_id <= 0:
            raise ValidationError("Valid permission ID is required", "permission_id")

        try:
            app_address = self._recover_app_address(request_json, signature)
            logger.info(f"[REQUEST {request_id}] Recovered app address: {app_address}")
        except Exception as e:
            raise AuthenticationError(
                "Invalid signature or unable to recover app address"
            )

        logger.info(f"[REQUEST {request_id}] Moving to permission fetch phase")
        
        try:
            logger.info(f"[REQUEST {request_id}] About to fetch permission {request.permission_id} from blockchain")
            logger.info(f"[OPERATIONS] DataPermissions object: {self.data_permissions}")
            logger.info(f"[OPERATIONS] DataPermissions class: {type(self.data_permissions).__name__}")
            
            permission = self.data_permissions.fetch_permission_from_blockchain(
                request.permission_id
            )
            
            logger.info(f"[OPERATIONS] Successfully fetched permission: {permission}")
            if not permission:
                raise NotFoundError("Permission", str(request.permission_id))
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise BlockchainError(
                f"Failed to fetch permission from blockchain: {str(e)}"
            )

        if not permission.file_ids or len(permission.file_ids) == 0:
            raise ValidationError("No file IDs found in permission")

        try:
            raw_grant_file = fetch_raw_grant_file(permission.grant)
            if not raw_grant_file:
                raise FileAccessError(
                    f"Grant data not found or invalid at {permission.grant}"
                )
        except Exception as e:
            if isinstance(e, FileAccessError):
                raise
            raise FileAccessError(f"Failed to fetch grant file: {str(e)}")

        try:
            grant_file = validate(raw_grant_file, app_address)
        except Exception as e:
            raise GrantValidationError(f"Grant validation failed: {str(e)}")

        try:
            server_private_key, server_address = self._derive_user_server_keys(
                permission.grantor
            )
            logger.info(f"Derived server address: {server_address}")
        except Exception as e:
            raise OperationError(f"Failed to derive server keys: {str(e)}")

        files_metadata = self._fetch_files_metadata(permission.file_ids, server_address)
        files_content = self._decrypt_files_content(files_metadata, server_private_key)

        try:
            return self.compute.execute(grant_file, files_content)
        except Exception as e:
            raise ComputeError(f"Compute operation failed: {str(e)}")

    def get(self, operation_id: str) -> GetResponse:
        try:
            result = self.compute.get(operation_id)
            if not result:
                raise NotFoundError("Operation", operation_id)
            return result
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            logger.error(f"Failed to get operation {operation_id}: {str(e)}")
            raise ComputeError(f"Failed to get operation: {str(e)}")

    def cancel(self, operation_id: str) -> bool:
        try:
            result = self.compute.cancel(operation_id)
            if result is None:
                raise NotFoundError("Operation", operation_id)
            return result
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            raise ComputeError(f"Failed to cancel operation: {str(e)}")

    def _recover_app_address(self, request_json: str, signature: str):
        message = encode_defunct(text=request_json)
        return self.web3.eth.account.recover_message(message, signature=signature)

    def _derive_user_server_keys(self, grantor: str) -> tuple[str, str]:
        identity_service = IdentityService()
        identity_response = identity_service.derive_server_identity(grantor)
        return identity_response.personal_server.private_key, identity_response.personal_server.address

    def _fetch_files_metadata(
        self, file_ids: list[int], server_address: str
    ) -> list[FileMetadata]:
        files_metadata = []
        for file_id in file_ids:
            try:
                file_metadata = self.data_registry.fetch_file_metadata(
                    file_id, server_address
                )

                if not file_metadata:
                    raise NotFoundError("File", str(file_id))

                files_metadata.append(file_metadata)
            except Exception as e:
                if isinstance(e, NotFoundError):
                    raise
                raise BlockchainError(
                    f"Failed to fetch file metadata for file {file_id}: {str(e)}"
                )

        return files_metadata

    def _decrypt_files_content(
        self, files_metadata: list[FileMetadata], server_private_key: str
    ) -> list[str]:
        files_content = []
        for file_metadata in files_metadata:
            try:
                encrypted_file_content = download_file(file_metadata.public_url)
                logger.info(
                    f"Fetched file content from {file_metadata.public_url}. File size: {len(encrypted_file_content)} bytes"
                )
                logger.debug(f"Processing encrypted key for file {file_metadata.file_id}")
                logger.debug(f"Using server private key for decryption")

                decrypted_encryption_key = decrypt_with_private_key(
                    file_metadata.encrypted_key, server_private_key
                )
                decrypted_file_content_bytes = decrypt_user_data(
                    encrypted_file_content, decrypted_encryption_key
                )
                decrypted_file_content = decrypted_file_content_bytes.decode("utf-8")
                files_content.append(decrypted_file_content)
            except Exception as e:
                if "download" in str(e).lower():
                    raise FileAccessError(
                        f"Failed to download file from {file_metadata.public_url}: {str(e)}"
                    )
                else:
                    raise DecryptionError(
                        f"Failed to decrypt file {file_metadata.file_id}: {str(e)}"
                    )

        return files_content
