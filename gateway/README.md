# Vana Personal-Server API

A user-scoped compute service that executes permissioned operations on private data. This implementation proxies requests to Replicate's API.

## Setup

1. Install dependencies:
```bash
cd server
pip install -r requirements.txt
```

2. Set environment variable:
```bash
export REPLICATE_API_TOKEN=your_token_here
```

3. Run the server:
```bash
python app.py
```

Or with uvicorn directly:
```bash
uvicorn app:app --reload
```

## API

The server runs on `http://localhost:8000` with automatic OpenAPI docs at `http://localhost:8000/docs`.

### Endpoints

- `POST /api/v1/operations` - Start an operation
- `GET /api/v1/operations/{id}` - Get operation status
- `DELETE /api/v1/operations/{id}` - Cancel operation
- `GET /api/v1/identity` - Get server identity

## Structure

- `entities.py` - Data models and enums
- `services.py` - Stateless services that proxy to Replicate API
- `routes.py` - FastAPI router with all endpoints
- `app.py` - Main FastAPI application entry point