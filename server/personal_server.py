import logging
import os

logger = logging.getLogger(__name__)
import json

import web3
from eth_account.messages import encode_defunct
from ecies import decrypt as ecies_decrypt

from entities import AccessPermissionsResponse, PersonalServerRequest
from onchain.data_registry import DataRegistry
from onchain.access_permissions import AccessPermissions
from llm import Llm
from files import download_file, decrypt
from identity_server import IdentityServer

LLM_INFERENCE_OPERATION = "llm_inference"
PROMPT_DATA_SEPARATOR = ("-----"*80 + "\n")

class PersonalServer:
    def __init__(self, llm: Llm):
        self.llm = llm
        self.data_registry = DataRegistry()
        self.web3 = web3.Web3()
        self.access_permissions = AccessPermissions()
        self.identity_server = IdentityServer()

    def execute(self, request_json: str, signature: str):
        request = PersonalServerRequest(**json.loads(request_json))

        if request.permission_id <= 0:
            raise ValueError("Valid permission ID is required")

        app_address = self.recover_app_address(request_json, signature)
        print(f"App address: {app_address}")
        
        # Fetch access permissions from blockchain using permission_id
        access_permissions = self.fetch_access_permissions(app_address, request)
        print(f"Access permissions: {access_permissions}")

        if access_permissions.operation != LLM_INFERENCE_OPERATION:
            raise ValueError("Only LLM inference is supported")

        if not access_permissions.file_ids or len(access_permissions.file_ids) == 0:
            raise ValueError("No file IDs found in permission")

        logger.info(f"App {app_address} has access to execute the request: {request}")

        # Derive the personal server private key based on user address
        user_server_keys = self.identity_server.derive_user_server_address(request.user_address)
        personal_server_private_key = user_server_keys["private_key"]
        personal_server_address = user_server_keys["address"]

        files_metadata = []
        for file_id in access_permissions.file_ids:
            file_metadata = self.data_registry.fetch_file_metadata(file_id, personal_server_address)

            if not file_metadata:
                raise ValueError(f"File {file_id} not found in the data registry")

            if not file_metadata.encrypted_key:
                raise ValueError(f"Encryption key not found for file {file_id}. Most likely {personal_server_address} is not permitted to decryot the file.")

            files_metadata.append(file_metadata)

        files_content = []
        for file_metadata in files_metadata:
            encrypted_file_content = download_file(file_metadata.public_url)
            print(f"Fetched file content from {file_metadata.public_url}")
            # Decrypt file_metadata.encrypted_key with personal_server_private_key using ECIES
            encrypted_key_bytes = bytes.fromhex(file_metadata.encrypted_key)
            decrypted_key = ecies_decrypt(personal_server_private_key, encrypted_key_bytes)
            print(f"Decrypted key: {decrypted_key}")

            # Decrypt actual file content with the decrypted key
            decrypted_key_hex = decrypted_key.hex()
            decrypted_file_content = decrypt(decrypted_key_hex, encrypted_file_content)
            print(f"Decrypted file content: {decrypted_file_content}")
            files_content.append(decrypted_file_content)

        # Get the prompt template from access permissions parameters
        prompt_template = access_permissions.parameters.get("prompt", "")
        if not prompt_template:
            raise ValueError("Prompt template is required in permission parameters")
        
        prompt = self.build_prompt(prompt_template, files_content)
        return self.llm.run(prompt)
    
    def recover_app_address(self, request_json: str, signature: str):
        message = encode_defunct(text=request_json)
        return self.web3.eth.account.recover_message(message, signature=signature)
    
    def fetch_access_permissions(self, app_address: str, request: PersonalServerRequest) -> AccessPermissionsResponse:
        return self.access_permissions.fetch_access_permissions(app_address, request)
    
    def build_prompt(self, prompt_template: str, files_content: list[str]):
        concatenated_data = "\n" + PROMPT_DATA_SEPARATOR.join(files_content) + "\n" + PROMPT_DATA_SEPARATOR
        return prompt_template.replace("{{data}}", concatenated_data)
