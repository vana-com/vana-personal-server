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
        cpu_limit: str = "1.0",
        allow_network: bool = False
    ):
        """
        Initialize Docker agent runner.
        
        Args:
            image_name: Docker image for agent execution
            memory_limit: Memory limit (e.g., "512m", "1g")
            timeout_sec: Execution timeout in seconds
            max_output_bytes: Maximum output capture size
            cpu_limit: CPU limit (e.g., "0.5", "1.0", "2.0")
            allow_network: Allow network access (needed for API calls)
        """
        self.image_name = image_name
        self.memory_limit = memory_limit
        self.timeout_sec = timeout_sec
        self.max_output_bytes = max_output_bytes
        self.cpu_limit = cpu_limit
        self.allow_network = allow_network
        
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
        operation_id: str,
        task_store=None,  # Optional task store for streaming logs
        stdin_input: Optional[str] = None  # Optional stdin input for long prompts
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
            stdin_input: Optional input to pass via stdin (for long prompts)
            
        Returns:
            Execution result with status, output, artifacts, and logs
        """
        start_time = time.time()
        
        logger.info(f"[DOCKER-{agent_type}] execute_agent called with stdin_input={bool(stdin_input)} (length={len(stdin_input) if stdin_input else 0})")
        
        # 1. Define the base path for workspaces inside the container's shared volume.
        #    This path (/app/.agent_workspaces) exists both in the container AND on the host.
        workspace_base_dir = Path("/app/.agent_workspaces")
        workspace_base_dir.mkdir(exist_ok=True)
        
        # Guard: ensure directory is writable
        if not os.access(workspace_base_dir, os.W_OK):
            raise RuntimeError(f"{workspace_base_dir} not writable; run: mkdir -p .agent_workspaces && chmod 755 .agent_workspaces (or export UID=$(id -u) GID=$(id -g) before docker compose up)")
        
        # Guard: ensure sufficient disk space (100MB minimum)
        import shutil
        if shutil.disk_usage(str(workspace_base_dir)).free < 100_000_000:
            raise RuntimeError("Insufficient disk space: less than 100MB free")

        # 2. Create a unique, temporary directory for this specific operation.
        #    This directory is created inside the shared volume.
        operation_workspace_path = Path(tempfile.mkdtemp(prefix=f"{operation_id}_", dir=workspace_base_dir))
        # Fix permissions immediately - tempfile.mkdtemp creates 0o700 (owner-only)
        # Agent container runs as different UID, needs traverse AND write access
        operation_workspace_path.chmod(0o777)  # Allow read/write/execute for all users
        
        try:
            # 3. Translate the container path to the absolute path on the HOST.
            #    The Docker daemon needs this path for the volume mount.
            # Since we're in the container at /app, and /app is mounted from host's project root,
            # we need to replace /app with the actual host project directory
            host_project_dir = os.environ.get("HOST_PROJECT_DIR", os.getcwd())
            host_workspace_path = str(operation_workspace_path).replace('/app', host_project_dir)

            self._stage_workspace_files(operation_workspace_path, workspace_files)
            
            if stdin_input:
                stdin_file = operation_workspace_path / ".stdin_input"
                stdin_file.write_text(stdin_input, encoding='utf-8')
                # Make file readable by all users (agent container may have different UID)
                stdin_file.chmod(0o644)
                logger.info(f"[DOCKER] Wrote stdin input to {stdin_file}")
            
            # 5. Execute the container, providing the HOST path for the volume.
            result = await self._run_container(
                agent_type, command, args, str(host_workspace_path), env_vars, 
                operation_id, task_store
            )
            
            # Collect artifacts from workspace (bind mount means they're on host filesystem)
            artifacts = self._collect_artifacts(operation_workspace_path, operation_id)
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
        finally:
            # 6. Clean up the workspace using the container's path.
            try:
                import shutil
                shutil.rmtree(operation_workspace_path)
                logger.debug(f"[DOCKER] Cleaned up workspace: {operation_workspace_path}")
            except Exception as e:
                logger.error(f"[DOCKER] Failed to cleanup workspace {operation_workspace_path}: {e}")
    
    def _stage_workspace_files(self, workspace_path: Path, files_dict: Dict[str, bytes]):
        """Stage input files in the workspace directory."""
        for filename, content in files_dict.items():
            file_path = workspace_path / filename
            # Ensure safe path (no directory traversal)
            try:
                file_path.relative_to(workspace_path)
                file_path.write_bytes(content)
                # Make files world-readable to avoid UID/GID issues
                file_path.chmod(0o644)
                logger.debug(f"Staged file: {filename} ({len(content)} bytes, mode: {oct(file_path.stat().st_mode)})")
            except ValueError as e:
                logger.warning(f"Skipping unsafe file path: {filename}: {e}")
    
    async def _run_container(
        self,
        agent_type: str,
        command: str,
        args: List[str],
        host_workspace_path: str,
        env_vars: Dict[str, str],
        operation_id: str,
        task_store=None
    ) -> Dict[str, Any]:
        """
        Run agent command in secure Docker container.
        
        Implements Phase 1 security controls:
        - network_mode="none": Complete network isolation
        - user="appuser": Non-root execution
        - read_only=True: Immutable container filesystem
        - Working directory mounted as writable for artifacts
        """
        # Ensure command is executed through shell to find npm-installed binaries
        # The command should be in PATH from Dockerfile ENV PATH="/workspace/node_modules/.bin:${PATH}"
        # Use shlex to properly escape arguments for shell
        import shlex
        escaped_args = ' '.join(shlex.quote(arg) for arg in args)
        
        # Check if stdin input file exists and pipe it to the command
        full_command = ["sh", "-c", f"if [ -f .stdin_input ]; then cat .stdin_input | {command} {escaped_args}; else {command} {escaped_args}; fi"]
        
        # Determine network mode based on agent requirements
        # Allow network for agents that need API access, otherwise isolate
        network_mode = "bridge" if self.allow_network else "none"
        
        # Prepare secure container configuration
        container_config = {
            "image": self.image_name,
            "command": full_command,
            "working_dir": "/workspace/agent-work",
            "environment": self._prepare_environment(env_vars),
            # Use volumes dict for Docker API (expects host paths)
            "volumes": {
                host_workspace_path: {"bind": "/workspace/agent-work", "mode": "rw,z"}  # Workspace for input/output
            },
            # Use tmpfs for writable directories (not the workspace)
            "tmpfs": {
                "/home/appuser": "size=50m,mode=1777",  # Writable home directory
                "/tmp": "size=100m,mode=1777",  # Temp directory
            },
            "network_mode": network_mode,  # Conditional network access
            "user": f"{os.getuid()}:{os.getgid()}",  # Match orchestrator UID/GID
            "mem_limit": self.memory_limit,  # Memory constraint
            "cpu_quota": int(float(self.cpu_limit) * 100_000),  # CPU limit (100k = 1 CPU)
            "cpu_period": 100_000,   # CPU period (100ms)
            "detach": True,
            # Security hardening as suggested
            "cap_drop": ["ALL"],  # Drop all capabilities
            "security_opt": ["no-new-privileges:true"],  # Prevent privilege escalation
            "pids_limit": 256,  # Prevent fork bombs
            # Add file size limit to prevent single huge files
            "ulimits": [
                {"Name": "fsize", "Hard": 104857600, "Soft": 104857600}  # 100MB per file
            ]
        }
        
        logger.info(f"[DOCKER-{agent_type}] Starting container for {operation_id}")
        logger.debug(f"[DOCKER-{agent_type}] Command: {' '.join(full_command)}")
        logger.debug(f"[DOCKER-{agent_type}] Network mode: {network_mode}")
        logger.info(f"[DOCKER-{agent_type}] Mounting {host_workspace_path} -> /workspace/agent-work")
        
        try:
            # Run container asynchronously with streaming if task_store provided
            if task_store:
                return await self._execute_container_streaming(container_config, agent_type, operation_id, task_store)
            else:
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
        
        # Parse JSON result from output
        parsed_json = self._parse_agent_result(stdout)
        
        # Extract clean logs from stdout (excluding JSON and sentinel)
        clean_logs = self._extract_logs_from_stdout(stdout)
        
        # Add runtime errors to logs if any
        if runtime_error:
            clean_logs.append(f"Runtime error: {runtime_error}")
        if exit_code != 0 and exit_code != -1:
            clean_logs.append(f"Process exited with code: {exit_code}")
        
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
            status = parsed_json.get("status", "ok" if has_sentinel else "ok")
            summary = parsed_json.get("summary", "Agent completed successfully")
        elif has_sentinel and not has_error_pattern:
            # Agent printed sentinel but no JSON - partial success
            status = "ok" 
            summary = "Agent completed successfully"
        elif exit_code == 0 and not has_error_pattern:
            # Container exited successfully without errors, likely produced artifacts
            status = "ok"
            summary = "Agent completed successfully"
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
            "result": parsed_json.get("result", {}) if parsed_json else {},
            "artifacts": [],  # Will be populated by caller
            "logs": clean_logs,
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
    
    def _extract_logs_from_stdout(self, stdout: str) -> List[str]:
        """Extract clean logs from stdout, excluding JSON output and sentinel."""
        logs = []
        lines = stdout.split('\n')
        json_found = False
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Skip sentinel line
            if SENTINEL in line:
                break
            
            # Try to detect JSON output (agent result)
            if not json_found and line.strip().startswith('{'):
                try:
                    json.loads(line.strip())
                    json_found = True
                    continue  # Skip JSON line
                except (json.JSONDecodeError, ValueError):
                    pass  # Not JSON, include in logs
            
            # Include the line in logs
            logs.append(line.rstrip())
        
        return logs
    
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
    
    def _collect_artifacts_from_container(self, container, operation_id: str) -> List[Dict]:
        """Collect artifacts from container using get_archive (works on stopped containers)."""
        artifacts = []
        
        try:
            import tarfile
            import io
            
            # Try to get the entire output directory as tar archive
            try:
                bits, stat = container.get_archive("/workspace/agent-work/out")
            except docker.errors.NotFound:
                logger.debug(f"[DOCKER] No output directory found in container")
                return artifacts
            
            # Extract tar stream
            tar_stream = io.BytesIO()
            for chunk in bits:
                tar_stream.write(chunk)
            tar_stream.seek(0)
            
            # Parse tar archive
            with tarfile.open(fileobj=tar_stream, mode='r') as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        try:
                            # Extract file content
                            f = tar.extractfile(member)
                            if f:
                                content = f.read()
                                filename = Path(member.name).name
                                
                                artifacts.append({
                                    "name": filename,
                                    "content": content,
                                    "size": len(content),
                                    "artifact_path": filename
                                })
                                logger.info(f"[DOCKER] Collected artifact: {filename} ({len(content)} bytes)")
                        except Exception as e:
                            logger.warning(f"[DOCKER] Failed to extract {member.name}: {e}")
        except Exception as e:
            logger.warning(f"[DOCKER] Failed to collect artifacts: {e}")
        
        return artifacts
    
    def _collect_artifacts(self, workspace_path: Path, operation_id: str) -> List[Dict]:
        """Legacy artifact collection - kept for compatibility."""
        # This is now only used as a fallback
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
                            "artifact_path": file_path.name
                        })
                        logger.info(f"[DOCKER] Collected artifact: {file_path.name} ({len(content)} bytes)")
                    except Exception as e:
                        logger.warning(f"[DOCKER] Failed to collect artifact {file_path}: {e}")
        
        return artifacts
    
    async def _execute_container_streaming(
        self, 
        container_config: Dict,
        agent_type: str,
        operation_id: str,
        task_store
    ) -> Dict[str, Any]:
        """
        Execute container with real-time log streaming.
        
        This method:
        1. Starts the container
        2. Streams logs in real-time to task store
        3. Monitors container status for completion
        4. Processes results when done
        """
        
        def create_and_start_container():
            """Create and start container synchronously."""
            try:
                container = self.docker_client.containers.create(**container_config)
                container.start()
                return container, None
            except Exception as e:
                logger.error(f"[DOCKER-{agent_type}] Failed to start container: {e}")
                return None, str(e)
        
        # Start container in thread pool
        loop = asyncio.get_event_loop()
        container, error = await loop.run_in_executor(None, create_and_start_container)
        
        if error:
            return {
                "status": "error",
                "summary": f"Failed to start container: {error}",
                "result": {},
                "artifacts": [],
                "logs": [error],
                "stdout": ""
            }
        
        logger.info(f"[DOCKER-{agent_type}] Container started for {operation_id}, streaming logs...")
        
        # Run log streaming and status monitoring in parallel
        try:
            stream_task = asyncio.create_task(
                self._stream_container_logs(container, agent_type, operation_id, task_store)
            )
            monitor_task = asyncio.create_task(
                self._monitor_container_status(container, agent_type, operation_id)
            )
            
            # Wait for both tasks
            logs_result, status_result = await asyncio.gather(stream_task, monitor_task)
            
            # Combine results
            stdout = logs_result.get("stdout", "")
            exit_code = status_result.get("exit_code", -1)
            
            # Clean up container (keep failed containers for debugging)
            try:
                if exit_code == 0:
                    await loop.run_in_executor(None, container.remove)
                    logger.debug(f"[DOCKER-{agent_type}] Container cleaned up")
                else:
                    logger.warning(f"[DOCKER-{agent_type}] Keeping failed container for debugging: {container.name}")
            except:
                pass  # Ignore cleanup errors
            
            # Parse and return results
            parsed_json = self._parse_agent_result(stdout)
            has_sentinel = SENTINEL in stdout
            
            # Extract clean logs from stdout
            clean_logs = self._extract_logs_from_stdout(stdout)
            
            # Log stdout for debugging failed containers
            if exit_code != 0:
                logger.error(f"[DOCKER-{agent_type}] Container failed with exit code {exit_code}")
                logger.error(f"[DOCKER-{agent_type}] Stdout (first 500 chars): {stdout[:500]}")
                if exit_code != -1:
                    clean_logs.append(f"Process exited with code: {exit_code}")
            
            # Check for error patterns like the non-streaming version
            error_patterns = [
                "error:", "exception:", "traceback:", "failed:", 
                "permission denied", "not found", "syntax error"
            ]
            has_error_pattern = any(
                pattern in stdout.lower() 
                for pattern in error_patterns
            )
            
            if parsed_json:
                status = parsed_json.get("status", "ok")
                summary = parsed_json.get("summary", "Agent completed successfully")
            elif has_sentinel and not has_error_pattern:
                status = "ok"
                summary = "Agent completed successfully"
            elif exit_code == 0 and not has_error_pattern:
                status = "ok"
                summary = "Agent completed successfully"
            elif has_error_pattern:
                status = "error"
                summary = "Agent encountered errors during execution"
            else:
                status = "error"
                summary = f"Process exited with code {exit_code}"
            
            return {
                "status": status,
                "summary": summary,
                "result": parsed_json.get("result", {}) if parsed_json else {},
                "artifacts": [],  # Will be populated by caller
                "logs": clean_logs,  # Clean logs extracted from stdout
                "stdout": stdout
            }
            
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            logger.warning(f"[DOCKER-{agent_type}] Task cancelled, stopping container")
            try:
                await loop.run_in_executor(None, container.kill)
                await loop.run_in_executor(None, container.remove)
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"[DOCKER-{agent_type}] Streaming execution failed: {e}")
            # Try to clean up container
            try:
                await loop.run_in_executor(None, lambda: container.remove(force=True))
            except:
                pass
            return {
                "status": "error",
                "summary": f"Container execution failed: {str(e)[:100]}",
                "result": {},
                "artifacts": [],
                "logs": [str(e)],
                "stdout": ""
            }
    
    async def _stream_container_logs(
        self,
        container,
        agent_type: str,
        operation_id: str,
        task_store
    ) -> Dict[str, Any]:
        """
        Collect logs from container periodically and update task store.
        
        Returns dict with stdout collected.
        """
        loop = asyncio.get_event_loop()
        
        try:
            # Periodically collect logs while container is running
            all_logs = ""
            last_log_size = 0
            
            while True:
                # Check container status
                def check_container():
                    try:
                        container.reload()
                        return container.status, container.logs(stdout=True, stderr=True).decode('utf-8', errors='ignore')
                    except Exception as e:
                        logger.warning(f"[DOCKER-{agent_type}] Error checking container: {e}")
                        return 'error', all_logs
                
                status, current_logs = await loop.run_in_executor(None, check_container)
                
                # If we have new logs, process them
                if len(current_logs) > last_log_size:
                    new_content = current_logs[last_log_size:]
                    
                    # Log new content (may be one line or multiple)
                    # Just log what we get without trying to be clever
                    if new_content.strip():
                        logger.info(f"[DOCKER-{agent_type}] {new_content.strip()}")
                    
                    # Update task store with new content
                    if new_content.strip():
                        await task_store.append_logs(operation_id, new_content.splitlines())
                    
                    all_logs = current_logs
                    last_log_size = len(current_logs)
                
                # If container has exited, we're done
                if status in ['exited', 'dead']:
                    break
                
                # Check for sentinel to stop early
                if SENTINEL in all_logs:
                    break
                
                # Wait before next check
                await asyncio.sleep(2)
            
            return {"stdout": all_logs}
            
        except Exception as e:
            logger.error(f"[DOCKER-{agent_type}] Error collecting logs: {e}")
            return {"stdout": "", "error": str(e)}
    
    async def _monitor_container_status(
        self,
        container,
        agent_type: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """
        Monitor container status for completion or timeout.
        
        Returns dict with exit_code and any errors.
        """
        loop = asyncio.get_event_loop()
        start_time = time.time()
        
        while True:
            # Check container status in thread pool
            def check_status():
                try:
                    container.reload()
                    return container.status, container.attrs.get('State', {})
                except Exception as e:
                    logger.warning(f"[DOCKER-{agent_type}] Error checking status: {e}")
                    return 'error', {}
            
            status, state = await loop.run_in_executor(None, check_status)
            
            # Check if container has exited
            if status in ['exited', 'dead']:
                exit_code = state.get('ExitCode', -1)
                logger.info(f"[DOCKER-{agent_type}] Container exited with code {exit_code}")
                return {"exit_code": exit_code}
            
            # Check for timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout_sec:
                logger.warning(f"[DOCKER-{agent_type}] Container timeout after {elapsed:.1f}s, killing")
                try:
                    await loop.run_in_executor(None, container.kill)
                except:
                    pass
                return {"exit_code": -1, "error": "Execution timeout"}
            
            # Check status every second
            await asyncio.sleep(1)
    
    def cleanup(self):
        """Cleanup Docker resources."""
        try:
            self.docker_client.close()
            logger.debug("Docker client closed")
        except Exception as e:
            logger.warning(f"Error closing Docker client: {e}")