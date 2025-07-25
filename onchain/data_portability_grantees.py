"""
DataPortabilityGrantees contract interface for the personal server.
"""

import logging
from typing import Optional, Dict, Any
from web3 import AsyncWeb3

from .chain import Chain, get_data_portability_grantees_address
from .abi import get_abi

logger = logging.getLogger(__name__)


class DataPortabilityGrantees:
    """Interface for the DataPortabilityGrantees smart contract."""
    
    def __init__(self, chain: Chain, web3: AsyncWeb3):
        self.chain = chain
        self.web3 = web3
        
        self.contract_address = get_data_portability_grantees_address(chain.chain_id)
        self.contract_abi = get_abi("DataPortabilityGrantees")
        
        self.contract = self.web3.eth.contract(
            address=self.contract_address, abi=self.contract_abi
        )
    
    async def get_grantee_info(self, grantee_id: int) -> Optional[Dict[str, Any]]:
        """Fetch grantee info from the DataPortabilityGrantees contract.
        
        Args:
            grantee_id: The ID of the grantee to fetch
            
        Returns:
            Dict containing grantee information or None if not found
        """
        try:
            logger.info(f"[BLOCKCHAIN] Fetching info for granteeId {grantee_id}")
            logger.info(f"[BLOCKCHAIN] Contract address: {self.contract_address}, Chain: {self.chain.chain_id}")
            
            # Call the grantees function on the contract
            grantee_data = await self.contract.functions.grantees(grantee_id).call()
            
            # The contract returns a tuple: (owner, granteeAddress, publicKey, permissionIds)
            result = {
                "owner": grantee_data[0],
                "granteeAddress": grantee_data[1], 
                "publicKey": grantee_data[2],
                "permissionIds": grantee_data[3],
            }
            
            logger.info(f"[BLOCKCHAIN] Successfully fetched grantee info: owner={result['owner']}, address={result['granteeAddress']}")
            
            return result
            
        except Exception as e:
            logger.error(f"[BLOCKCHAIN] Failed to fetch info for granteeId {grantee_id}: {e}")
            logger.error(f"[BLOCKCHAIN] Contract address: {self.contract_address}, Chain: {self.chain.chain_id}")
            logger.error(f"[BLOCKCHAIN] Exception type: {type(e).__name__}")
            return None