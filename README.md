# Vana Personal-Server API

A user-scoped compute service that executes permissioned operations on private data. This implementation proxies requests to Replicate's API and integrates with blockchain-based data permissions.

## Setup

1. Install dependencies using Poetry:
```bash
poetry install
```

2. Set environment variables:
```bash
export REPLICATE_API_TOKEN=your_token_here
export WALLET_MNEMONIC=your_mnemonic_here
export MNEMONIC_LANGUAGE=english  # optional, defaults to english
```

3. Run the server:
```bash
poetry run python app.py
```

Or with uvicorn directly:
```bash
poetry run uvicorn app:app --reload
```

## API

The server runs on `http://localhost:8000` with automatic OpenAPI docs at `http://localhost:8000/docs`.

### Endpoints

- `POST /api/v1/operations` - Start an operation
- `GET /api/v1/operations/{id}` - Get operation status
- `POST /api/v1/operations/cancel` - Cancel operation
- `GET /api/v1/identity` - Get server identity for a user address

## Structure

- `app.py` - Main FastAPI application entry point
- `models.py` - Pydantic data models and validation
- `settings.py` - Application settings and environment configuration
- `domain.py` - Domain logic and business rules
- `api/` - FastAPI routers
  - `operations.py` - Operation management endpoints
  - `identity.py` - Identity derivation endpoints
- `services/` - Business logic services
  - `operations.py` - Operation orchestration
  - `identity.py` - Identity derivation service
- `compute/` - Compute provider integrations
  - `replicate.py` - Replicate API integration
  - `base.py` - Abstract compute interface
- `onchain/` - Blockchain integration
  - `data_registry.py` - Data registry contract interactions
  - `data_permissions.py` - Permission checking logic
  - `chain.py` - Blockchain connection management
  - `abi.py` - Contract ABI definitions
- `grants/` - Data permission grants
  - `fetch.py` - Grant retrieval logic
  - `validate.py` - Grant validation
  - `schema/` - Grant schema definitions
- `files/` - File handling utilities
  - `download.py` - File download functionality
  - `decrypt.py` - File decryption utilities
- `utils/` - Utility functions
- `tests/` - Test suite