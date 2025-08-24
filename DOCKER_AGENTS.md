# Docker Agent Sandbox Implementation

## Overview

This implementation replaces direct host-based agent execution with secure Docker-based sandboxing using the "Agent-in-a-Box" pattern.

## Security Features (Phase 1 - Foundation)

- **Network Isolation**: `--network none` - Complete network isolation
- **User Isolation**: Non-root execution as `appuser`
- **Filesystem Isolation**: Read-only container filesystem with writable workspace
- **Resource Limits**: Configurable memory and CPU constraints
- **Timeout Controls**: Configurable execution timeouts

## Architecture

### Components

1. **DockerAgentRunner** (`services/agent_runner.py`)
   - Core Docker execution service
   - Handles container lifecycle and security controls
   - Manages workspace mounting and artifact collection

2. **BaseAgentProvider** (`compute/base_agent.py`)
   - Updated to use Docker execution instead of pexpect
   - Maintains same interface for backward compatibility
   - Lazy-loads Docker runner with configuration

3. **Agent Dockerfile** (`Dockerfile.agent`)
   - Minimal Alpine-based image with Node.js
   - Pre-installs agent CLI tools (qwen, gemini)
   - Configured for secure non-root execution

4. **Configuration** (`settings.py`)
   - `DOCKER_AGENT_IMAGE`: Image name (default: vana-agent-sandbox)
   - `DOCKER_AGENT_MEMORY_LIMIT`: Memory limit (default: 512m)
   - `DOCKER_AGENT_CPU_LIMIT`: CPU limit (default: 1.0)
   - `DOCKER_AGENT_TIMEOUT_SEC`: Timeout (default: 300)
   - `DOCKER_AGENT_MAX_OUTPUT_MB`: Output limit (default: 10MB)

## Setup Instructions

### 1. Build Agent Docker Image

```bash
docker build -f Dockerfile.agent -t vana-agent-sandbox .
```

### 2. Install Dependencies

```bash
poetry install  # Installs docker SDK
```

### 3. Configuration (Optional)

Set environment variables to customize:

```bash
export DOCKER_AGENT_MEMORY_LIMIT="1g"
export DOCKER_AGENT_CPU_LIMIT="2.0"
export DOCKER_AGENT_TIMEOUT_SEC="600"
```

## Testing

### Manual Testing

Run the test script to verify functionality:

```bash
python3 test_docker_agents.py
```

### Integration Testing

The existing test suite will work with Docker agents. The Docker implementation maintains the same API interface as the original pexpect-based execution.

## Security Model

### Isolation Boundaries

1. **Network**: Complete isolation (`--network none`)
2. **Filesystem**: Read-only container + writable workspace mount
3. **Process**: Non-root user execution
4. **Resources**: Memory and CPU limits enforced by Docker

### Trust Boundaries

- **Trusted**: Host system, Docker daemon, server process
- **Untrusted**: Agent code, user data, generated artifacts
- **Sandbox**: Docker container with security controls

### Data Flow

1. User data staged in temporary workspace directory
2. Workspace mounted into read-only container
3. Agent executes with no network access
4. Artifacts collected from workspace output directory
5. Workspace cleaned up automatically

## Migration Notes

### Backward Compatibility

The Docker implementation is drop-in compatible with existing agent code:

- Same `BaseAgentProvider` interface
- Same artifact handling
- Same configuration patterns
- Same error handling

### Performance Considerations

- Container startup overhead (~1-2 seconds)
- Increased memory usage (container base image)
- Network isolation may break agents requiring external APIs (by design)

## Future Enhancements (Phase 2+)

- Linux capabilities restrictions
- Seccomp profiles
- AppArmor/SELinux integration
- Resource quotas and scheduling
- Multi-container orchestration
- Enhanced monitoring and logging