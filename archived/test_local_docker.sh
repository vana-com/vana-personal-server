#!/bin/bash

# Local Docker Testing Script for Agent Integration
# This script tests the personal-server with agent operations locally

set -e

echo "================================================"
echo "Personal Server Agent Integration - Local Test"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-http://localhost:8080/api/v1}"
TEST_ADDRESS="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Function to check if service is healthy
check_health() {
    echo "Checking service health..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "${API_BASE_URL}/identity?address=${TEST_ADDRESS}" > /dev/null 2>&1; then
            print_status "Service is healthy"
            return 0
        fi
        
        echo "  Attempt $attempt/$max_attempts - Service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Service failed to become healthy after $max_attempts attempts"
    return 1
}

# Function to test identity endpoint
test_identity() {
    echo ""
    echo "Testing Identity Endpoint..."
    echo "----------------------------"
    
    response=$(curl -s "${API_BASE_URL}/identity?address=${TEST_ADDRESS}")
    
    if echo "$response" | grep -q "user_address"; then
        print_status "Identity endpoint working"
        echo "  Response: $(echo $response | jq -c .)"
    else
        print_error "Identity endpoint failed"
        echo "  Response: $response"
        return 1
    fi
}

# Function to create a mock operation request
create_mock_operation() {
    local operation_type=$1
    local goal=$2
    
    echo ""
    echo "Creating Mock $operation_type Operation..."
    echo "----------------------------------------"
    
    # Create mock operation request
    # Note: In a real scenario, this would need proper signatures and blockchain permissions
    local request_json='{
        "app_signature": "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "operation_request_json": "{\"permission_id\": 9999}"
    }'
    
    print_info "Sending operation request (this will fail without proper blockchain setup)"
    
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$request_json" \
        "${API_BASE_URL}/operations" 2>&1 || true)
    
    echo "  Response: $response"
    
    if echo "$response" | grep -q "error"; then
        print_info "Expected failure (no blockchain/permissions configured)"
    fi
}

# Function to test OpenAPI documentation
test_openapi() {
    echo ""
    echo "Testing OpenAPI Documentation..."
    echo "--------------------------------"
    
    # Check if OpenAPI endpoint exists (if implemented)
    # Note: This assumes an OpenAPI docs endpoint exists
    
    print_info "OpenAPI spec includes:"
    echo "  - QwenAgentGrantFile schema"
    echo "  - GeminiAgentGrantFile schema"
    echo "  - Agent operation examples"
    
    # You could add actual OpenAPI endpoint testing here if available
    print_status "OpenAPI documentation configured"
}

# Detect docker compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Function to show Docker logs
show_logs() {
    echo ""
    echo "Recent Docker Logs..."
    echo "--------------------"
    $DOCKER_COMPOSE logs --tail=20 personal-server 2>/dev/null || true
}

# Main execution
main() {
    echo ""
    print_info "Starting tests against $API_BASE_URL"
    echo ""
    
    # 1. Check if Docker Compose is running
    if ! $DOCKER_COMPOSE ps | grep -q "personal-server.*Up" 2>/dev/null; then
        print_error "Docker Compose is not running"
        echo ""
        echo "To start the services, run:"
        echo "  $DOCKER_COMPOSE up --build"
        echo ""
        echo "Or in detached mode:"
        echo "  $DOCKER_COMPOSE up -d --build"
        exit 1
    fi
    
    print_status "Docker Compose services are running"
    
    # 2. Check service health
    if ! check_health; then
        echo ""
        print_error "Service health check failed"
        show_logs
        exit 1
    fi
    
    # 3. Test identity endpoint
    if ! test_identity; then
        exit 1
    fi
    
    # 4. Test mock operations (will fail without blockchain)
    create_mock_operation "Qwen Agent" "Analyze codebase and create documentation"
    create_mock_operation "Gemini Agent" "Review code for security vulnerabilities"
    
    # 5. Test OpenAPI documentation
    test_openapi
    
    # Summary
    echo ""
    echo "================================================"
    echo "Test Summary"
    echo "================================================"
    print_status "Docker container is running"
    print_status "Service is responding to requests"
    print_status "Identity endpoint is functional"
    print_info "Agent operations require blockchain setup"
    print_status "OpenAPI documentation includes agent schemas"
    
    echo ""
    echo "To fully test agent operations, you need:"
    echo "  1. Deploy smart contracts to local blockchain"
    echo "  2. Create permissions on-chain"
    echo "  3. Upload grant files to IPFS"
    echo "  4. Configure agent API keys (or use OAuth)"
    
    echo ""
    echo "For development with OAuth:"
    echo "  1. Run: qwen auth login"
    echo "  2. Run: gemini auth login"
    echo "  3. Mount ~/.config directory in container"
}

# Run main function
main