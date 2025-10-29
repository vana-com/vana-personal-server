import logging
from typing import Optional
from web3 import AsyncWeb3
from domain.entities import FileMetadata
from .chain import Chain, get_data_registry_address
from .abi import get_abi
from .data_refiner_registry import DataRefinerRegistry

logger = logging.getLogger(__name__)


class DataRegistry:
    def __init__(self, chain: Chain, web3: AsyncWeb3):
        self.web3 = web3
        self.chain = chain
        self.data_registry_address = get_data_registry_address(chain.chain_id)
        self.data_registry_abi = get_abi("DataRegistry")
        self.contract = self.web3.eth.contract(
            address=self.data_registry_address, abi=self.data_registry_abi
        )
        # Initialize DataRefinerRegistry for schema lookups
        self.refiner_registry = DataRefinerRegistry(chain, web3)

    async def fetch_file_metadata(
        self, file_id: int, personal_server_address: str
    ) -> Optional[FileMetadata]:
        """Fetch file metadata from the DataRegistry contract"""
        try:
            # AsyncWeb3 connection check would need to be awaited if available
            # For now, we'll proceed with the contract call

            # Call the files function
            logger.info(f"[BLOCKCHAIN] Fetching file metadata for file {file_id} from DataRegistry contract")
            logger.info(f"[BLOCKCHAIN] Contract address: {self.data_registry_address}, Server: {personal_server_address}")
            
            file_data = await self.contract.functions.files(file_id).call()
            logger.info(f"[BLOCKCHAIN] Contract call successful for file {file_id}")

            # Log the raw file data
            logger.info(f"[BLOCKCHAIN] Raw file data for file {file_id}: {file_data}")

            file_id_from_contract = file_data[0]
            owner_address = file_data[1]
            public_url = file_data[2]
            # file_data[3] is schemaId
            schema_id = file_data[3] if len(file_data) > 3 else None
            # file_data[4] is addedAtBlock (not currently used)

            # Log the parsed file data
            logger.info(
                f"[BLOCKCHAIN] Parsed file data: id={file_id_from_contract}, owner={owner_address}, "
                f"url={public_url}, schemaId={schema_id}"
            )

            # Get the encrypted key using the personal server address (not the file owner)
            logger.info(f"[BLOCKCHAIN] Fetching encrypted key for file {file_id} with server address {personal_server_address}")
            encrypted_key = await self._get_encrypted_key_for_file(
                file_id, personal_server_address
            )
            logger.info(f"[BLOCKCHAIN] Encrypted key fetched successfully for file {file_id}")

            # Resolve schema metadata if schema_id is present
            schema_name = None
            schema_dialect = None
            if schema_id and schema_id > 0:
                logger.info(f"[BLOCKCHAIN] Resolving schema metadata for schemaId {schema_id}")
                schema_data = await self.refiner_registry.get_schema(schema_id)
                if schema_data:
                    schema_name = schema_data.get("name")
                    schema_dialect = schema_data.get("dialect")
                    logger.info(f"[BLOCKCHAIN] Schema resolved: {schema_name} ({schema_dialect})")
                else:
                    logger.warning(f"[BLOCKCHAIN] Failed to resolve schema {schema_id}")

            return FileMetadata(
                file_id=file_id_from_contract,
                owner_address=owner_address,
                public_url=public_url,
                encrypted_key=encrypted_key,
                schema_id=schema_id,
                schema_name=schema_name,
                schema_dialect=schema_dialect
            )

        except Exception as e:
            logger.error(f"[BLOCKCHAIN] Failed to fetch file {file_id} from blockchain: {e}")
            logger.error(f"[BLOCKCHAIN] Contract address: {self.data_registry_address}, Server: {personal_server_address}")
            logger.error(f"[BLOCKCHAIN] Exception type: {type(e).__name__}")
            return None

    async def _get_encrypted_key_for_file(
        self, file_id: int, personal_server_address: str
    ) -> str:
        """Get the encrypted key for a file using the filePermissions function."""
        try:
            # AsyncWeb3 connection check would need to be awaited if available
            # For now, we'll proceed with the contract call

            # Call the filePermissions function to get the encrypted key
            logger.info(f"[BLOCKCHAIN] Calling filePermissions contract function for file {file_id}, server {personal_server_address}")
            encrypted_key = await self.contract.functions.filePermissions(
                file_id, personal_server_address
            ).call()
            logger.info(f"[BLOCKCHAIN] filePermissions contract call successful for file {file_id}")

            if encrypted_key:
                logger.info(
                    f"[BLOCKCHAIN] Successfully retrieved encrypted key for file {file_id} and server {personal_server_address}"
                )
                return encrypted_key
            else:
                logger.error(f"[BLOCKCHAIN] No encrypted key found for file {file_id} and server {personal_server_address}")
                raise ValueError(f"No encrypted key found for file {file_id} and server {personal_server_address}")

        except Exception as e:
            logger.error(
                f"[BLOCKCHAIN] Failed to fetch encrypted key for file {file_id} and server {personal_server_address}: {e}"
            )
            logger.error(f"[BLOCKCHAIN] Contract address: {self.data_registry_address}")
            logger.error(f"[BLOCKCHAIN] Exception type: {type(e).__name__}")
            raise
