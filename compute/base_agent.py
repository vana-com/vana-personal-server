"""
Refactored base agent provider with clean separation of concerns.
Uses centralized task store and Docker-based secure execution.
"""
import asyncio
import json
import logging
import os
import tempfile
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from compute.base import BaseCompute, ExecuteResponse, GetResponse
from domain.entities import GrantFile
from services.task_store import TaskStatus, get_task_store
from services.agent_runner import DockerAgentRunner

logger = logging.getLogger(__name__)

# Sentinel to mark agent completion
SENTINEL = "__AGENT_DONE__"


class BaseAgentProvider(BaseCompute, ABC):
    """
    Refactored base class for headless agent providers.
    Uses dependency injection and centralized state management.
    """
    
    # Subclasses should override these
    CLI_NAME = "agent"
    AGENT_TYPE = "base"
    REQUIRES_NETWORK = False  # Set to True for agents that need API access
    
    def __init__(self, task_store=None, artifact_storage=None, docker_runner=None):
        """
        Initialize with injected dependencies.
        
        Args:
            task_store: Task storage service (uses global if not provided)
            artifact_storage: Artifact storage service (lazy loaded if not provided)
            docker_runner: Docker agent runner (lazy loaded if not provided)
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
        self._docker_runner = docker_runner
    
    @property
    def artifact_storage(self):
        """Lazy load artifact storage to avoid circular imports."""
        if self._artifact_storage is None:
            from services.artifact_storage import ArtifactStorageService
            self._artifact_storage = ArtifactStorageService()
        return self._artifact_storage
    
    @property
    def docker_runner(self):
        """Lazy load Docker agent runner with configuration from settings."""
        if self._docker_runner is None:
            from settings import get_settings
            settings = get_settings()
            
            self._docker_runner = DockerAgentRunner(
                image_name=settings.docker_agent_image,
                memory_limit=settings.docker_agent_memory_limit,
                timeout_sec=settings.docker_agent_timeout_sec,
                max_output_bytes=settings.docker_agent_max_output_mb * 1_000_000,
                cpu_limit=settings.docker_agent_cpu_limit or "1.0",
                allow_network=self.REQUIRES_NETWORK  # Pass network requirement
            )
        return self._docker_runner
    
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
        """Get task status and results with accumulated logs."""
        task_info = await self._task_store.get_task(prediction_id)
        
        if not task_info:
            raise ValueError(f"Operation {prediction_id} not found")
        
        # Map internal status to API status
        api_status = self._map_status(task_info.status)
        
        # Format result with logs included
        if task_info.result:
            # Include logs in existing result
            result_with_logs = dict(task_info.result)
            result_with_logs["logs"] = task_info.logs[-100:]  # Last 100 lines
            result_with_logs["log_count"] = len(task_info.logs)
            result_with_logs["truncated"] = task_info.truncated
            result_str = json.dumps(result_with_logs, indent=2)
        else:
            # Include logs even when no result yet
            result_str = json.dumps({
                "status": task_info.status.value,
                "summary": f"Task is {task_info.status.value}",
                "result": {},
                "artifacts": [],
                "logs": task_info.logs[-100:],  # Last 100 lines
                "log_count": len(task_info.logs),
                "truncated": task_info.truncated
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
                    command, args, workspace, operation_id, prompt
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
        operation_id: str,
        prompt: str = None
    ) -> Dict:
        """Execute CLI command in secure Docker container."""
        # Convert workspace files to the format expected by Docker runner
        workspace_path = Path(workspace)
        workspace_files = {}
        
        # Load all files in workspace for Docker mounting
        for file_path in workspace_path.iterdir():
            if file_path.is_file():
                workspace_files[file_path.name] = file_path.read_bytes()
        
        # Get environment variables for the agent
        env_vars = self.get_env_overrides()
        
        # Determine if we should use stdin for the prompt
        # Gemini CLI works better with stdin for long prompts
        stdin_input = None
        if self.AGENT_TYPE == "gemini" and prompt:
            stdin_input = prompt
            logger.info(f"[{self.AGENT_TYPE}] Using stdin for prompt (length: {len(prompt)})")
        else:
            logger.info(f"[{self.AGENT_TYPE}] Not using stdin (agent_type={self.AGENT_TYPE}, has_prompt={bool(prompt)})")
        
        # Execute in Docker container with streaming
        result = await self.docker_runner.execute_agent(
            agent_type=self.AGENT_TYPE,
            command=command,
            args=args,
            workspace_files=workspace_files,
            env_vars=env_vars,
            operation_id=operation_id,
            task_store=self._task_store,  # Enable streaming logs
            stdin_input=stdin_input  # Pass prompt via stdin if needed
        )
        
        return result
    
    
    async def _process_artifacts(
        self, 
        workspace: str, 
        operation_id: str,
        grantee_address: str,
        result: Dict
    ) -> List[Dict]:
        """Process and store artifacts from Docker agent execution."""
        artifacts_metadata = []
        
        # Docker runner already collected artifacts and included them in result
        artifacts = result.get("artifacts", [])
        
        for artifact in artifacts:
            content = artifact.get("content")
            filename = artifact.get("name")
            
            if content and filename:
                # Store in artifact storage
                await self.artifact_storage.store_artifact(
                    operation_id, filename, content, grantee_address
                )
                
                # Add metadata for result
                artifacts_metadata.append({
                    "name": filename,
                    "size": artifact.get("size", len(content)),
                    "artifact_path": artifact.get("artifact_path", f"out/{filename}")
                })
        
        return artifacts_metadata