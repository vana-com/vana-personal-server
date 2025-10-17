# Docker Agent Sandbox (Experimental)

This directory contains infrastructure for running agents in isolated Docker containers.

## Status: Experimental

The Docker-based agent runtime is currently **experimental and not used in production**.

Production deployments use the **process-based runtime** (`ProcessAgentRunner`) which runs agents directly on Cloud Run without Docker-in-Docker overhead.

## What's Here

- `Dockerfile.agent` - Agent sandbox container image
- `build-agent-image.sh` - Build the sandbox image
- `setup-loop-device.sh` - Create filesystem limits for agent workspaces (requires root)
- `teardown-loop-device.sh` - Remove loop device setup

## When to Use

Use Docker sandbox runtime when:
- Running on local development machines
- Need stronger isolation between agent executions
- Testing agent behavior in containerized environments

## How It Works

1. Build sandbox image: `./build-agent-image.sh`
2. Set environment: `AGENT_RUNTIME=docker`
3. Agents execute in isolated containers via `DockerAgentRunner`

## Architecture

```
Agent Providers (Qwen, Gemini)
    ↓
AgentRuntimeFactory (AGENT_RUNTIME env)
    ↓
ProcessAgentRunner (production) | DockerAgentRunner (experimental)
```

See `services/agent_runner.py` for Docker implementation details.
