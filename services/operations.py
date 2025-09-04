import json
import logging
import time

from web3 import AsyncWeb3
from compute.base import BaseCompute, ExecuteResponse, GetResponse
from services.compute_registry import get_compute_registry
from domain.entities import FileMetadata, GrantFile
from domain.operation_context import OperationContext
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
from onchain.data_portability_grantees import DataPortabilityGrantees
from services.identity import IdentityService

logger = logging.getLogger(__name__)


class OperationsService:
    """Service that enforces protocol rules for processing permissions and proxies to compute endpoints."""

    def __init__(self, compute: BaseCompute, chain: Chain):
        self.compute = compute
        self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(chain.url))
        self.data_registry = DataRegistry(chain, self.web3)
        self.data_permissions = DataPermissions(chain, self.web3)
        self.data_portability_grantees = DataPortabilityGrantees(chain, self.web3)

    async def create(self, request_json: str, signature: str, request_id: str = None) -> ExecuteResponse:
        if not request_id:
            request_id = f"svc_req_{int(__import__('time').time() * 1000)}"
            
        logger.info(f"[SERVICE] Starting operation creation [RequestID: {request_id}]")
        
        try:
            request = PersonalServerRequest(**json.loads(request_json))
            logger.info(f"[SERVICE] Parsed request - Permission ID: {request.permission_id} [RequestID: {request_id}]")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"[SERVICE] JSON parsing failed: {str(e)} [RequestID: {request_id}]")
            logger.error(f"[SERVICE] Raw request JSON: {request_json} [RequestID: {request_id}]")
            raise ValidationError(
                "Invalid JSON format in operation request", "operation_request_json"
            )

        if request.permission_id <= 0:
            logger.error(f"[SERVICE] Invalid permission ID: {request.permission_id} [RequestID: {request_id}]")
            raise ValidationError("Valid permission ID is required", "permission_id")

        try:
            app_address = self._recover_app_address(request_json, signature)
            logger.info(f"[SERVICE] Recovered app address: {app_address} [RequestID: {request_id}]")
            logger.info(f"[SERVICE] Signature verification successful for permission {request.permission_id} [RequestID: {request_id}]")
        except Exception as e:
            logger.error(f"[SERVICE] Signature recovery failed: {str(e)} [RequestID: {request_id}]")
            logger.error(f"[SERVICE] Signature (first 20 chars): {signature[:20]}... [RequestID: {request_id}]")
            logger.error(f"[SERVICE] Request JSON hash: {hash(request_json)} [RequestID: {request_id}]")
            raise AuthenticationError(
                "Invalid signature or unable to recover app address"
            )

        try:
            logger.info(f"[SERVICE] Fetching permission {request.permission_id} from blockchain [RequestID: {request_id}]")
            permission = await self.data_permissions.fetch_permission_from_blockchain(
                request.permission_id
            )
            if not permission:
                logger.error(f"[SERVICE] Permission {request.permission_id} not found on blockchain [RequestID: {request_id}]")
                raise NotFoundError("Permission", str(request.permission_id))
            
            logger.info(f"[SERVICE] Permission fetched successfully - Grantor: {permission.grantor}, Grant: {permission.grant}, File IDs: {permission.file_ids} [RequestID: {request_id}]")
            logger.info(f"[SERVICE] Permission details - Grantee: {getattr(permission, 'grantee', 'N/A')}, Valid until: {getattr(permission, 'valid_until', 'N/A')} [RequestID: {request_id}]")
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            logger.error(f"[SERVICE] Blockchain permission fetch failed: {str(e)} [RequestID: {request_id}]")
            logger.error(f"[SERVICE] Contract call details - Permission ID: {request.permission_id}, Chain URL: {self.web3.provider.endpoint_uri} [RequestID: {request_id}]")
            raise BlockchainError(
                f"Failed to fetch permission from blockchain: {str(e)}"
            )

        if not permission.file_ids or len(permission.file_ids) == 0:
            logger.error(f"[SERVICE] No file IDs in permission {request.permission_id} [RequestID: {request_id}]")
            raise ValidationError("No file IDs found in permission")

        # Look up the grantee info from the on-chain record using the granteeId
        try:
            logger.info(f"[SERVICE] Resolving granteeId {permission.grantee_id} to address [RequestID: {request_id}]")
            grantee_info = await self.data_portability_grantees.get_grantee_info(permission.grantee_id)
            if not grantee_info:
                logger.error(f"[SERVICE] Grantee {permission.grantee_id} not found on blockchain [RequestID: {request_id}]")
                raise NotFoundError("Grantee", str(permission.grantee_id))
            
            on_chain_grantee_address = grantee_info['granteeAddress']
            logger.info(f"[SERVICE] Resolved granteeId {permission.grantee_id} to address {on_chain_grantee_address} [RequestID: {request_id}]")
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            logger.error(f"[SERVICE] Failed to resolve granteeId {permission.grantee_id}: {str(e)} [RequestID: {request_id}]")
            raise BlockchainError(f"Failed to resolve granteeId {permission.grantee_id}: {str(e)}")

        # Perform the correct validation: The signature must come from the on-chain grantee
        if app_address.lower() != on_chain_grantee_address.lower():
            logger.error(f"[SERVICE] Signature mismatch: recovered {app_address}, expected {on_chain_grantee_address} [RequestID: {request_id}]")
            raise AuthenticationError(
                f"Signature recovered address {app_address} does not match on-chain grantee address {on_chain_grantee_address}"
            )

        try:
            logger.info(f"[SERVICE] Fetching grant file from: {permission.grant} [RequestID: {request_id}]")
            raw_grant_file = fetch_raw_grant_file(permission.grant)
            if not raw_grant_file:
                logger.error(f"[SERVICE] Grant file empty or invalid at {permission.grant} [RequestID: {request_id}]")
                raise FileAccessError(
                    f"Grant data not found or invalid at {permission.grant}"
                )
            logger.info(f"[SERVICE] Grant file fetched successfully, size: {len(raw_grant_file)} bytes [RequestID: {request_id}]")
        except Exception as e:
            if isinstance(e, FileAccessError):
                raise
            logger.error(f"[SERVICE] Grant file fetch failed: {str(e)} [RequestID: {request_id}]")
            raise FileAccessError(f"Failed to fetch grant file: {str(e)}")

        try:
            logger.info(f"[SERVICE] Validating grant file against on-chain grantee address {on_chain_grantee_address} [RequestID: {request_id}]")
            grant_file = validate(raw_grant_file, on_chain_grantee_address)
            logger.info(f"[SERVICE] Grant validation successful [RequestID: {request_id}]")
            # Optional: Log warning if grant file's grantee doesn't match the on-chain record
            if raw_grant_file.get("grantee", "").lower() != on_chain_grantee_address.lower():
                logger.warning(f"[SERVICE] Grant file's grantee {raw_grant_file.get('grantee')} doesn't match on-chain grantee {on_chain_grantee_address} [RequestID: {request_id}]")
        except Exception as e:
            logger.error(f"[SERVICE] Grant validation failed: {str(e)} [RequestID: {request_id}]")
            logger.error(f"[SERVICE] On-chain grantee: {on_chain_grantee_address}, Grant size: {len(raw_grant_file)} bytes [RequestID: {request_id}]")
            raise GrantValidationError(f"Grant validation failed: {str(e)}")

        # Validate response_format parameter if present
        try:
            self._validate_response_format(grant_file, request_id)
        except Exception as e:
            logger.error(f"[SERVICE] Response format validation failed: {str(e)} [RequestID: {request_id}]")
            raise ValidationError(f"Invalid response_format in grant file: {str(e)}")

        try:
            logger.info(f"[SERVICE] Deriving server keys for grantor: {permission.grantor} [RequestID: {request_id}]")
            server_private_key, server_address = self._derive_user_server_keys(
                permission.grantor
            )
            logger.info(f"[SERVICE] Derived server address: {server_address} [RequestID: {request_id}]")
        except Exception as e:
            logger.error(f"[SERVICE] Server key derivation failed: {str(e)} [RequestID: {request_id}]")
            logger.error(f"[SERVICE] Grantor address: {permission.grantor} [RequestID: {request_id}]")
            raise OperationError(f"Failed to derive server keys: {str(e)}")

        logger.info(f"[SERVICE] Starting file metadata fetch for {len(permission.file_ids)} files [RequestID: {request_id}]")
        files_metadata = await self._fetch_files_metadata(permission.file_ids, server_address, request_id)
        
        logger.info(f"[SERVICE] Starting file content decryption for {len(files_metadata)} files [RequestID: {request_id}]")
        files_content = self._decrypt_files_content(files_metadata, server_private_key, request_id)

        # Create operation context with both addresses
        operation_id = f"{grant_file.operation}_{int(time.time() * 1000)}"
        context = OperationContext(
            operation_id=operation_id,
            grantor=permission.grantor,  # User who owns the data
            grantee=app_address,  # App with delegated access
            permission_id=request.permission_id
        )
        logger.info(f"[SERVICE] Created operation context - ID: {operation_id}, Grantor: {permission.grantor}, Grantee: {app_address} [RequestID: {request_id}]")

        try:
            # Use registry to get appropriate compute provider
            registry = get_compute_registry()
            provider = registry.get_provider(grant_file.operation)
            
            if provider:
                logger.info(f"[SERVICE] Using registered provider for '{grant_file.operation}' [RequestID: {request_id}]")
                result = await provider.execute(grant_file, files_content, context)
            else:
                # Fallback to default compute provider for unregistered operations
                logger.info(f"[SERVICE] No registered provider for '{grant_file.operation}', using default [RequestID: {request_id}]")
                result = await self.compute.execute(grant_file, files_content, context)
            
            logger.info(f"[SERVICE] Compute operation completed successfully, operation ID: {result.id} [RequestID: {request_id}]")
            return result
        except Exception as e:
            logger.error(f"[SERVICE] Compute operation failed: {str(e)} [RequestID: {request_id}]")
            logger.error(f"[SERVICE] Grant file type: {type(grant_file)}, Files count: {len(files_content)} [RequestID: {request_id}]")
            raise ComputeError(f"Compute operation failed: {str(e)}")

    async def get(self, operation_id: str) -> GetResponse:
        logger.info(f"[SERVICE] Getting operation status for {operation_id}")
        try:
            # Check if this is an agent operation based on ID prefix
            if operation_id.startswith("qwen_") or operation_id.startswith("prompt_qwen_agent"):
                logger.info(f"[SERVICE] Routing get request to Qwen agent provider for {operation_id}")
                from compute.qwen_agent import QwenCodeAgentProvider
                agent_provider = QwenCodeAgentProvider()
                result = await agent_provider.get(operation_id)
            elif operation_id.startswith("gemini_") or operation_id.startswith("prompt_gemini_agent"):
                logger.info(f"[SERVICE] Routing get request to Gemini agent provider for {operation_id}")
                from compute.gemini_agent import GeminiAgentProvider
                agent_provider = GeminiAgentProvider()
                result = await agent_provider.get(operation_id)
            else:
                result = self.compute.get(operation_id)
            
            if not result:
                logger.error(f"[SERVICE] Operation {operation_id} not found in compute layer")
                raise NotFoundError("Operation", operation_id)
            logger.info(f"[SERVICE] Operation {operation_id} found - Status: {result.status}")
            return result
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            logger.error(f"[SERVICE] Failed to get operation {operation_id}: {str(e)}")
            raise ComputeError(f"Failed to get operation: {str(e)}")

    def cancel(self, operation_id: str) -> bool:
        logger.info(f"[SERVICE] Cancelling operation {operation_id}")
        try:
            # Check if this is an agent operation based on ID prefix
            if operation_id.startswith("qwen_") or operation_id.startswith("prompt_qwen_agent"):
                logger.info(f"[SERVICE] Routing cancel request to Qwen agent provider for {operation_id}")
                from compute.qwen_agent import QwenCodeAgentProvider
                agent_provider = QwenCodeAgentProvider()
                result = agent_provider.cancel(operation_id)
            elif operation_id.startswith("gemini_") or operation_id.startswith("prompt_gemini_agent"):
                logger.info(f"[SERVICE] Routing cancel request to Gemini agent provider for {operation_id}")
                from compute.gemini_agent import GeminiAgentProvider
                agent_provider = GeminiAgentProvider()
                result = agent_provider.cancel(operation_id)
            else:
                result = self.compute.cancel(operation_id)
            
            if result is None:
                logger.error(f"[SERVICE] Operation {operation_id} not found for cancellation")
                raise NotFoundError("Operation", operation_id)
            logger.info(f"[SERVICE] Operation {operation_id} cancellation result: {result}")
            return result
        except Exception as e:
            if isinstance(e, NotFoundError):
                raise
            logger.error(f"[SERVICE] Failed to cancel operation {operation_id}: {str(e)}")
            raise ComputeError(f"Failed to cancel operation: {str(e)}")

    def _recover_app_address(self, request_json: str, signature: str):
        logger.debug(f"[SERVICE] Recovering app address from signature")
        message = encode_defunct(text=request_json)
        recovered_address = self.web3.eth.account.recover_message(message, signature=signature)
        logger.debug(f"[SERVICE] Message body length: {len(message.body)}, Recovered address: {recovered_address}")
        return recovered_address

    def _derive_user_server_keys(self, grantor: str) -> tuple[str, str]:
        logger.debug(f"[SERVICE] Deriving server identity for grantor: {grantor}")
        identity_service = IdentityService()
        identity_response = identity_service.derive_server_identity(grantor)
        logger.debug(f"[SERVICE] Server identity derived successfully for grantor: {grantor}")
        return identity_response.personal_server.private_key, identity_response.personal_server.address

    async def _fetch_files_metadata(
        self, file_ids: list[int], server_address: str, request_id: str = None
    ) -> list[FileMetadata]:
        if not request_id:
            request_id = f"fetch_meta_{int(__import__('time').time() * 1000)}"
            
        files_metadata = []
        for i, file_id in enumerate(file_ids):
            try:
                logger.info(f"[SERVICE] Fetching metadata for file {file_id} ({i+1}/{len(file_ids)}) [RequestID: {request_id}]")
                file_metadata = await self.data_registry.fetch_file_metadata(
                    file_id, server_address
                )

                if not file_metadata:
                    logger.error(f"[SERVICE] File {file_id} metadata not found on blockchain [RequestID: {request_id}]")
                    raise NotFoundError("File", str(file_id))

                logger.info(f"[SERVICE] File {file_id} metadata fetched - URL: {file_metadata.public_url}, Owner: {file_metadata.owner_address} [RequestID: {request_id}]")
                files_metadata.append(file_metadata)
            except Exception as e:
                if isinstance(e, NotFoundError):
                    raise
                logger.error(f"[SERVICE] Failed to fetch metadata for file {file_id}: {str(e)} [RequestID: {request_id}]")
                logger.error(f"[SERVICE] Contract call details - File ID: {file_id}, Server: {server_address}, Chain: {self.web3.provider.endpoint_uri} [RequestID: {request_id}]")
                raise BlockchainError(
                    f"Failed to fetch file metadata for file {file_id}: {str(e)}"
                )

        return files_metadata

    def _decrypt_files_content(
        self, files_metadata: list[FileMetadata], server_private_key: str, request_id: str = None
    ) -> list[str]:
        if not request_id:
            request_id = f"decrypt_{int(__import__('time').time() * 1000)}"
            
        files_content = []
        for i, file_metadata in enumerate(files_metadata):
            try:
                logger.info(f"[SERVICE] Downloading file {file_metadata.file_id} ({i+1}/{len(files_metadata)}) from {file_metadata.public_url} [RequestID: {request_id}]")
                encrypted_file_content = download_file(file_metadata.public_url)
                logger.info(
                    f"[SERVICE] Downloaded file {file_metadata.file_id} successfully. Size: {len(encrypted_file_content)} bytes [RequestID: {request_id}]"
                )
                
                logger.info(f"[SERVICE] Decrypting encryption key for file {file_metadata.file_id} [RequestID: {request_id}]")
                decrypted_encryption_key = decrypt_with_private_key(
                    file_metadata.encrypted_key, server_private_key
                )
                
                logger.info(f"[SERVICE] Decrypting file content for file {file_metadata.file_id} [RequestID: {request_id}]")
                decrypted_file_content_bytes = decrypt_user_data(
                    encrypted_file_content, decrypted_encryption_key
                )
                decrypted_file_content = decrypted_file_content_bytes.decode("utf-8")
                
                logger.info(f"[SERVICE] File {file_metadata.file_id} decrypted successfully. Content size: {len(decrypted_file_content)} chars [RequestID: {request_id}]")
                files_content.append(decrypted_file_content)
            except Exception as e:
                if "download" in str(e).lower():
                    logger.error(f"[SERVICE] File download failed for {file_metadata.file_id}: {str(e)} [RequestID: {request_id}]")
                    logger.error(f"[SERVICE] Download URL: {file_metadata.public_url} [RequestID: {request_id}]")
                    raise FileAccessError(
                        f"Failed to download file from {file_metadata.public_url}: {str(e)}"
                    )
                else:
                    logger.error(f"[SERVICE] File decryption failed for {file_metadata.file_id}: {str(e)} [RequestID: {request_id}]")
                    logger.error(f"[SERVICE] Encrypted key length: {len(file_metadata.encrypted_key)} [RequestID: {request_id}]")
                    raise DecryptionError(
                        f"Failed to decrypt file {file_metadata.file_id}: {str(e)}"
                    )

        return files_content

    def _validate_response_format(self, grant_file: GrantFile, request_id: str = None):
        """Validate response_format parameter in grant file.
        
        Args:
            grant_file: The grant file to validate
            request_id: Request ID for logging
            
        Raises:
            ValidationError: If response_format is invalid or not allowed for this operation
        """
        if not request_id:
            request_id = f"validate_{int(__import__('time').time() * 1000)}"
        
        response_format = grant_file.parameters.get("response_format")
        
        # If no response_format is specified, that's fine - defaults to text mode
        if response_format is None:
            logger.debug(f"[SERVICE] No response_format specified, defaulting to text mode [RequestID: {request_id}]")
            return
        
        # response_format is only valid for llm_inference operations (not agent operations)
        agent_operations = ["agentic_task", "prompt_qwen_agent", "prompt_gemini_agent"]
        if grant_file.operation not in ["llm_inference"] and grant_file.operation not in agent_operations:
            logger.error(f"[SERVICE] response_format specified for unsupported operation: {grant_file.operation} [RequestID: {request_id}]")
            raise ValidationError(f"response_format is only valid for llm_inference operations, not {grant_file.operation}")
        
        # Agent operations don't support response_format
        if grant_file.operation in agent_operations:
            logger.debug(f"[SERVICE] Ignoring response_format for agent operation: {grant_file.operation} [RequestID: {request_id}]")
            return
        
        # Validate response_format structure
        if not isinstance(response_format, dict):
            logger.error(f"[SERVICE] response_format must be a dict, got {type(response_format)} [RequestID: {request_id}]")
            raise ValidationError(f"response_format must be an object, got {type(response_format).__name__}")
        
        # Validate required 'type' field
        format_type = response_format.get("type")
        if not format_type:
            logger.error(f"[SERVICE] response_format missing required 'type' field [RequestID: {request_id}]")
            raise ValidationError("response_format must include a 'type' field")
        
        # Validate type value
        valid_types = ["text", "json_object"]
        if format_type not in valid_types:
            logger.error(f"[SERVICE] Invalid response_format type: {format_type}, valid types: {valid_types} [RequestID: {request_id}]")
            raise ValidationError(f"response_format.type must be one of {valid_types}, got '{format_type}'")
        
        logger.info(f"[SERVICE] Response format validation successful: {response_format} [RequestID: {request_id}]")
