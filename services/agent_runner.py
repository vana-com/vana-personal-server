"""
Docker-based agent execution service implementing "Agent-in-a-Box" sandbox pattern.

Provides secure, isolated execution of AI agents using Docker containers with:
- Network isolation (--network none)
- Non-root execution (appuser)
- Read-only filesystem with writable workspace
- Resource constraints (memory, CPU, timeout)
- Artifact collection and processing

Phase 1 (Foundation): Basic Docker isolation with security hardening
"""
import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

logger = logging.getLogger(__name__)

# Sentinel to mark agent completion
SENTINEL = "__AGENT_DONE__"

class DockerAgentRunner:
    """
    Secure Docker-based agent execution service.
    
    Implements the Agent-in-a-Box pattern with strict security controls:
    - Network isolation: --network none (no external connectivity)
    - User isolation: Run as non-root appuser
    - Filesystem isolation: Read-only with writable workspace mount
    - Resource limits: Memory, timeout constraints
    """
    
    def __init__(
        self,
        image_name: str = "vana-agent-sandbox",
        memory_limit: str = "512m",
        timeout_sec: int = 300,
        max_output_bytes: int = 2_000_000,
        cpu_limit: str = "1.0"
    ):
        """
        Initialize Docker agent runner.
        
        Args:
            image_name: Docker image for agent execution
            memory_limit: Memory limit (e.g., "512m", "1g")
            timeout_sec: Execution timeout in seconds
            max_output_bytes: Maximum output capture size
            cpu_limit: CPU limit (e.g., "0.5", "1.0", "2.0")
        """
        self.image_name = image_name
        self.memory_limit = memory_limit
        self.timeout_sec = timeout_sec
        self.max_output_bytes = max_output_bytes
        self.cpu_limit = cpu_limit
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise RuntimeError(f"Docker unavailable: {e}")
    
    async def execute_agent(
        self,
        agent_type: str,
        command: str,
        args: List[str],
        workspace_files: Dict[str, bytes],
        env_vars: Dict[str, str],
        operation_id: str
    ) -> Dict[str, Any]:
        """
        Execute agent in secure Docker container.
        
        Args:
            agent_type: Agent type identifier (qwen/gemini)
            command: CLI command to execute
            args: Command arguments
            workspace_files: Files to mount in workspace {filename: content}
            env_vars: Environment variables for agent
            operation_id: Operation identifier for logging
            
        Returns:
            Execution result with status, output, artifacts, and logs
        """
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "workspace"
            workspace_path.mkdir()
            
            try:
                # Stage workspace files
                self._stage_workspace_files(workspace_path, workspace_files)
                
                # Execute in container
                result = await self._run_container(
                    agent_type, command, args, workspace_path, env_vars, operation_id
                )
                
                # Process artifacts from workspace
                artifacts = self._collect_artifacts(workspace_path, operation_id)
                result["artifacts"] = artifacts
                result["execution_time"] = time.time() - start_time
                
                return result
                
            except Exception as e:
                logger.error(f"[DOCKER-{agent_type}] Agent execution failed: {e}")
                return {
                    "status": "error",
                    "summary": f"Docker execution failed: {type(e).__name__}",
                    "result": {},
                    "artifacts": [],
                    "logs": [str(e)],
                    "stdout": "",
                    "execution_time": time.time() - start_time
                }
    
    def _stage_workspace_files(self, workspace_path: Path, files_dict: Dict[str, bytes]):
        """Stage input files in the workspace directory."""
        for filename, content in files_dict.items():
            file_path = workspace_path / filename
            # Ensure safe path (no directory traversal)
            try:
                file_path.relative_to(workspace_path)
                file_path.write_bytes(content)
                logger.debug(f"Staged file: {filename} ({len(content)} bytes)")
            except ValueError as e:
                logger.warning(f"Skipping unsafe file path: {filename}: {e}")
    
    async def _run_container(
        self,
        agent_type: str,
        command: str,
        args: List[str],
        workspace_path: Path,
        env_vars: Dict[str, str],
        operation_id: str
    ) -> Dict[str, Any]:
        """
        Run agent command in secure Docker container.
        
        Implements Phase 1 security controls:
        - network_mode="none": Complete network isolation
        - user="appuser": Non-root execution
        - read_only=True: Immutable container filesystem
        - Working directory mounted as writable for artifacts
        """
        full_command = [command] + args
        
        # Prepare secure container configuration
        container_config = {
            "image": self.image_name,
            "command": full_command,
            "working_dir": "/workspace",
            "environment": self._prepare_environment(env_vars),
            "volumes": {
                str(workspace_path): {"bind": "/workspace", "mode": "rw"}
            },
            "network_mode": "none",  # Complete network isolation
            "user": "appuser",       # Non-root execution
            "read_only": True,       # Read-only container filesystem
            "mem_limit": self.memory_limit,  # Memory constraint
            "cpu_quota": int(float(self.cpu_limit) * 100_000),  # CPU limit (100k = 1 CPU)
            "cpu_period": 100_000,   # CPU period (100ms)
            "detach": True,
        }
        
        logger.info(f"[DOCKER-{agent_type}] Starting container for {operation_id}")
        logger.debug(f"[DOCKER-{agent_type}] Command: {' '.join(full_command)}")
        
        try:
            # Run container asynchronously
            return await self._execute_container_async(container_config, agent_type, operation_id)
            
        except ImageNotFound:
            error_msg = f"Docker image '{self.image_name}' not found"
            logger.error(f"[DOCKER-{agent_type}] {error_msg}")
            return {
                "status": "error",
                "summary": error_msg,
                "result": {},
                "artifacts": [],
                "logs": [error_msg],
                "stdout": ""
            }
        except APIError as e:
            error_msg = f"Docker API error: {e}"
            logger.error(f"[DOCKER-{agent_type}] {error_msg}")
            return {
                "status": "error", 
                "summary": "Docker execution failed",
                "result": {},
                "artifacts": [],
                "logs": [error_msg],
                "stdout": ""
            }
    
    async def _execute_container_async(
        self, 
        container_config: Dict,
        agent_type: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """Execute container and capture output asynchronously."""
        
        def run_container():
            """Synchronous container execution."""
            container = None
            try:
                # Create and start container separately for better control
                container = self.docker_client.containers.create(**container_config)
                container.start()
                
                # Wait for completion with timeout
                start_time = time.time()
                while True:
                    container.reload()
                    if container.status in ['exited', 'dead']:
                        break
                    if time.time() - start_time > self.timeout_sec:
                        logger.warning(f"[DOCKER-{agent_type}] Container timeout, killing")
                        container.kill()
                        break
                    time.sleep(1)
                
                # Collect output
                logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='ignore')
                exit_code = container.attrs['State']['ExitCode']
                
                # Limit output size
                if len(logs) > self.max_output_bytes:
                    logs = logs[:self.max_output_bytes] + "\n... [output truncated]"
                
                # Clean up container
                try:
                    container.remove()
                    logger.debug(f"[DOCKER-{agent_type}] Container cleaned up")
                except:
                    pass  # Ignore cleanup errors
                
                return {
                    "stdout": logs,
                    "exit_code": exit_code,
                    "runtime_error": None
                }
                
            except ContainerError as e:
                logger.error(f"[DOCKER-{agent_type}] Container error: {e}")
                # Clean up container if it was created
                if container:
                    try:
                        container.remove(force=True)
                    except:
                        pass
                return {
                    "stdout": e.stderr.decode('utf-8', errors='ignore') if e.stderr else "",
                    "exit_code": e.exit_status,
                    "runtime_error": str(e)
                }
            except Exception as e:
                logger.error(f"[DOCKER-{agent_type}] Unexpected error: {e}")
                # Clean up container if it was created
                if container:
                    try:
                        container.remove(force=True)
                    except:
                        pass
                return {
                    "stdout": "",
                    "exit_code": -1,
                    "runtime_error": str(e)
                }
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        exec_result = await loop.run_in_executor(None, run_container)
        
        # Process results
        stdout = exec_result["stdout"]
        exit_code = exec_result["exit_code"]
        runtime_error = exec_result["runtime_error"]
        
        logs = []
        if runtime_error:
            logs.append(f"Runtime error: {runtime_error}")
        if exit_code != 0:
            logs.append(f"Process exited with code: {exit_code}")
        
        # Parse JSON result from output
        parsed_json = self._parse_agent_result(stdout)
        
        # Determine final status with comprehensive fallbacks
        has_sentinel = SENTINEL in stdout
        
        # Check for common error patterns in output
        error_patterns = [
            "error:", "exception:", "traceback:", "failed:", 
            "permission denied", "not found", "syntax error"
        ]
        has_error_pattern = any(
            pattern in stdout.lower() 
            for pattern in error_patterns
        )
        
        if runtime_error:
            status = "error"
            summary = f"Container execution failed: {runtime_error[:100]}"
        elif parsed_json:
            status = parsed_json.get("status", "ok" if has_sentinel else "error")
            summary = parsed_json.get("summary", "Agent completed")
        elif has_sentinel and not has_error_pattern:
            # Agent printed sentinel but no JSON - partial success
            status = "warning"
            summary = "Agent completed but produced no structured output"
        elif has_error_pattern:
            # Detected error patterns in output
            status = "error"
            summary = "Agent encountered errors during execution"
        else:
            status = "error"
            summary = "Agent failed to complete (no result or sentinel)"
        
        return {
            "status": status,
            "summary": summary,
            "result": parsed_json or {},
            "artifacts": [],  # Will be populated by caller
            "logs": logs,
            "stdout": stdout
        }
    
    def _prepare_environment(self, env_vars: Dict[str, str]) -> Dict[str, str]:
        """Prepare environment variables for container execution."""
        # Base security environment
        secure_env = {
            "CI": "1",
            "NO_COLOR": "1",
            "HOME": "/home/appuser",
            "USER": "appuser",
            "TERM": "xterm",
        }
        
        # Add agent-specific environment variables
        secure_env.update(env_vars)
        
        return secure_env
    
    def _parse_agent_result(self, output: str) -> Optional[Dict]:
        """
        Parse JSON result from agent output with comprehensive error handling.
        
        Handles edge cases:
        - Multiple JSON objects in output
        - Partial/malformed JSON
        - JSON embedded in other text
        - No JSON present
        """
        # Look for JSON line in output (agents output result as single JSON line)
        json_candidates = []
        
        for line in reversed(output.splitlines()):
            line = line.strip()
            
            # Skip empty lines and obvious non-JSON
            if not line or not ('{' in line and '}' in line):
                continue
            
            # Try to extract JSON from the line
            # Handle cases where JSON is embedded in text
            start_idx = line.find('{')
            end_idx = line.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                potential_json = line[start_idx:end_idx]
                
                try:
                    parsed = json.loads(potential_json)
                    # Validate it looks like agent output
                    if isinstance(parsed, dict) and any(
                        key in parsed for key in ['status', 'summary', 'result', 'artifacts']
                    ):
                        json_candidates.append(parsed)
                except json.JSONDecodeError:
                    # Try to fix common issues
                    try:
                        # Handle single quotes (common in Python output)
                        fixed = potential_json.replace("'", '"')
                        parsed = json.loads(fixed)
                        if isinstance(parsed, dict):
                            json_candidates.append(parsed)
                    except:
                        continue
        
        # Return the most complete candidate (with most expected fields)
        if json_candidates:
            def score_candidate(obj):
                expected_fields = ['status', 'summary', 'artifacts', 'result']
                return sum(1 for field in expected_fields if field in obj)
            
            return max(json_candidates, key=score_candidate)
        
        return None
    
    def _collect_artifacts(self, workspace_path: Path, operation_id: str) -> List[Dict]:
        """Collect artifacts from workspace output directory."""
        artifacts = []
        out_dir = workspace_path / "out"
        
        if out_dir.exists() and out_dir.is_dir():
            for file_path in out_dir.iterdir():
                if file_path.is_file():
                    try:
                        content = file_path.read_bytes()
                        artifacts.append({
                            "name": file_path.name,
                            "content": content,
                            "size": len(content),
                            "artifact_path": f"out/{file_path.name}"
                        })
                        logger.info(f"[DOCKER] Collected artifact: {file_path.name} ({len(content)} bytes)")
                    except Exception as e:
                        logger.warning(f"[DOCKER] Failed to collect artifact {file_path}: {e}")
        
        return artifacts
    
    def cleanup(self):
        """Cleanup Docker resources."""
        try:
            self.docker_client.close()
            logger.debug("Docker client closed")
        except Exception as e:
            logger.warning(f"Error closing Docker client: {e}")