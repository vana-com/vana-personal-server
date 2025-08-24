# Local Docker Testing Guide

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build

# View logs
docker-compose logs -f personal-server

# Stop services
docker-compose down
```

### 2. Test the Service

```bash
# Run the test script
./test_local_docker.sh

# Or test manually with curl
curl http://localhost:8080/identity?address=0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6
```

## Docker Setup Details

### Services Included

1. **personal-server**: Main API service on port 8080
2. **local-blockchain** (optional): Ganache blockchain on port 8545

### Environment Configuration

The `docker-compose.yml` includes:

- **Development Mode** (default): Uses OAuth for agent authentication
- **Production Mode**: Configure API keys in `.env` file

### Create .env File (Optional)

```bash
# Create .env file for production mode
cat > .env << 'EOF'
# Blockchain Configuration
WALLET_MNEMONIC=your twelve word mnemonic phrase here for production use only
CHAIN_ID=1
RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
DATA_REGISTRY_ADDRESS=0xYourContractAddress
DATA_PERMISSIONS_ADDRESS=0xYourContractAddress

# Qwen Agent (Production)
QWEN_API_KEY=your-qwen-api-key
QWEN_API_URL=https://api.qwen.ai/v1
QWEN_MODEL_NAME=qwen-coder-32b

# Gemini Agent (Production)
GEMINI_API_KEY=your-gemini-api-key
EOF
```

## Testing Agent Operations

### Option 1: Development Mode with OAuth

```bash
# First, authenticate locally (outside container)
qwen auth login
gemini auth login

# Then mount auth directory in container
docker run -it \
  -v ~/.config:/root/.config:ro \
  -p 8080:8080 \
  personal-server
```

### Option 2: Production Mode with API Keys

1. Set API keys in `.env` file
2. Run with docker-compose: `docker-compose up`

### Option 3: Full Integration Test

For a complete end-to-end test with blockchain:

```bash
# 1. Start services including local blockchain
docker-compose up -d

# 2. Deploy contracts (requires separate setup)
# npm run deploy:local

# 3. Create test permission on-chain
# npm run create:permission

# 4. Test with curl
curl -X POST http://localhost:8080/operations \
  -H "Content-Type: application/json" \
  -d '{
    "app_signature": "0x...",
    "operation_request_json": "{\"permission_id\": 1}"
  }'
```

## Debugging

### View Container Logs

```bash
# All logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 personal-server
```

### Execute Commands in Container

```bash
# Open shell in running container
docker-compose exec personal-server /bin/bash

# Check if CLI tools are installed
docker-compose exec personal-server which qwen
docker-compose exec personal-server which gemini

# Test CLI tools directly
docker-compose exec personal-server qwen --version
docker-compose exec personal-server gemini --version
```

### Health Check

```bash
# Check service health
curl http://localhost:8080/identity?address=0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6

# Check container status
docker-compose ps

# Check resource usage
docker stats
```

## Mock Testing Without Blockchain

To test agent routing without a real blockchain:

```python
# test_mock_agent.py
import requests
import json

# This will fail without blockchain, but shows the routing
response = requests.post(
    "http://localhost:8080/operations",
    json={
        "app_signature": "0x" + "0" * 130,
        "operation_request_json": json.dumps({"permission_id": 1})
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
# Expected: Error about blockchain/permission not found
# But logs will show routing attempt
```

## Container Architecture

```
personal-server container
├── /app (application code)
├── Node.js 20.x
├── Python 3.12
├── qwen CLI (global npm package)
├── gemini CLI (global npm package)
└── Python dependencies (via Poetry)
```

## Troubleshooting

### Common Issues

1. **Port 8080 already in use**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "8081:8080"  # Use 8081 instead
   ```

2. **CLI tools not found**
   ```bash
   # Rebuild image to ensure CLIs are installed
   docker-compose build --no-cache personal-server
   ```

3. **Authentication errors**
   - Development: Ensure OAuth tokens are valid
   - Production: Check API keys in .env file

4. **Blockchain connection errors**
   - Verify RPC_URL is accessible
   - Check contract addresses are correct
   - Ensure wallet has sufficient funds

### Testing Checklist

- [ ] Docker image builds successfully
- [ ] Container starts without errors
- [ ] Identity endpoint responds
- [ ] CLI tools are installed in container
- [ ] Environment variables are set correctly
- [ ] Logs show proper agent routing
- [ ] Health check passes

## Next Steps

1. **Set up blockchain**: Deploy contracts for full testing
2. **Configure IPFS**: For grant file storage
3. **Add monitoring**: Prometheus/Grafana for production
4. **Set up CI/CD**: Automated testing in GitHub Actions