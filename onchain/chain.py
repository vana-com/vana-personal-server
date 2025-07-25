"""
Chain information for the data portability personal server.
Single source of truth for all chain IDs and URLs.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Chain:
    chain_id: int
    url: str


# Chain definitions
MOKSHA = Chain(chain_id=14800, url="https://rpc.moksha.vana.org")
MAINNET = Chain(chain_id=1480, url="https://rpc.vana.org")

# Chain registry
CHAINS = {
    MOKSHA.chain_id: MOKSHA,
    MAINNET.chain_id: MAINNET,
}

# Contract addresses
CONTRACTS = {
    "DataPermissions": {
        "addresses": {
            MOKSHA.chain_id: "0xD54523048AdD05b4d734aFaE7C68324Ebb7373eF",
            MAINNET.chain_id: "0xD54523048AdD05b4d734aFaE7C68324Ebb7373eF",
        },
    },
    "DataRegistry": {
        "addresses": {
            MOKSHA.chain_id: "0x8C8788f98385F6ba1adD4234e551ABba0f82Cb7C",
            MAINNET.chain_id: "0x8C8788f98385F6ba1adD4234e551ABba0f82Cb7C",
        },
    },
    "DataPortabilityGrantees": {
        "addresses": {
            MOKSHA.chain_id: "0x8325C0A0948483EdA023A1A2Fd895e62C5131234",
            MAINNET.chain_id: "0x8325C0A0948483EdA023A1A2Fd895e62C5131234",
        },
    },
}


def get_chain(chain_id: int) -> Chain:
    """Get Chain object for a specific chain ID."""
    if chain_id not in CHAINS:
        raise ValueError(f"Chain ID {chain_id} not supported")
    return CHAINS[chain_id]


def get_chain_url(chain_id: int) -> str:
    """Get RPC URL for a specific chain ID."""
    return get_chain(chain_id).url


def get_contract_address(chain_id: int, contract_name: str) -> str:
    """Get contract address for a specific chain and contract."""
    if contract_name not in CONTRACTS:
        raise ValueError(f"Contract {contract_name} not found")

    if chain_id not in CONTRACTS[contract_name]["addresses"]:
        raise ValueError(f"Chain ID {chain_id} not supported for {contract_name}")

    return CONTRACTS[contract_name]["addresses"][chain_id]


def get_data_permissions_address(chain_id: int = MOKSHA.chain_id) -> str:
    """Get DataPermissions contract address."""
    return get_contract_address(chain_id, "DataPermissions")


def get_data_registry_address(chain_id: int = MOKSHA.chain_id) -> str:
    """Get DataRegistry contract address."""
    return get_contract_address(chain_id, "DataRegistry")


def get_data_portability_grantees_address(chain_id: int = MOKSHA.chain_id) -> str:
    """Get DataPortabilityGrantees contract address."""
    return get_contract_address(chain_id, "DataPortabilityGrantees")
