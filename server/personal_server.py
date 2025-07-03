import logging

logger = logging.getLogger(__name__)
import json

import web3
from eth_account.messages import encode_defunct

from entities import AccessPermissionsResponse, PersonalServerRequest
from onchain.data_registry import DataRegistry
from onchain.access_permissions import AccessPermissions
from llm import Llm
from files import download_file, decrypt

LLM_INFERENCE_OPERATION = "llm_inference"
PROMPT_DATA_SEPARATOR = ("-----"*80 + "\n")

class PersonalServer:
    def __init__(self, llm: Llm, web3=None):
        self.llm = llm
        self.data_registry = DataRegistry()
        self.web3 = web3
        self.access_permissions = AccessPermissions()

    def execute(self, request_json: str, signature: str):
        request = PersonalServerRequest(**json.loads(request_json))

        if request.operation != LLM_INFERENCE_OPERATION:
            raise ValueError("Only LLM inference is supported")
        
        if request.file_ids is None or len(request.file_ids) == 0:
            raise ValueError("File IDs are required")

        app_address = self.recover_app_address(request_json, signature)
        access_permissions = self.fetch_access_permissions(app_address, request)
        print(f"Access permissions: {access_permissions}")

        if request.operation != access_permissions.operation:
            raise ValueError("App does not have access to the operation")

        if request.parameters != access_permissions.parameters:
            raise ValueError("App does not have access to the parameters")

        if set(request.file_ids) != set(access_permissions.file_ids):
            raise ValueError("App does not have access to the files")

        logger.info(f"App {app_address} has access to execute the request: {request}")

        files_metadata = []
        for file_id in request.file_ids:
            file_metadata = self.data_registry.fetch_file_metadata(file_id)
            print(f"File metadata for file {file_id}: {file_metadata}")
            if not file_metadata:
                raise ValueError(f"File {file_id} not found in the data registry")

            files_metadata.append(file_metadata)

        files_content = []
        for file_metadata in files_metadata:
            encrypted_file_content = download_file(file_metadata.public_url)
            print(f"Fetched file content from {file_metadata.public_url}. Encrypted content: \n{encrypted_file_content}")
            decrypted_file_content = decrypt(file_metadata.encryption_key, encrypted_file_content)
            print(f"Decrypted file content: {decrypted_file_content}")
            files_content.append(decrypted_file_content)

        # Get the prompt template from request parameters
        prompt_template = request.parameters.get("prompt", "")
        if not prompt_template:
            raise ValueError("Prompt template is required in parameters")
        
        prompt = self.build_prompt(prompt_template, files_content)
        return self.llm.run(prompt)
    
    def recover_app_address(self, request_json: str, signed_request: str):
        message = encode_defunct(text=request_json)
        return self.web3.eth.account.recover_message(message, signature=signed_request)
    
    def fetch_access_permissions(self, app_address: str, request: PersonalServerRequest) -> AccessPermissionsResponse:
        return self.access_permissions.fetch_access_permissions(app_address, request)
    
    def fetch_file_metadata(self, file_id: int):
        # TODO Handle missing files or permissions
        return self.data_registry.fetch_file_metadata(file_id)

    def build_prompt(self, prompt_template: str, files_content: list[str]):
        concatenated_data = "\n" + PROMPT_DATA_SEPARATOR.join(files_content) + "\n" + PROMPT_DATA_SEPARATOR
        return prompt_template.replace("{{data}}", concatenated_data)



