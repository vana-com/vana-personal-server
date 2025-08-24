"""
Refactored base agent provider with clean separation of concerns.
Uses centralized task store instead of shared class variables.
"""
import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pexpect

from compute.base import BaseCompute, ExecuteResponse, GetResponse
from domain.entities import GrantFile
from services.task_store import TaskStatus, get_task_store

logger = logging.getLogger(__name__)

# Sentinel to mark agent completion
SENTINEL = "__AGENT_DONE__"
JSON_LINE_RE = re.compile(r'^\s*\{.*\}\s*$')

def _redact_sensitive_data(text: str, api_key: str = None) -> str:
    """Redact API keys from output."""
    if api_key and len(api_key) > 8:
        # Redact all but first 4 chars
        text = text.replace(api_key, api_key[:4] + "[REDACTED]")
    return text


class BaseAgentProvider(BaseCompute, ABC):
    """
    Refactored base class for headless agent providers.
    Uses dependency injection and centralized state management.
    """
    
    # Subclasses should override these
    CLI_NAME = "agent"
    AGENT_TYPE = "base"
    
    def __init__(self, task_store=None, artifact_storage=None):
        """
        Initialize with injected dependencies.
        
        Args:
            task_store: Task storage service (uses global if not provided)
            artifact_storage: Artifact storage service (lazy loaded if not provided)
        """
        # Configuration (subclasses should set these)
        self.settings = None
        self.api_key = None
        self.timeout_sec = 180
        self.max_stdout_bytes = 2_000_000
        self.cli_path = None
        self.use_api_auth = False
        
        # Injected dependencies
        self._task_store = task_store or get_task_store()
        self._artifact_storage = artifact_storage
    
    @property
    def artifact_storage(self):
        """Lazy load artifact storage to avoid circular imports."""
        if self._artifact_storage is None:
            from services.artifact_storage import ArtifactStorageService
            self._artifact_storage = ArtifactStorageService()
        return self._artifact_storage
    
    @abstractmethod
    def get_cli_command(self) -> str:
        """Get the CLI command to execute."""
        pass
    
    @abstractmethod
    def get_cli_args(self, prompt: str) -> List[str]:
        """Get CLI arguments for the specific agent."""
        pass
    
    def get_env_overrides(self) -> Dict[str, str]:
        """Get environment variable overrides for API authentication."""
        return {}
    
    def build_prompt(self, goal: str, files_dict: Dict[str, bytes] = None) -> str:
        """Build the prompt for the agent."""
        files_info = ""
        if files_dict:
            files_list = []
            for filename, content in files_dict.items():
                size_kb = len(content) / 1024
                files_list.append(f"  - {filename} ({size_kb:.1f}KB)")
            files_info = f"\n\nAVAILABLE DATA FILES:\n" + "\n".join(files_list) + "\n"
        
        return (
            f"You are running in a headless, single-shot batch mode. "
            f"Work only inside the current directory.{files_info}\n"
            f"IMPORTANT: Read and analyze the available data files to complete your task.\n"
            f"Generate output files in ./out/ directory.\n\n"
            f"CONSTRAINTS:\n"
            f"- No follow-up questions. Assume sensible defaults.\n"
            f"- Create ./out/ directory if needed.\n"
            f"- Save work products to ./out/.\n"
            f"- At completion, print exactly one JSON line describing results:\n"
            f'  {{"status":"ok|error","summary":"<one line>","artifacts":["./out/..."],"notes":"<optional>"}}\n'
            f"- Then print exactly: {SENTINEL}\n\n"
            f"GOAL:\n{goal}\n"
        )
    
    async def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        """
        Start an agentic task asynchronously.
        
        Args:
            grant_file: Grant containing operation parameters
            files_content: List of decrypted file contents
            
        Returns:
            ExecuteResponse with operation ID (task runs in background)
        """
        goal = grant_file.parameters.get("goal")
        if not goal or not isinstance(goal, str):
            raise ValueError(f"{self.AGENT_TYPE} operation requires 'goal' parameter")
        
        # Generate operation ID
        operation_id = f"{self.AGENT_TYPE}_{int(time.time() * 1000)}"
        created_at = datetime.utcnow().isoformat() + "Z"
        
        # Convert files to workspace format
        files_dict = self._prepare_files(files_content)
        
        # Create task entry
        await self._task_store.create_task(operation_id)
        
        # Start background task
        task = asyncio.create_task(
            self._run_agent_async(operation_id, goal, files_dict, grant_file.grantee)
        )
        
        # Store task reference
        await self._task_store.set_async_task(operation_id, task)
        
        logger.info(f"[{self.AGENT_TYPE}] Task started: {operation_id}")
        
        return ExecuteResponse(id=operation_id, created_at=created_at)
    
    async def get(self, prediction_id: str) -> GetResponse:
        """Get task status and results."""
        task_info = await self._task_store.get_task(prediction_id)
        
        if not task_info:
            raise ValueError(f"Operation {prediction_id} not found")
        
        # Map internal status to API status
        api_status = self._map_status(task_info.status)
        
        # Format result
        if task_info.result:
            result_str = json.dumps(task_info.result, indent=2)
        else:
            result_str = json.dumps({
                "status": task_info.status.value,
                "summary": f"Task is {task_info.status.value}",
                "result": {},
                "artifacts": [],
                "logs": []
            }, indent=2)
        
        return GetResponse(
            id=prediction_id,
            status=api_status,
            started_at=task_info.started_at.isoformat() + "Z" if task_info.started_at else None,
            finished_at=task_info.completed_at.isoformat() + "Z" if task_info.completed_at else None,
            result=result_str
        )
    
    async def cancel(self, prediction_id: str) -> bool:
        """Cancel a running task."""
        success = await self._task_store.cancel_task(prediction_id)
        if success:
            logger.info(f"[{self.AGENT_TYPE}] Cancelled task: {prediction_id}")
        return success
    
    def _prepare_files(self, files_content: list[str]) -> Dict[str, bytes]:
        """Convert file contents to workspace format with descriptive names."""
        files_dict = {}
        for i, content in enumerate(files_content):
            # Determine filename based on content
            if "chatgpt" in content.lower():
                filename = f"chatgpt_conversations_{i:02d}.txt"
            elif "spotify" in content.lower():
                filename = f"spotify_data_{i:02d}.json"
            elif "linkedin" in content.lower():
                filename = f"linkedin_profile_{i:02d}.json"
            else:
                filename = f"user_data_{i:02d}.txt"
            
            files_dict[filename] = content.encode('utf-8')
        
        return files_dict
    
    def _map_status(self, status: TaskStatus) -> str:
        """Map internal status to API status."""
        mapping = {
            TaskStatus.PENDING: "pending",
            TaskStatus.RUNNING: "running",
            TaskStatus.SUCCEEDED: "succeeded",
            TaskStatus.FAILED: "failed",
            TaskStatus.CANCELLED: "cancelled"
        }
        return mapping.get(status, "failed")
    
    async def _run_agent_async(
        self, 
        operation_id: str, 
        goal: str, 
        files_dict: Dict[str, bytes],
        grantee_address: str
    ):
        """
        Run the agent in a background task.
        This is the core execution logic, now with clean separation.
        """
        try:
            # Update status to running
            await self._task_store.update_status(operation_id, TaskStatus.RUNNING)
            
            # Create workspace
            with tempfile.TemporaryDirectory() as workspace:
                # Stage files
                for filename, content in files_dict.items():
                    filepath = os.path.join(workspace, filename)
                    with open(filepath, 'wb') as f:
                        f.write(content)
                
                # Build prompt
                prompt = self.build_prompt(goal, files_dict)
                
                # Get CLI command and args
                command = self.get_cli_command()
                args = self.get_cli_args(prompt)
                
                # Execute agent
                result = await self._execute_cli(
                    command, args, workspace, operation_id
                )
                
                # Process artifacts
                artifacts = await self._process_artifacts(
                    workspace, operation_id, grantee_address, result
                )
                
                # Update result with artifact metadata
                result["artifacts"] = artifacts
                
                # Store result
                status = TaskStatus.SUCCEEDED if result.get("status") == "ok" else TaskStatus.FAILED
                await self._task_store.update_status(
                    operation_id, status, result=result
                )
                
                logger.info(f"[{self.AGENT_TYPE}] Task completed: {operation_id}")
                
        except Exception as e:
            logger.error(f"[{self.AGENT_TYPE}] Task failed: {operation_id}: {e}")
            await self._task_store.update_status(
                operation_id, 
                TaskStatus.FAILED,
                error=str(e)
            )
    
    async def _execute_cli(
        self, 
        command: str, 
        args: List[str], 
        workspace: str,
        operation_id: str
    ) -> Dict:
        """Execute CLI command and capture output."""
        # Run synchronously in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._run_cli_sync,
            command, args, workspace, operation_id
        )
    
    def _run_cli_sync(
        self,
        command: str,
        args: List[str],
        workspace: str,
        operation_id: str
    ) -> Dict[str, Any]:
        """Synchronous CLI execution with pexpect."""
        t0 = time.time()
        workspace_path = Path(workspace)
        
        # Setup environment
        env = os.environ.copy()
        env["CI"] = "1"
        env["NO_COLOR"] = "1"
        env.update(self.get_env_overrides())
        
        child = None
        captured = bytearray()
        logs = []
        artifacts = []
        parsed_json = None
        
        try:
            logger.info(f"[{self.AGENT_TYPE}] Spawning {command} in {workspace}")
            
            child = pexpect.spawn(
                command,
                args=args,
                cwd=workspace,
                env=env,
                encoding="utf-8",
                timeout=self.timeout_sec,
            )
            
            # Read output until sentinel or timeout
            last_log = time.time()
            while True:
                try:
                    chunk = child.read_nonblocking(size=4096, timeout=5)
                except pexpect.TIMEOUT:
                    elapsed = time.time() - t0
                    if elapsed > self.timeout_sec:
                        logs.append(f"Timeout after {self.timeout_sec}s")
                        break
                    if time.time() - last_log > 10:
                        logger.info(f"[{self.AGENT_TYPE}] Still running... ({elapsed:.1f}s)")
                        last_log = time.time()
                    continue
                except pexpect.EOF:
                    logger.info(f"[{self.AGENT_TYPE}] Process completed")
                    break
                else:
                    captured.extend(chunk.encode("utf-8", errors="ignore"))
                    if len(captured) >= self.max_stdout_bytes:
                        logs.append("Max output size reached")
                        break
                    if SENTINEL in chunk:
                        logger.info(f"[{self.AGENT_TYPE}] Found completion sentinel")
                        break
            
            # Terminate process
            if child and child.isalive():
                child.terminate(force=True)
            if child:
                child.close(force=True)
            
            # Process output
            stdout_text = captured.decode("utf-8", errors="ignore")
            stdout_text = _redact_sensitive_data(stdout_text, self.api_key)
            
            logs.append(f"Execution time: {time.time() - t0:.2f}s")
            
            # Parse JSON result
            for line in reversed(stdout_text.splitlines()):
                if JSON_LINE_RE.match(line.strip()):
                    try:
                        parsed_json = json.loads(line.strip())
                        logger.info(f"[{self.AGENT_TYPE}] Parsed JSON result")
                        break
                    except json.JSONDecodeError:
                        pass
            
            # Collect artifacts
            if parsed_json and isinstance(parsed_json.get("artifacts"), list):
                for rel_path in parsed_json["artifacts"]:
                    artifact_path = (workspace_path / rel_path).resolve()
                    try:
                        artifact_path.relative_to(workspace_path)  # Security check
                        if artifact_path.is_file():
                            artifacts.append({
                                "name": str(Path(rel_path)),
                                "content": artifact_path.read_bytes(),
                            })
                            logger.info(f"[{self.AGENT_TYPE}] Collected artifact: {rel_path}")
                    except (ValueError, FileNotFoundError) as e:
                        logs.append(f"Artifact error: {rel_path}: {e}")
            
            # Determine status
            has_sentinel = SENTINEL in stdout_text
            status = (parsed_json or {}).get("status", "ok" if has_sentinel else "error")
            summary = (parsed_json or {}).get("summary", "Task completed" if status == "ok" else "Task failed")
            
            return {
                "status": status,
                "summary": summary,
                "result": parsed_json or {},
                "artifacts": artifacts,
                "logs": logs,
                "stdout": stdout_text[:10000] if len(stdout_text) > 10000 else stdout_text  # Limit for storage
            }
            
        except Exception as e:
            logger.error(f"[{self.AGENT_TYPE}] Execution failed: {e}")
            return {
                "status": "error",
                "summary": f"Execution failed: {type(e).__name__}",
                "result": {},
                "artifacts": [],
                "logs": logs + [str(e)],
                "stdout": ""
            }
    
    async def _process_artifacts(
        self, 
        workspace: str, 
        operation_id: str,
        grantee_address: str,
        result: Dict
    ) -> List[Dict]:
        """Process and store artifacts from agent execution."""
        artifacts_metadata = []
        
        out_dir = os.path.join(workspace, "out")
        if os.path.exists(out_dir):
            for filename in os.listdir(out_dir):
                filepath = os.path.join(out_dir, filename)
                if os.path.isfile(filepath):
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    
                    # Store in artifact storage
                    await self.artifact_storage.store_artifact(
                        operation_id, filename, content, grantee_address
                    )
                    
                    # Add metadata
                    artifacts_metadata.append({
                        "name": filename,
                        "size": len(content),
                        "artifact_path": f"out/{filename}"
                    })
        
        return artifacts_metadata