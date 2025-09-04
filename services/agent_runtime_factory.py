"""
Agent runtime factory for selecting between Docker and Process execution.

Provides runtime abstraction to support both local/dev environments (Docker)
and Cloud Run environments (Process) using the same interface.
"""
import logging
from typing import Union

from settings import get_settings
from services.agent_runner import DockerAgentRunner
from services.process_agent_runner import ProcessAgentRunner

logger = logging.getLogger(__name__)

AgentRunner = Union[DockerAgentRunner, ProcessAgentRunner]


def create_agent_runner() -> AgentRunner:
    """
    Create an agent runner based on the configured runtime.
    
    Returns:
        DockerAgentRunner for local/dev environments
        ProcessAgentRunner for Cloud Run environments
    """
    settings = get_settings()
    runtime = settings.agent_runtime.lower()
    
    if runtime == "docker":
        logger.info("[RUNTIME] Using Docker agent runner")
        return DockerAgentRunner(
            image_name=settings.docker_agent_image,
            memory_limit=settings.docker_agent_memory_limit,
            timeout_sec=settings.docker_agent_timeout_sec,
            max_output_bytes=settings.docker_agent_max_output_mb * 1_000_000,
            cpu_limit=settings.docker_agent_cpu_limit or "1.0",
            allow_network=True  # Will be overridden by individual agents
        )
    
    elif runtime == "process":
        logger.info("[RUNTIME] Using Process agent runner")
        return ProcessAgentRunner(
            memory_limit_mb=settings.agent_memory_limit_mb,
            timeout_sec=settings.agent_timeout_sec,
            max_output_bytes=settings.agent_max_output_mb * 1_000_000,
            file_size_limit_mb=settings.agent_file_size_limit_mb
        )
    
    else:
        raise ValueError(
            f"Unknown agent runtime: {runtime}. "
            f"Valid options are 'docker' or 'process'"
        )


def get_runtime_info() -> dict:
    """
    Get information about the current agent runtime configuration.
    
    Returns:
        Dictionary with runtime type and configuration details
    """
    settings = get_settings()
    runtime = settings.agent_runtime.lower()
    
    if runtime == "docker":
        return {
            "type": "docker",
            "image": settings.docker_agent_image,
            "memory_limit": settings.docker_agent_memory_limit,
            "timeout_sec": settings.docker_agent_timeout_sec,
            "max_output_mb": settings.docker_agent_max_output_mb,
            "cpu_limit": settings.docker_agent_cpu_limit
        }
    
    elif runtime == "process":
        return {
            "type": "process",
            "memory_limit_mb": settings.agent_memory_limit_mb,
            "timeout_sec": settings.agent_timeout_sec,
            "max_output_mb": settings.agent_max_output_mb,
            "file_size_limit_mb": settings.agent_file_size_limit_mb,
            "max_concurrent": settings.agent_max_concurrent_per_instance
        }
    
    else:
        return {"type": "unknown", "error": f"Unknown runtime: {runtime}"}