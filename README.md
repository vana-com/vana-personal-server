# Vana Personal-Server API

⚠️ **UNDER HEAVY DEVELOPMENT** ⚠️  
This project is in active development and may contain security vulnerabilities or breaking changes. 
Use at your own risk in production environments.

A user-scoped compute service that executes permissioned operations on private data. 
This implementation provides secure compute capabilities with blockchain-based data permissions, 
integrating with various compute providers and supporting encrypted data processing.

## Features

- **Secure Compute**: Execute operations on private data with cryptographic guarantees
- **Blockchain Integration**: Data permissions managed through smart contracts
- **Multiple Compute Providers**: Support for Replicate, OpenAI, and local AI inference
- **Encrypted Data Processing**: Handle encrypted files with proper decryption
- **Identity Management**: Derive server identities from user addresses
- **IPFS Integration**: Fetch data grants from IPFS
- **Robust Error Handling**: Comprehensive error handling and retry mechanisms
- **Privacy-Preserving AI Pipeline**: Advanced privacy protection for AI processing
- **Differential Privacy**: Mathematical guarantees for data privacy
- **Secure Memory Management**: RAM cleanup to prevent data leaks
- **Local AI Inference**: Process data locally without external exposure

## Privacy Features

### **Privacy-Preserving AI Pipeline**
- **Document Classification**: Automatic categorization by type and risk level
- **Feature Extraction**: Safe statistical and semantic feature extraction
- **Differential Privacy**: Configurable epsilon values for privacy-accuracy trade-offs
- **Embedding Generation**: Vector representations with anonymization
- **Synthetic Data**: Artificial data preserving statistical properties
- **Privacy Budget Management**: Track and limit information disclosure
- **Secure Memory Cleanup**: Explicit RAM wiping after processing

### **Compute Providers**
- **Local Inference**: Ollama integration for complete privacy
- **OpenAI Integration**: ChatGPT with privacy-enhanced prompts
- **Replicate Fallback**: External AI when local processing unavailable
- **Multi-Model Orchestration**: Infrastructure for combining multiple AI providers

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
export OPENAI_API_KEY=your_openai_key_here  # optional, for ChatGPT integration
export ANTHROPIC_API_KEY=your_anthropic_key_here  # optional, for Claude integration
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

### Docker Setup

1. **Build the Docker image:**
```bash
docker build -t vana-personal-server .
```

2. **Run with Docker:**
```bash
docker run -p 8080:8080 \
  -e REPLICATE_API_TOKEN=your_token_here \
  -e WALLET_MNEMONIC=your_mnemonic_here \
  -e CHAIN_ID=your_chain_id_here \
  -e MNEMONIC_LANGUAGE=english \
  -e OPENAI_API_KEY=your_openai_key_here \
  vana-personal-server
```

The server will be available at `http://localhost:8080`.

3. **Using Docker Compose (optional):**
```bash
# Create docker-compose.yml with your environment variables
docker-compose up -d
```

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
│   ├── operations.py        # Operation orchestration with privacy pipeline
│   └── identity.py          # Identity derivation service
├── compute/                  # Compute provider integrations
│   ├── base.py              # Abstract compute interface
│   ├── replicate.py         # Replicate API integration
│   ├── local_inference.py   # Local AI inference with Ollama
│   ├── openai_provider.py   # OpenAI integration with privacy controls
│   └── privacy_preserving_inference.py # Privacy-enhanced external AI
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
│   ├── ipfs.py              # IPFS integration utilities
│   ├── differential_privacy.py # Differential privacy implementation
│   ├── secure_memory.py     # Secure memory management
│   ├── privacy_classifier.py # Document classification
│   ├── feature_extractor.py # Safe feature extraction
│   ├── embedding_generator.py # Vector embedding generation
│   ├── synthetic_generator.py # Synthetic data generation
│   └── privacy_pipeline.py  # Complete privacy pipeline
├── llm/                      # Large Language Model integration
│   └── llm.py               # LLM service implementation
├── tests/                    # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── test_utils.py        # Test utilities for real data
├── scripts/                  # Utility scripts
│   ├── demo_flow.py         # Privacy pipeline demonstration
│   ├── encryption_demo.py   # Encryption demonstration
│   └── query_blockchain.py  # Blockchain data querying
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

### Privacy Pipeline Testing

Test the privacy features:
```bash
# Test individual components
poetry run python utils/differential_privacy.py
poetry run python utils/secure_memory.py

# Test complete pipeline
poetry run python utils/privacy_pipeline.py

# Test ChatGPT integration
poetry run python test_chatgpt_integration.py
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
- `OPENAI_API_KEY` - OpenAI API key for ChatGPT integration
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude integration

### Security Considerations

⚠️ **Important Security Notes:**
- This project is under active development and may contain security vulnerabilities
- Never commit sensitive environment variables to version control
- Use secure methods to manage your wallet mnemonic in production
- Review all permissions and data access patterns before deployment
- Monitor for suspicious activity and implement appropriate logging
- The privacy pipeline provides mathematical privacy guarantees but requires proper configuration
- Local AI inference provides the highest level of privacy protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is part of the Vana ecosystem. Please refer to the license file for details.