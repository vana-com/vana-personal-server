import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)
import json

import web3
from entities import FileMetadata, PermissionData, PersonalServerRequest
from eth_account.messages import encode_defunct
from files import decrypt_user_data, decrypt_with_wallet_private_key, download_file
from grants.fetch_grant import fetch_grant
from llm.llm import Llm
from onchain.data_permissions import DataPermissions
from onchain.data_registry import DataRegistry
from utils.identity_server import IdentityServer
from grants.grant_models import GrantFile

LLM_INFERENCE_OPERATION = "llm_inference"
PROMPT_DATA_SEPARATOR = ("-----"*80 + "\n")

class Server:
    def __init__(self, llm: Llm, chain):
        self.llm = llm
        self.chain = chain
        self.web3 = web3.Web3(web3.HTTPProvider(chain.url))
        self.data_registry = DataRegistry(chain, self.web3)
        self.data_permissions = DataPermissions(chain, self.web3)
        self.identity_server = IdentityServer()

    def execute(self, request_json: str, signature: str):
        request = PersonalServerRequest(**json.loads(request_json))

        if request.permission_id <= 0:
            raise ValueError("Valid permission ID is required")

        app_address = self.recover_app_address(request_json, signature)
        logger.info(f"Recovered app address: {app_address}")
        
        permission = self.data_permissions.fetch_permission_from_blockchain(request.permission_id)
        if not permission:
            raise ValueError(f"Permission {request.permission_id} not found on blockchain")
        
        if not permission.file_ids or len(permission.file_ids) == 0:
            raise ValueError("No file IDs found in permission")
        
        grant_file = fetch_grant(permission.grant)
        if not grant_file:
            raise ValueError(f"Grant data not found or invalid at {permission.grant}")
        
        if grant_file.operation != LLM_INFERENCE_OPERATION:
            raise ValueError("Only LLM inference is supported")
        
        if grant_file.grantee != app_address:
            raise ValueError("App address does not match the app address in the access permissions")

        logger.info(f"App {app_address} has access to execute the request: {request}")

        server_private_key, server_address = self._derive_user_server_keys(permission.grantor)

        logger.info(f"Derived server address: {server_address}")

        files_metadata = self._fetch_files_metadata(permission.file_ids, server_address)
        files_content = self._decrypt_files_content(files_metadata, server_private_key)
        prompt = self._build_prompt(grant_file, files_content)
        return self.llm.run(prompt)
    
    def recover_app_address(self, request_json: str, signature: str):
        message = encode_defunct(text=request_json)
        return self.web3.eth.account.recover_message(message, signature=signature)
    
    def _derive_user_server_keys(self, grantor: str) -> tuple[str, str]:
        user_server_keys = self.identity_server.derive_user_server_address(grantor)
        return user_server_keys["private_key"], user_server_keys["address"]
    
    def _fetch_files_metadata(self, file_ids: list[int], server_address: str) -> list[FileMetadata]:
        files_metadata = []
        for file_id in file_ids:
            file_metadata = self.data_registry.fetch_file_metadata(file_id, server_address)

            if not file_metadata:
                raise ValueError(f"File {file_id} not found in the data registry")

            files_metadata.append(file_metadata)
        
        return files_metadata
    
    def _decrypt_files_content(self, files_metadata: list[FileMetadata], server_private_key: str) -> list[str]:
        files_content = []
        for file_metadata in files_metadata:
            encrypted_file_content = download_file(file_metadata.public_url)
            logger.info(f"Fetched file content from {file_metadata.public_url}")
            decrypted_encryption_key = decrypt_with_wallet_private_key(file_metadata.encrypted_key, server_private_key)
            decrypted_file_content_bytes = decrypt_user_data(encrypted_file_content, decrypted_encryption_key)
            decrypted_file_content = decrypted_file_content_bytes.decode('utf-8')
            files_content.append(decrypted_file_content)

        return files_content

    def _build_prompt(self, grant_file: GrantFile, files_content: list[str]):
        prompt_template = grant_file.parameters.get("prompt", "")
        if not prompt_template:
            raise ValueError("Prompt template is required in permission parameters")
        
        concatenated_data = "\n" + PROMPT_DATA_SEPARATOR.join(files_content) + "\n" + PROMPT_DATA_SEPARATOR
        return prompt_template.replace("{{data}}", concatenated_data)
