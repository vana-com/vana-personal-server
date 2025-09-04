#!/bin/bash
# Build the agent sandbox Docker image

echo "Building agent sandbox Docker image..."
docker build -f Dockerfile.agent -t vana-agent-sandbox .

if [ $? -eq 0 ]; then
    echo "✓ Agent sandbox image built successfully: vana-agent-sandbox"
    echo ""
    echo "You can now run the personal server with Docker agent support:"
    echo "  docker-compose up --build"
else
    echo "✗ Failed to build agent sandbox image"
    exit 1
fi