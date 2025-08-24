# Makefile for Personal Server with Agent Integration

# Detect if we should use 'docker-compose' or 'docker compose'
DOCKER_COMPOSE := $(shell command -v docker-compose 2> /dev/null)
ifeq ($(DOCKER_COMPOSE),)
    DOCKER_COMPOSE := docker compose
endif

.PHONY: help build up down logs test clean shell test-agents test-container

help: ## Show this help message
	@echo "Personal Server - Agent Integration"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

build: ## Build Docker image
	$(DOCKER_COMPOSE) build

up: ## Start services in background
	$(DOCKER_COMPOSE) up -d
	@echo "Waiting for service to be healthy..."
	@sleep 5
	@make test-health

up-verbose: ## Start services with logs
	$(DOCKER_COMPOSE) up --build

down: ## Stop and remove containers
	$(DOCKER_COMPOSE) down

logs: ## Show service logs
	$(DOCKER_COMPOSE) logs -f personal-server

test-health: ## Test if service is healthy
	@curl -s http://localhost:8080/api/v1/identity?address=0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6 > /dev/null && \
		echo "✓ Service is healthy" || \
		echo "✗ Service health check failed"

test: ## Run local tests
	./test_local_docker.sh

test-agents: ## Test agent CLI tools in container
	$(DOCKER_COMPOSE) exec personal-server python3 test_container_agent.py

test-container: ## Run all tests inside container
	$(DOCKER_COMPOSE) exec personal-server bash -c "python3 test_container_agent.py && python3 test_agent_routing.py"

shell: ## Open shell in running container
	$(DOCKER_COMPOSE) exec personal-server /bin/bash

clean: ## Clean up containers and volumes
	$(DOCKER_COMPOSE) down -v
	docker system prune -f

# Development targets
dev-build: ## Build for development with cache mount
	DOCKER_BUILDKIT=1 docker build \
		--cache-from personal-server:latest \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		-t personal-server:latest .

dev-run: ## Run with development settings
	docker run -it --rm \
		-p 8080:8080 \
		-v $(PWD):/app \
		-e LOG_LEVEL=DEBUG \
		personal-server:latest

# Testing targets
test-qwen: ## Test Qwen agent routing
	@echo "Testing Qwen agent operation..."
	@curl -X POST http://localhost:8080/api/v1/operations \
		-H "Content-Type: application/json" \
		-d '{"app_signature":"0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000","operation_request_json":"{\"permission_id\": 3072}"}' \
		2>/dev/null | jq . || echo "Expected: Requires blockchain setup"

test-gemini: ## Test Gemini agent routing
	@echo "Testing Gemini agent operation..."
	@curl -X POST http://localhost:8080/api/v1/operations \
		-H "Content-Type: application/json" \
		-d '{"app_signature":"0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000","operation_request_json":"{\"permission_id\": 4096}"}' \
		2>/dev/null | jq . || echo "Expected: Requires blockchain setup"

# Installation verification
verify-install: ## Verify CLI tools are installed in container
	@echo "Checking Qwen CLI..."
	@$(DOCKER_COMPOSE) exec personal-server which qwen || echo "Not found"
	@echo ""
	@echo "Checking Gemini CLI..."
	@$(DOCKER_COMPOSE) exec personal-server which gemini || echo "Not found"
	@echo ""
	@echo "Checking Node.js..."
	@$(DOCKER_COMPOSE) exec personal-server node --version || echo "Not found"

# Docker image inspection
inspect: ## Inspect the Docker image
	$(DOCKER_COMPOSE) exec personal-server bash -c "echo '=== Installed NPM packages ===' && npm list -g --depth=0"
	$(DOCKER_COMPOSE) exec personal-server bash -c "echo '=== Python packages ===' && pip list | grep -E 'pexpect|web3|httpx'"

# Quick start
quickstart: ## Quick start: build, run, and test
	@echo "Starting Personal Server with Agent Integration..."
	@make build
	@make up
	@sleep 5
	@make test-health
	@make verify-install
	@echo ""
	@echo "✓ Setup complete!"
	@echo ""
	@echo "API endpoint: http://localhost:8080"
	@echo "View logs: make logs"
	@echo "Run tests: make test"
	@echo "Stop services: make down"