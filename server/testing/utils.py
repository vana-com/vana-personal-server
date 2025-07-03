from eth_keys import keys

def private_to_public(private_key: str) -> str:
    private_key_bytes = bytes.fromhex(private_key)
    eth_key = keys.PrivateKey(private_key_bytes)
    return eth_key.public_key.to_hex()