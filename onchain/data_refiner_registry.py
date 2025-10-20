"""
Data Refiner Registry contract interface.

Provides schema metadata lookup for files in the data registry.
"""
import logging
from typing import Optional
from web3 import AsyncWeb3
from .chain import Chain, get_contract_address
from .abi import get_abi

logger = logging.getLogger(__name__)


class DataRefinerRegistry:
    """Interface to DataRefinerRegistry contract for schema lookups."""

    def __init__(self, chain: Chain, web3: AsyncWeb3):
        self.web3 = web3
        self.registry_address = get_contract_address(chain.chain_id, "DataRefinerRegistry")
        self.registry_abi = get_abi("DataRefinerRegistry")
        self.contract = self.web3.eth.contract(
            address=self.registry_address,
            abi=self.registry_abi
        )
        logger.info(f"[BLOCKCHAIN] Initialized DataRefinerRegistry at {self.registry_address}")

    async def get_schema(self, schema_id: int) -> Optional[dict]:
        """
        Fetch schema metadata from the registry.

        Args:
            schema_id: Schema identifier from file metadata

        Returns:
            Dictionary with schema metadata:
                - name: Schema name (e.g., "Audata Schema")
                - dialect: Data format (e.g., "sqlite", "json")
                - definitionUrl: IPFS URL with schema definition

            Returns None if schema not found or error occurs.
        """
        try:
            logger.info(f"[BLOCKCHAIN] Fetching schema {schema_id} from DataRefinerRegistry")

            schema_data = await self.contract.functions.schemas(schema_id).call()

            # Parse tuple response
            schema_name = schema_data[0]
            schema_dialect = schema_data[1]
            schema_definition_url = schema_data[2]

            logger.info(
                f"[BLOCKCHAIN] Schema {schema_id} retrieved: "
                f"name={schema_name}, dialect={schema_dialect}"
            )

            return {
                "name": schema_name,
                "dialect": schema_dialect,
                "definitionUrl": schema_definition_url
            }

        except Exception as e:
            logger.error(
                f"[BLOCKCHAIN] Failed to fetch schema {schema_id} from registry: {e}"
            )
            logger.error(f"[BLOCKCHAIN] Registry address: {self.registry_address}")
            return None
