# Personal Server Identity

Deterministic identity server for personal data servers based on user identity.
Uses BIP44 standard for deterministic address derivation, reusing the core logic from `crypto_service.py`.

## Purpose

This server provides deterministic personal server identity derivation. Given a user's Ethereum address,
it derives a unique personal server address using BIP44 derivation from a master mnemonic. The same user address 
will always produce the same personal server address, which can be stored in smart contracts for identity management.

## API Endpoint

**Model**: `vana-com/identity-server`

### Input
- `user_address`: User's Ethereum address (e.g., "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4")

### Output
```json
{
  "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4",
  "derived_address": "0x5B926696fE0230bbB69e42d2dBCf80671184e526"
}
```

## Implementation

The server reuses the core BIP44 key derivation logic from the existing `crypto_service.py`,
but in a simplified form that only includes the address derivation functionality without the complex
encryption/decryption operations and dependencies.

### Identity Derivation Process

1. **Index Generation**: User address is hashed to produce a deterministic index
2. **BIP44 Derivation**: Uses the master mnemonic to derive keys at path `m/44'/60'/0'/0/{index}`
3. **Identity Output**: Returns only the derived personal server address for smart contract storage

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
cog push r8.im/vana-com/identity-server

# Test with curl
curl -X POST "https://api.replicate.com/v1/predictions" \
  -H "Authorization: Token r8_..." \
  -H "Content-Type: application/json" \
  -d '{
    "version": "vana-com/identity-server:latest",
    "input": {
      "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    }
  }'
```

## Security

- The master mnemonic must be kept secure and never exposed
- Each user gets a unique personal server identity derived deterministically
- The same user address will always produce the same personal server identity
- Identities are derived using industry-standard BIP44 specification
- No private keys are exposed in the API response

## Features

- ✅ **Deterministic**: Same user address always produces the same personal server identity
- ✅ **BIP44 Standard**: Uses industry-standard identity derivation
- ✅ **Secure**: Personal server identities derived from VANA_MNEMONIC
- ✅ **Simple API**: Just provide user address, get derived personal server identity for smart contract storage

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
   cog push r8.im/vana-com/identity-server
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
  "derived_address": "0x5B926696fE0230bbB69e42d2dBCf80671184e526"
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
    "version": "vana-com/identity-server:latest",
    "input": {
      "user_address": "0xf0ebD65BEaDacD191dc96D8EC69bbA4ABCf621D4"
    }
  }'
```

## Identity Derivation Details

### Deterministic Index Generation
The user address is converted to a deterministic index using:
```python
digest = hashlib.sha256(user_address.lower().encode()).digest()
index = int.from_bytes(digest[:4], 'big') % (2**31)
```

### BIP44 Derivation Path
Personal server identities are derived using the path: `m/44'/60'/0'/0/{index}`

- `44'`: BIP44 purpose
- `60'`: Ethereum coin type
- `0'`: Account 0
- `0`: External chain
- `{index}`: Deterministic index from user address

## Security Notes

- The model requires `VANA_MNEMONIC` to be set securely
- Personal server identities are derived deterministically - same input always produces same output
- No private keys are exposed in the API response
- The model only derives identities, it doesn't store them

## Use Cases

- **Smart Contract Integration**: Store personal server identities in smart contracts
- **Personal Data Sovereignty**: Each user gets their own deterministic personal server identity
- **Identity Management**: Consistent personal server identity derivation across services
- **Multi-tenant Systems**: Isolated personal server identities per user
- **Data Portability**: Deterministic identity for personal data servers 