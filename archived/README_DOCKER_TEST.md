# Docker Testing Instructions

## Prerequisites

- Docker and Docker Compose installed
- Port 8080 available (or modify in docker-compose.yml)
- (Optional) Node.js for local CLI testing

## Quick Test

```bash
# 1. Build and start the service
make quickstart

# Or manually:
docker-compose up --build

# 2. In another terminal, run tests
make test

# 3. Check agent tools are installed
make verify-install

# 4. View logs
make logs

# 5. Stop everything
make down
```

## Step-by-Step Testing

### 1. Build the Docker Image

```bash
# Build with docker-compose
docker-compose build

# Or build standalone
docker build -t personal-server .
```

### 2. Start the Service

```bash
# Start in background
docker-compose up -d

# Or start with logs visible
docker-compose up
```

### 3. Verify Installation

```bash
# Check if CLI tools are installed
docker-compose exec personal-server which qwen
docker-compose exec personal-server which gemini

# Run the container test script
docker-compose exec personal-server python3 test_container_agent.py
```

### 4. Test API Endpoints

```bash
# Test identity endpoint (should work)
curl http://localhost:8080/identity?address=0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6

# Test agent operations (will fail without blockchain)
./test_local_docker.sh
```

### 5. Test Agent Routing

```bash
# Inside container
docker-compose exec personal-server python3 test_agent_routing.py

# Check routing logs
docker-compose logs personal-server | grep -E "Routing to|agent provider"
```

## Expected Results

### ✅ What Should Work

1. **Docker Build**: Image builds with Node.js and CLI tools
2. **Container Start**: Service starts on port 8080
3. **Health Check**: Identity endpoint responds
4. **CLI Tools**: `qwen` and `gemini` commands available in container
5. **Routing Logic**: Correct provider selected based on operation type

### ⚠️ What Requires Additional Setup

1. **Actual Operations**: Need blockchain and permissions
2. **Agent Execution**: Need API keys or OAuth tokens
3. **File Processing**: Need IPFS and encrypted files

## Testing Without Full Setup

To test routing without blockchain:

```python
# Save as test_mock.py and run with: python3 test_mock.py

import requests
import json

# This will fail but shows routing in logs
resp = requests.post("http://localhost:8080/operations", 
    json={
        "app_signature": "0x" + "0" * 130,
        "operation_request_json": json.dumps({"permission_id": 1})
    })

print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")

# Check Docker logs to see routing attempts:
# docker-compose logs | grep -i "routing"
```

## Environment Variables for Testing

Create `.env` file for testing:

```bash
cat > .env << 'EOF'
# Minimal config for testing
WALLET_MNEMONIC=test test test test test test test test test test test junk
CHAIN_ID=1337
RPC_URL=http://localhost:8545

# Optional: Add API keys for agent testing
# QWEN_API_KEY=your-key-here
# GEMINI_API_KEY=your-key-here

LOG_LEVEL=DEBUG
EOF
```

## Debugging

### View Detailed Logs

```bash
# All logs with timestamps
docker-compose logs -t

# Follow logs for personal-server
docker-compose logs -f personal-server

# Search logs for routing
docker-compose logs | grep -A5 -B5 "operation.*qwen\|gemini"
```

### Interactive Container Session

```bash
# Open bash in container
docker-compose exec personal-server /bin/bash

# Inside container:
python3 -c "from compute.qwen_agent import QwenCodeAgentProvider; print('✓ Qwen imports')"
python3 -c "from compute.gemini_agent import GeminiAgentProvider; print('✓ Gemini imports')"
```

### Check Container Configuration

```bash
# List installed npm packages
docker-compose exec personal-server npm list -g --depth=0

# Check Python packages
docker-compose exec personal-server pip list

# Check environment variables
docker-compose exec personal-server env | grep -E "QWEN|GEMINI"
```

## Common Issues and Solutions

### Issue: Port 8080 in use
```bash
# Change port in docker-compose.yml
# ports:
#   - "8081:8080"
```

### Issue: CLI tools not found
```bash
# Rebuild without cache
docker-compose build --no-cache
```

### Issue: Module import errors
```bash
# Check Python path
docker-compose exec personal-server python3 -c "import sys; print(sys.path)"
```

### Issue: Permission denied
```bash
# Fix permissions
docker-compose exec personal-server chown -R appuser:appuser /app
```

## Summary

The Docker setup includes:

1. ✅ **Base Python environment** (3.12)
2. ✅ **Node.js runtime** (v20)
3. ✅ **Qwen CLI** (@qwen-chat/qwen-code)
4. ✅ **Gemini CLI** (@google/gemini-cli)
5. ✅ **Agent routing logic** (services/operations.py)
6. ✅ **OpenAPI documentation** (with agent schemas)

To fully test agent execution, you'll need:

1. 🔧 Deploy smart contracts
2. 🔧 Create on-chain permissions
3. 🔧 Upload grant files to IPFS
4. 🔧 Configure API keys or OAuth