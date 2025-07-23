import logging
from typing import Optional
from web3 import AsyncWeb3
from domain.entities import FileMetadata
from .chain import Chain, get_data_registry_address
from .abi import get_abi

logger = logging.getLogger(__name__)


class DataRegistry:
    def __init__(self, chain: Chain, web3: AsyncWeb3):
        self.web3 = web3
        self.data_registry_address = get_data_registry_address(chain.chain_id)
        self.data_registry_abi = get_abi("DataRegistry")
        self.contract = self.web3.eth.contract(
            address=self.data_registry_address, abi=self.data_registry_abi
        )

    async def fetch_file_metadata(
        self, file_id: int, personal_server_address: str
    ) -> Optional[FileMetadata]:
        """Fetch file metadata from the DataRegistry contract"""
        try:
            # AsyncWeb3 connection check would need to be awaited if available
            # For now, we'll proceed with the contract call

            # Call the files function
            file_data = await self.contract.functions.files(file_id).call()

            # Debug: Print the raw file data
            logger.info(f"Raw file data for file {file_id}: {file_data}")

            file_id_from_contract = file_data[0]
            owner_address = file_data[1]
            public_url = file_data[2]

            # Debug: Print the parsed file data
            logger.info(
                f"Parsed file data: id={file_id_from_contract}, owner={owner_address}, url={public_url}"
            )

            # Get the encrypted key using the personal server address (not the file owner)
            encrypted_key = await self._get_encrypted_key_for_file(
                file_id, personal_server_address
            )

            return FileMetadata(
                file_id=file_id_from_contract,
                owner_address=owner_address,
                public_url=public_url,
                encrypted_key=encrypted_key,
            )

        except Exception as e:
            logger.error(f"Failed to fetch file {file_id} from blockchain: {e}")
            return None

    async def _get_encrypted_key_for_file(
        self, file_id: int, personal_server_address: str
    ) -> str:
        """Get the encrypted key for a file using the filePermissions function."""
        try:
            # AsyncWeb3 connection check would need to be awaited if available
            # For now, we'll proceed with the contract call

            # Call the filePermissions function to get the encrypted key
            encrypted_key = await self.contract.functions.filePermissions(
                file_id, personal_server_address
            ).call()

            if encrypted_key:
                logger.debug(
                    f"Successfully retrieved encrypted key for file {file_id} and server {personal_server_address}"
                )
                return encrypted_key
            else:
                raise ValueError(f"No encrypted key found for file {file_id} and server {personal_server_address}")

        except Exception as e:
            logger.error(
                f"Failed to fetch encrypted key for file {file_id} and server {personal_server_address}: {e}"
            )
            raise
