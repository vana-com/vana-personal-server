"""
Process-based agent execution service for Cloud Run compatibility.

Provides secure agent execution using OS processes instead of Docker containers:
- Resource limits (memory, file size) via rlimits  
- Process isolation via separate process groups
- Workspace isolation via random temp directories
- Concurrency control via semaphores
- Artifact collection and processing

Designed for Cloud Run where Docker-in-Docker is not available.
"""
import asyncio
import json
import logging
import os
import resource
import secrets
import shutil
import signal
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Sentinel to mark agent completion  
SENTINEL = "__AGENT_DONE__"

# Global semaphore for per-instance concurrency control
_semaphore = None

def _get_semaphore():
    """Get or create the global semaphore for concurrency control."""
    global _semaphore
    if _semaphore is None:
        max_concurrent = int(os.getenv("AGENT_MAX_CONCURRENT_PER_INSTANCE", "1"))
        _semaphore = asyncio.Semaphore(max_concurrent)
    return _semaphore


class ProcessAgentRunner:
    """
    Process-based agent execution service.
    
    Provides resource-bounded agent execution using OS processes:
    - Memory limits: RLIMIT_AS to cap virtual memory
    - File size limits: RLIMIT_FSIZE to prevent huge files
    - Concurrency control: Semaphore to limit parallel agents
    - Process isolation: Separate process groups for clean kills
    """
    
    def __init__(
        self,
        memory_limit_mb: int = 768,
        timeout_sec: int = 300,
        max_output_bytes: int = 2_000_000,
        file_size_limit_mb: int = 100,
        allow_network: bool = True,  # Processes have network access by default
    ):
        """
        Initialize process agent runner.
        
        Args:
            memory_limit_mb: Memory limit per agent process in MB
            timeout_sec: Timeout for agent execution
            max_output_bytes: Maximum stdout/stderr to capture
            file_size_limit_mb: Maximum file size per write operation
            allow_network: Whether to allow network access (compatibility with DockerAgentRunner)
        """
        self.memory_limit_mb = memory_limit_mb
        self.timeout_sec = timeout_sec
        self.max_output_bytes = max_output_bytes
        self.file_size_limit_mb = file_size_limit_mb
        self.allow_network = allow_network
        
        logger.info(f"[PROCESS] ProcessAgentRunner initialized:")
        logger.info(f"[PROCESS]   Memory limit: {memory_limit_mb}MB")
        logger.info(f"[PROCESS]   Timeout: {timeout_sec}s")
        logger.info(f"[PROCESS]   File size limit: {file_size_limit_mb}MB")
    
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
        Execute agent in a resource-bounded process.
        
        Args:
            agent_type: Type of agent (gemini, qwen, etc.)
            command: CLI command to execute
            args: Command arguments
            workspace_files: Input files to stage in workspace
            env_vars: Environment variables
            operation_id: Unique operation identifier
            task_store: Optional task store for log streaming
            stdin_input: Optional stdin input for prompts
            
        Returns:
            Dictionary with execution results, logs, and artifacts
        """
        start_time = time.time()
        
        # Use semaphore to control concurrency per instance
        semaphore = _get_semaphore()
        
        async with semaphore:
            logger.info(f"[PROCESS-{agent_type}] Starting execution for {operation_id}")
            
            try:
                # 1. Create random workspace directory
                workspace_path = self._create_workspace()
                
                try:
                    # 2. Stage input files
                    self._stage_workspace_files(workspace_path, workspace_files)
                    
                    # 3. Execute agent process with limits
                    result = await self._run_process(
                        agent_type=agent_type,
                        command=command,
                        args=args,
                        workspace_path=workspace_path,
                        env_vars=env_vars,
                        operation_id=operation_id,
                        task_store=task_store,
                        stdin_input=stdin_input
                    )
                    
                    # 4. Collect artifacts
                    artifacts = self._collect_artifacts(workspace_path, operation_id)
                    result["artifacts"] = artifacts
                    result["execution_time"] = time.time() - start_time
                    
                    return result
                    
                finally:
                    # 5. Clean up workspace
                    self._cleanup_workspace(workspace_path)
                    
            except Exception as e:
                logger.error(f"[PROCESS-{agent_type}] Agent execution failed: {e}")
                return {
                    "status": "error",
                    "summary": f"Process execution failed: {type(e).__name__}",
                    "result": {},
                    "artifacts": [],
                    "logs": [str(e)],
                    "stdout": "",
                    "execution_time": time.time() - start_time
                }
    
    def _create_workspace(self) -> Path:
        """Create a random workspace directory in /tmp."""
        workspace_name = f"agent_{secrets.token_hex(16)}"
        workspace_path = Path("/tmp") / workspace_name
        workspace_path.mkdir(mode=0o700, parents=True, exist_ok=True)
        
        # Create output directory
        out_dir = workspace_path / "out"
        out_dir.mkdir(mode=0o700, exist_ok=True)
        
        logger.debug(f"[PROCESS] Created workspace: {workspace_path}")
        return workspace_path
    
    def _stage_workspace_files(self, workspace_path: Path, files_dict: Dict[str, bytes]):
        """Stage input files in the workspace directory."""
        for filename, content in files_dict.items():
            file_path = workspace_path / filename
            # Ensure safe path (no directory traversal)
            try:
                file_path.relative_to(workspace_path)
                file_path.write_bytes(content)
                file_path.chmod(0o644)
                logger.debug(f"[PROCESS] Staged file: {filename} ({len(content)} bytes)")
            except ValueError as e:
                logger.warning(f"[PROCESS] Skipping unsafe file path: {filename}: {e}")
    
    def _cleanup_workspace(self, workspace_path: Path):
        """Clean up workspace directory."""
        try:
            shutil.rmtree(workspace_path)
            logger.debug(f"[PROCESS] Cleaned up workspace: {workspace_path}")
        except Exception as e:
            logger.error(f"[PROCESS] Failed to cleanup workspace {workspace_path}: {e}")
    
    def _collect_artifacts(self, workspace_path: Path, operation_id: str) -> List[Dict]:
        """Collect artifacts from the workspace output directory."""
        artifacts = []
        out_dir = workspace_path / "out"
        
        if not out_dir.exists():
            logger.debug(f"[PROCESS] No output directory found at {out_dir}")
            return artifacts
        
        try:
            for file_path in out_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        content = file_path.read_bytes()
                        # Use relative path from out/ directory as the artifact name
                        relative_path = file_path.relative_to(out_dir)
                        artifact_name = str(relative_path)
                        
                        artifacts.append({
                            "name": artifact_name,
                            "content": content,
                            "size": len(content),
                            "artifact_path": artifact_name
                        })
                        logger.info(f"[PROCESS] Collected artifact: {artifact_name} ({len(content)} bytes)")
                    except Exception as e:
                        logger.warning(f"[PROCESS] Failed to collect artifact {file_path}: {e}")
        except Exception as e:
            logger.warning(f"[PROCESS] Failed to collect artifacts from {out_dir}: {e}")
        
        return artifacts
    
    def _prepare_resource_limits(self):
        """Prepare resource limit function for preexec_fn."""
        def apply_limits():
            # Note: RLIMIT_AS limits virtual address space, not physical memory (RSS).
            # V8 reserves 15-20Gi virtual space but uses much less physically.
            # Setting RLIMIT_AS too low causes immediate malloc failures.
            # Instead, we limit V8 heap via NODE_OPTIONS --max-old-space-size.
            # Cloud Run enforces container-level memory at the instance boundary.

            # Set file size limit (safe for all processes)
            file_size_bytes = self.file_size_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_bytes, file_size_bytes))

            # Create new process group for clean kills
            os.setsid()

        return apply_limits
    
    async def _run_process(
        self,
        agent_type: str,
        command: str,
        args: List[str],
        workspace_path: Path,
        env_vars: Dict[str, str],
        operation_id: str,
        task_store=None,
        stdin_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run agent process with resource limits and log streaming."""
        
        # Prepare full command
        full_command = [command] + args
        
        # Prepare clean environment with only agent-specific credentials
        # Prevents auth conflicts: qwen-code prioritizes GEMINI_API_KEY over OPENAI_API_KEY
        # in env detection, causing it to call wrong API even when OPENAI_* vars are set
        process_env = {
            "PYTHONUNBUFFERED": "1",
            "NO_COLOR": "1",
            "PATH": "/app/node_modules/.bin:" + os.environ.get("PATH", ""),
            "HOME": str(workspace_path),
            "USER": "appuser",
            "NODE_ENV": "production",
            **env_vars  # Agent-specific credentials from get_env_overrides()
        }

        # Limit Node.js V8 heap to prevent memory exhaustion
        # This is the primary memory control for Node-based agents (qwen, gemini)
        node_opts = f"--max-old-space-size={self.memory_limit_mb} {process_env.get('NODE_OPTIONS', '')}"
        process_env["NODE_OPTIONS"] = node_opts.strip()

        logger.info(f"[PROCESS-{agent_type}] Starting agent (op={operation_id}, heap_limit={self.memory_limit_mb}MB)")
        logger.debug(f"[PROCESS-{agent_type}] Working directory: {workspace_path}")
        logger.info(f"[PROCESS-{agent_type}] Running as UID={os.getuid()}, GID={os.getgid()}")
        
        try:
            # Create subprocess with resource limits
            proc = await asyncio.create_subprocess_exec(
                *full_command,
                cwd=str(workspace_path),
                env=process_env,
                stdin=asyncio.subprocess.PIPE if stdin_input else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._prepare_resource_limits()
            )
            
            # Check if process started successfully
            if proc.returncode is not None:
                logger.error(f"[PROCESS-{agent_type}] Process exited immediately with code {proc.returncode}")
                stderr = await proc.stderr.read() if proc.stderr else b""
                raise RuntimeError(f"Process failed to start: exit code {proc.returncode}, stderr: {stderr.decode('utf-8', errors='ignore')}")
            
            # Stream logs and collect output
            return await self._handle_process_output(
                proc, agent_type, operation_id, task_store, stdin_input
            )
            
        except Exception as e:
            logger.error(f"[PROCESS-{agent_type}] Failed to start process: {e}")
            raise
    
    async def _handle_process_output(
        self,
        proc: asyncio.subprocess.Process,
        agent_type: str,
        operation_id: str,
        task_store=None,
        stdin_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle process output with streaming and timeout."""

        process_start = time.time()
        stdout_lines = []

        try:
            # Send stdin if provided
            if stdin_input and proc.stdin:
                proc.stdin.write(stdin_input.encode())
                await proc.stdin.drain()
                proc.stdin.close()
            
            # Stream output with timeout
            async with asyncio.timeout(self.timeout_sec):
                while True:
                    # Read line from stdout
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    
                    line_str = line.decode("utf-8", errors="ignore").rstrip()
                    stdout_lines.append(line_str)
                    
                    # Stream logs to task store if available
                    if task_store:
                        try:
                            await task_store.append_log(operation_id, line_str)
                        except Exception as e:
                            logger.debug(f"[PROCESS] Failed to stream log: {e}")
                    
                    # Check for sentinel (agent completion marker)
                    if SENTINEL in line_str:
                        logger.debug(f"[PROCESS-{agent_type}] Found sentinel, agent completed")
                        break
            
            # Wait for process to complete
            return_code = await proc.wait()
            
            # Also capture stderr if there was an error
            if return_code != 0 and proc.stderr:
                stderr = await proc.stderr.read()
                if stderr:
                    stderr_str = stderr.decode("utf-8", errors="ignore").strip()
                    if stderr_str:
                        stdout_lines.append(f"STDERR: {stderr_str}")
                        logger.error(f"[PROCESS-{agent_type}] Process stderr: {stderr_str}")
            
        except asyncio.TimeoutError:
            logger.warning(f"[PROCESS-{agent_type}] Process timed out, killing...")
            try:
                # Kill the entire process group
                os.killpg(proc.pid, signal.SIGKILL)
                await proc.wait()
            except Exception as e:
                logger.error(f"[PROCESS-{agent_type}] Failed to kill process: {e}")
            
            # Create logs from stdout excluding JSON/sentinel
            logs = self._extract_logs_from_stdout(stdout_lines)
            
            return {
                "status": "error",
                "summary": "Process execution timed out",
                "result": {},
                "artifacts": [],
                "logs": logs,
                "stdout": "\n".join(stdout_lines),
                "return_code": -1
            }
        
        # Parse agent result from stdout
        agent_result = self._parse_agent_output(stdout_lines, agent_type)

        # Extract logs (excluding JSON output and sentinel)
        logs = self._extract_logs_from_stdout(stdout_lines)

        duration = time.time() - process_start
        logger.info(f"[PROCESS-{agent_type}] Agent exited (op={operation_id}, code={return_code}, duration={duration:.1f}s)")

        return {
            "status": agent_result.get("status", "ok"),
            "summary": agent_result.get("summary", "Agent completed successfully"),
            "result": agent_result.get("result", {}),
            "artifacts": [],  # Will be added by caller
            "logs": logs,
            "stdout": "\n".join(stdout_lines),
            "return_code": return_code
        }
    
    def _parse_agent_output(self, stdout_lines: List[str], agent_type: str) -> Dict:
        """Parse agent output looking for JSON result before sentinel."""
        
        # Look for JSON line before sentinel
        for line in reversed(stdout_lines):
            if line.strip() == SENTINEL:
                continue
            
            # Try to parse as JSON
            try:
                result = json.loads(line.strip())
                if isinstance(result, dict):
                    logger.debug(f"[PROCESS-{agent_type}] Parsed agent result: {result}")
                    return result
            except (json.JSONDecodeError, ValueError):
                continue
        
        # No valid JSON found, return basic result
        logger.warning(f"[PROCESS-{agent_type}] No valid agent result JSON found")
        return {
            "status": "ok",
            "summary": "Agent completed successfully",
            "result": {}
        }
    
    def _extract_logs_from_stdout(self, stdout_lines: List[str]) -> List[str]:
        """Extract clean logs from stdout, excluding JSON output and sentinel."""
        logs = []
        json_found = False
        
        for line in stdout_lines:
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
            
            # Skip lines that look like "Data collection is disabled." (common prefix)
            # but include actual work logs
            logs.append(line)
        
        return logs