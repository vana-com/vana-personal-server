import logging
from typing import Optional

from domain.entities import PermissionData
from web3 import AsyncWeb3

from .abi import get_abi
from .chain import Chain, get_data_permissions_address

logger = logging.getLogger(__name__)


class DataPermissions:
    def __init__(self, chain: Chain, web3: AsyncWeb3):
        self.chain = chain
        self.web3 = web3

        self.data_permissions_address = get_data_permissions_address(chain.chain_id)
        self.data_permissions_abi = get_abi("DataPermissions")

        self.contract = self.web3.eth.contract(
            address=self.data_permissions_address, abi=self.data_permissions_abi
        )

    async def fetch_permission_from_blockchain(
        self, permission_id: int
    ) -> Optional[PermissionData]:
        """Fetch permission data from the PermissionRegistry contract"""
        try:
            # AsyncWeb3 connection check would need to be awaited if available
            # For now, we'll proceed with the contract call

            # Call the permissions function
            logger.info(f"Fetching permission {permission_id} from blockchain")
            permission_data = await self.contract.functions.permissions(permission_id).call()

            result = PermissionData(
                id=permission_data[0],
                grantor=permission_data[1],
                nonce=permission_data[2],
                grant=permission_data[3],
                signature=permission_data[4],
                is_active=permission_data[5],
                file_ids=permission_data[6],
            )

            # Debug: logger.info the parsed permission data
            logger.info(f"Parsed permission data: {result}")

            return result

        except Exception as e:
            logger.error(
                f"Failed to fetch permission {permission_id} from blockchain: {e}"
            )
            return None
