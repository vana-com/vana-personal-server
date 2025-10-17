# Vana Personal-Server API

[![semantic-release: conventionalcommits](https://img.shields.io/badge/semantic--release-conventionalcommits-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
[![Release](https://github.com/vana-com/vana-personal-server/actions/workflows/semantic-release.yml/badge.svg)](https://github.com/vana-com/vana-personal-server/actions/workflows/semantic-release.yml)

⚠️ **UNDER HEAVY DEVELOPMENT** ⚠️  
This project is in active development and may contain security vulnerabilities or breaking changes. 
Use at your own risk in production environments.

A user-scoped compute service that executes permissioned operations on private data. 
This implementation provides secure compute capabilities with blockchain-based data permissions, 
integrating with various compute providers and supporting encrypted data processing.

## Features

- **Secure Compute**: Execute operations on private data with cryptographic guarantees
- **Blockchain Integration**: Data permissions managed through smart contracts
- **Multiple Compute Providers**: Support for Replicate and other compute services
- **AI Agents (Experimental)**: Qwen and Gemini agent providers for agentic workflows
- **Encrypted Data Processing**: Handle encrypted files with proper decryption
- **Identity Management**: Derive server identities from user addresses
- **IPFS Integration**: Fetch data grants from IPFS
- **Robust Error Handling**: Comprehensive error handling and retry mechanisms

## Quick Start

### Local Development

1. **Install dependencies using Poetry:**
```bash
poetry install
```

2. **Set up environment variables:**
```bash
export REPLICATE_API_TOKEN=your_token_here
export WALLET_MNEMONIC=your_mnemonic_here
export CHAIN_ID=your_chain_id_here
export MNEMONIC_LANGUAGE=english  # optional, defaults to english
```

3. **Run the development server:**
```bash
poetry run python app.py
```

Or with uvicorn directly:
```bash
poetry run uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at `http://localhost:8000` with automatic OpenAPI docs at `http://localhost:8000/docs`.

### Docker (Quick Start)

**Simplest way - use pre-built image:**
```bash
# 1. Create .env file with your secrets
cat > .env << EOF
REPLICATE_API_TOKEN=your_token_here
WALLET_MNEMONIC=your_mnemonic_here
CHAIN_ID=your_chain_id_here
EOF

# 2. Download docker-compose.yml
curl -O https://raw.githubusercontent.com/vana-com/vana-personal-server/release-automation/docker-compose.yml

# 3. Start the server
docker-compose up -d
```

The server will be available at `http://localhost:8080/docs`

## API Reference

### Endpoints

- `POST /api/v1/operations` - Start a compute operation
- `GET /api/v1/operations/{id}` - Get operation status and results
- `POST /api/v1/operations/cancel` - Cancel a running operation
- `GET /api/v1/identity` - Get server identity for a user address

### Authentication

Operations require valid blockchain-based permissions. The server validates data access rights through smart contract interactions before executing compute operations.

## Project Structure

```
vana-personal-server/
├── app.py                    # Main FastAPI application entry point
├── settings.py               # Application settings and environment configuration
├── dependencies.py           # Dependency injection and shared dependencies
├── api/                      # FastAPI routers and API endpoints
│   ├── operations.py         # Operation management endpoints
│   ├── identity.py          # Identity derivation endpoints
│   └── schemas.py           # API request/response schemas
├── services/                 # Business logic services
│   ├── operations.py        # Operation orchestration
│   └── identity.py          # Identity derivation service
├── compute/                  # Compute provider integrations
│   ├── base.py              # Abstract compute interface
│   ├── replicate.py         # Replicate API integration
│   ├── qwen_agent.py        # Qwen agent provider (experimental)
│   └── gemini_agent.py      # Gemini agent provider (experimental)
├── onchain/                  # Blockchain integration
│   ├── chain.py             # Blockchain connection management
│   ├── data_registry.py     # Data registry contract interactions
│   ├── data_permissions.py  # Permission checking logic
│   └── abi.py               # Contract ABI definitions
├── grants/                   # Data permission grants
│   ├── fetch.py             # Grant retrieval logic
│   ├── validate.py          # Grant validation
│   └── schema/              # Grant schema definitions
├── files/                    # File handling utilities
│   ├── download.py          # File download functionality
│   └── decrypt.py           # File decryption utilities
├── domain/                   # Domain entities and business logic
│   ├── entities.py          # Domain entities
│   ├── value_objects.py     # Value objects
│   └── exceptions.py        # Custom exceptions
├── utils/                    # Utility functions
│   ├── derive_ethereum_keys.py # Ethereum key derivation
│   └── ipfs.py              # IPFS integration utilities
├── llm/                      # Large Language Model integration
│   └── llm.py               # LLM service implementation
├── tests/                    # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── Dockerfile               # Docker container configuration
├── pyproject.toml           # Poetry dependencies and project configuration
└── openapi.yaml             # OpenAPI specification
```

## Development

### Testing

Run the test suite:
```bash
poetry run pytest
```

Run specific tests:
```bash
poetry run pytest tests/unit/
poetry run pytest tests/integration/
```

### Code Quality

This project uses Poetry for dependency management and follows Python best practices. The codebase is organized using clean architecture principles with clear separation between API, business logic, and infrastructure layers.

### Environment Variables

**Mandatory environment variables:**

- `REPLICATE_API_TOKEN` - Replicate API token for LLM inference
- `WALLET_MNEMONIC` - Wallet mnemonic to derive server key pair
- `CHAIN_ID` - Blockchain chain ID to use correct RPC endpoint and smart contract addresses

**Optional environment variables:**

- `MNEMONIC_LANGUAGE` - Language for mnemonic (optional, defaults to 'english')

### Security Considerations

⚠️ **Important Security Notes:**
- This project is under active development and may contain security vulnerabilities
- Never commit sensitive environment variables to version control
- Use secure methods to manage your wallet mnemonic in production
- Review all permissions and data access patterns before deployment
- Monitor for suspicious activity and implement appropriate logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is part of the Vana ecosystem. Please refer to the license file for details.