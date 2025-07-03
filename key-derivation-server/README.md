# Key Derivation Server

Deterministic key derivation server for user servers based on user identity.
Uses BIP44 standard for deterministic key derivation, reusing the core logic from `crypto_service.py`.

## Purpose

This server provides deterministic key derivation for user servers. Given a user's Ethereum address,
it derives a unique set of cryptographic keys (private key, public key, address) using BIP44 derivation
from a master mnemonic. The same user address will always produce the same keys.

## API Endpoint

**Model**: `vana-com/key-derivation-server`

### Input
- `user_address`: User's Ethereum address (e.g., "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4")

### Output
```json
{
  "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
  "derivation_index": 123456789,
  "private_key_hex": "0x...",
  "public_key_hex": "0x...",
  "derived_address": "0x...",
  "derivation_path": "m/44'/60'/0'/0/123456789",
  "mnemonic_language": "english"
}
```

## Implementation

The server reuses the core BIP44 key derivation logic from the existing `crypto_service.py`,
but in a simplified form that only includes the key derivation functionality without the complex
encryption/decryption operations and dependencies.

### Key Derivation Process

1. **Index Generation**: User address is hashed to produce a deterministic index
2. **BIP44 Derivation**: Uses the master mnemonic to derive keys at path `m/44'/60'/0'/0/{index}`
3. **Key Output**: Returns private key, public key, and derived address

## Environment Variables

- `VANA_MNEMONIC`: Master mnemonic phrase for key derivation
- `MNEMONIC_LANGUAGE`: Language of the mnemonic (default: "english")

## Testing

### Local Testing
```bash
# Set environment variables
export VANA_MNEMONIC="your twelve word mnemonic phrase here"
export MNEMONIC_LANGUAGE="english"

# Run test
python test_key_derivation.py
```

### Deploy and Test
```bash
# Deploy to Replicate
cog push r8.im/vana-com/key-derivation-server

# Test with curl
curl -X POST "https://api.replicate.com/v1/predictions" \
  -H "Authorization: Token r8_..." \
  -H "Content-Type: application/json" \
  -d '{
    "version": "vana-com/key-derivation-server:latest",
    "input": {
      "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    }
  }'
```

## Security

- The master mnemonic must be kept secure and never exposed
- Each user gets a unique set of keys derived deterministically
- The same user address will always produce the same keys
- Keys are derived using industry-standard BIP44 specification

## Features

- ✅ **Deterministic**: Same user address always produces the same keys
- ✅ **BIP44 Standard**: Uses industry-standard key derivation
- ✅ **Secure**: Keys derived from VANA_MNEMONIC
- ✅ **Simple API**: Just provide user address, get derived keys

## Deploy to Replicate

### Prerequisites
- Replicate account and API token
- Python 3.8+ installed locally

### Steps

1. **Install Replicate CLI**
   ```bash
   pip install cog
   ```

2. **Login to Replicate**
   ```bash
   cog login
   ```

3. **Deploy the model**
   ```bash
   cog push r8.im/vana-com/key-derivation-server
   ```

### Environment Variables
Make sure to set the following environment variables in your Replicate deployment:
- `VANA_MNEMONIC`: Your BIP39 mnemonic phrase
- `MNEMONIC_LANGUAGE`: Language of the mnemonic (default: "english")

## API Usage

### Input
```json
{
  "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
}
```

### Output
```json
{
  "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
  "derivation_index": 123456789,
  "private_key_hex": "0x1234567890abcdef...",
  "public_key_hex": "0xabcdef1234567890...",
  "derived_address": "0x9876543210fedcba...",
  "derivation_path": "m/44'/60'/0'/0/123456789",
  "mnemonic_language": "english"
}
```

## Testing

### Python Client
```bash
cd benchmarks && python key_derivation_client.py
```

### Curl Example
```bash
curl -X POST "https://api.replicate.com/v1/predictions" \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "vana-com/key-derivation-server:latest",
    "input": {
      "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    }
  }'
```

## Key Derivation Details

### Deterministic Index Generation
The user address is converted to a deterministic index using:
```python
digest = hashlib.sha256(user_address.lower().encode()).digest()
index = int.from_bytes(digest[:4], 'big') % (2**31)
```

### BIP44 Derivation Path
Keys are derived using the path: `m/44'/60'/0'/0/{index}`

- `44'`: BIP44 purpose
- `60'`: Ethereum coin type
- `0'`: Account 0
- `0`: External chain
- `{index}`: Deterministic index from user address

## Security Notes

- The model requires `VANA_MNEMONIC` to be set securely
- Keys are derived deterministically - same input always produces same output
- Private keys should be handled securely in production environments
- The model only derives keys, it doesn't store them

## Use Cases

- **Personal Server Setup**: Derive keys for user's personal data server
- **Identity Management**: Consistent key derivation across services
- **Backup Recovery**: Deterministic key recovery for user data
- **Multi-tenant Systems**: Isolated keys per user 