"""
Contract ABIs for the data portability personal server.
Single source of truth for all contract ABIs.
"""

# DataPermissions ABI
DATA_PERMISSIONS_ABI = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "permissionId",
                "type": "uint256"
            }
        ],
        "name": "permissions",
        "outputs": [
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "id",
                        "type": "uint256"
                    },
                    {
                        "internalType": "address",
                        "name": "grantor",
                        "type": "address"
                    },
                    {
                        "internalType": "uint256",
                        "name": "nonce",
                        "type": "uint256"
                    },
                    {
                        "internalType": "string",
                        "name": "grant",
                        "type": "string"
                    },
                    {
                        "internalType": "bytes",
                        "name": "signature",
                        "type": "bytes"
                    },
                    {
                        "internalType": "bool",
                        "name": "isActive",
                        "type": "bool"
                    },
                    {
                        "internalType": "uint256[]",
                        "name": "fileIds",
                        "type": "uint256[]"
                    }
                ],
                "internalType": "struct IDataPermissions.PermissionInfo",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# DataRegistry ABI
DATA_REGISTRY_ABI = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "fileId",
                "type": "uint256"
            }
        ],
        "name": "files",
        "outputs": [
            {
                "components": [
                    {
                        "internalType": "uint256",
                        "name": "id",
                        "type": "uint256"
                    },
                    {
                        "internalType": "address",
                        "name": "ownerAddress",
                        "type": "address"
                    },
                    {
                        "internalType": "string",
                        "name": "url",
                        "type": "string"
                    },
                    {
                        "internalType": "uint256",
                        "name": "addedAtBlock",
                        "type": "uint256"
                    }
                ],
                "internalType": "struct IDataRegistry.FileResponse",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "fileId",
                "type": "uint256"
            },
            {
                "internalType": "address",
                "name": "account",
                "type": "address"
            }
        ],
        "name": "filePermissions",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
]

def get_abi(contract_name: str) -> list:
    """Get ABI for a specific contract."""
    abi_map = {
        "DataPermissions": DATA_PERMISSIONS_ABI,
        "DataRegistry": DATA_REGISTRY_ABI,
    }
    
    if contract_name not in abi_map:
        raise ValueError(f"ABI not found for contract {contract_name}")
    
    return abi_map[contract_name] 