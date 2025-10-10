"""
Base agent provider with Docker-based secure execution.

Provides abstract base class for headless AI agent providers that execute
operations in sandboxed environments. Handles async execution, task state
management, and artifact storage.
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
from domain.operation_context import OperationContext
from services.task_store import TaskStatus, get_task_store
from services.agent_runtime_factory import create_agent_runner

logger = logging.getLogger(__name__)

# Sentinel to mark agent completion
SENTINEL = "__AGENT_DONE__"


class BaseAgentProvider(BaseCompute, ABC):
    """
    Base class for AI agent compute providers with sandboxed execution.

    Experimental: Agent providers are under active development and may change.

    Manages the full lifecycle of agent operations from execution to artifact
    storage. Agents run in isolated Docker containers or processes with
    configurable network access and resource limits.

    Subclasses must implement:
        - get_cli_command(): Return the agent CLI executable name
        - get_cli_args(): Build command-line arguments for the agent

    Attributes:
        CLI_NAME: Agent executable name (override in subclass)
        AGENT_TYPE: Agent type identifier for logging (override in subclass)
        REQUIRES_NETWORK: Whether agent needs external API access (default: False)
        timeout_sec: Maximum agent execution time in seconds (default: 180)
        max_stdout_bytes: Maximum captured output size (default: 2MB)

    Configuration:
        - Uses centralized TaskStore for operation state tracking
        - Supports Docker (production) or process-based (testing) execution
        - Artifacts are encrypted and stored per-operation
        - Network isolation enforced by default for security

    Note:
        Agents execute in single-shot batch mode with no user interaction.
        They must complete fully or fail - no streaming or checkpointing.
    """

    # Subclasses should override these
    CLI_NAME = "agent"
    AGENT_TYPE = "base"
    REQUIRES_NETWORK = False  # Set to True for agents that need API access
    
    def __init__(self, task_store=None, artifact_storage=None, agent_runner=None):
        """
        Initialize with injected dependencies.
        
        Args:
            task_store: Task storage service (uses global if not provided)
            artifact_storage: Artifact storage service (lazy loaded if not provided)
            agent_runner: Agent runner (Docker or Process, lazy loaded if not provided)
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
        self._agent_runner = agent_runner
    
    @property
    def artifact_storage(self):
        """Lazy load artifact storage to avoid circular imports."""
        if self._artifact_storage is None:
            from services.artifact_storage import ArtifactStorageService
            self._artifact_storage = ArtifactStorageService()
        return self._artifact_storage
    
    @property
    def agent_runner(self):
        """Lazy load agent runner (Docker or Process) based on configuration."""
        if self._agent_runner is None:
            self._agent_runner = create_agent_runner()
            
            # Set network requirement for Docker runners
            if hasattr(self._agent_runner, 'allow_network'):
                self._agent_runner.allow_network = self.REQUIRES_NETWORK
        
        return self._agent_runner
    
    @abstractmethod
    def get_cli_command(self) -> str:
        """
        Get the agent CLI executable name.

        Returns:
            CLI command string (e.g., "qwen-agent", "gemini-agent")

        Note:
            Must be implemented by subclasses to specify the agent binary.
        """
        pass

    @abstractmethod
    def get_cli_args(self, prompt: str) -> List[str]:
        """
        Build command-line arguments for agent execution.

        Args:
            prompt: Formatted prompt with goal and file information

        Returns:
            List of CLI arguments to pass to the agent command

        Note:
            Must be implemented by subclasses. Should include model configuration,
            output settings, and the prompt itself.
        """
        pass

    def get_env_overrides(self) -> Dict[str, str]:
        """
        Get environment variables for agent authentication.

        Returns:
            Dictionary of environment variable names to values (e.g., API keys)

        Note:
            Override in subclasses that require API authentication.
            Default implementation returns empty dict for offline agents.
        """
        return {}
    
    def build_prompt(self, goal: str, files_dict: Dict[str, bytes] = None, deadline_unix: float = None) -> str:
        """
        Construct formatted prompt for batch agent execution.

        Builds a comprehensive prompt that includes:
        - Batch mode instructions (no interactivity)
        - Available data file listing with sizes
        - Output directory requirements (./out/)
        - JSON result format specification
        - Completion sentinel marker

        Args:
            goal: User's objective for the agent to accomplish
            files_dict: Optional dict mapping filenames to file contents

        Returns:
            Formatted multi-line prompt string ready for agent execution

        Note:
            Agents must print a JSON summary line followed by SENTINEL marker
            to indicate completion. Output format:
            {"status":"ok|error","summary":"...","artifacts":["./out/..."]}
        """
        files_info = ""
        if files_dict:
            files_list = []
            for filename, content in files_dict.items():
                size_kb = len(content) / 1024
                files_list.append(f"  - {filename} ({size_kb:.1f}KB)")
            files_info = f"\n\nAVAILABLE DATA FILES:\n" + "\n".join(files_list) + "\n"

        deadline_info = ""
        if deadline_unix:
            from datetime import datetime
            deadline_dt = datetime.fromtimestamp(deadline_unix)
            deadline_info = (
                f"\n\nTIME LIMIT:\n"
                f"- You must complete by Unix timestamp {deadline_unix:.0f} ({deadline_dt.strftime('%Y-%m-%d %H:%M:%S')})\n"
                f"- Monitor system time (date +%s) to track progress\n"
                f"- If approaching deadline, output partial results rather than incomplete work\n"
            )

        return (
            f"You are running in a headless, single-shot batch mode. "
            f"Work only inside the current directory.{files_info}{deadline_info}\n"
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
    
    async def execute(self, grant_file: GrantFile, files_content: list[str], context: OperationContext) -> ExecuteResponse:
        """
        Start an agentic task asynchronously.
        
        Args:
            grant_file: Grant containing operation parameters
            files_content: List of decrypted file contents
            context: Operation context with grantor/grantee information
            
        Returns:
            ExecuteResponse with operation ID (task runs in background)
        """
        goal = grant_file.parameters.get("goal")
        if not goal or not isinstance(goal, str):
            raise ValueError(f"{self.AGENT_TYPE} operation requires 'goal' parameter")
        
        # Use operation ID from context
        operation_id = context.operation_id
        created_at = datetime.utcnow().isoformat() + "Z"
        
        # Convert files to workspace format
        files_dict = self._prepare_files(files_content)
        
        # Create task entry
        await self._task_store.create_task(operation_id)
        
        # Start background task
        task = asyncio.create_task(
            self._run_agent_async(operation_id, goal, files_dict, context)
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
            result_dict = result_with_logs
        else:
            # Include logs even when no result yet
            result_dict = {
                "status": task_info.status.value,
                "summary": f"Task is {task_info.status.value}",
                "result": {},
                "artifacts": [],
                "logs": task_info.logs[-100:],  # Last 100 lines
                "log_count": len(task_info.logs),
                "truncated": task_info.truncated
            }
        
        return GetResponse(
            id=prediction_id,
            status=api_status,
            started_at=task_info.started_at.isoformat() + "Z" if task_info.started_at else None,
            finished_at=task_info.completed_at.isoformat() + "Z" if task_info.completed_at else None,
            result=result_dict
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
        """Return API-compatible status value.

        TaskStatus enum values now match API schema directly.
        """
        return status.value
    
    async def _run_agent_async(
        self, 
        operation_id: str, 
        goal: str, 
        files_dict: Dict[str, bytes],
        context: OperationContext
    ):
        """
        Run the agent in a background task.
        This is the core execution logic, now with clean separation.
        """
        try:
            # Update status to running
            await self._task_store.update_status(operation_id, TaskStatus.RUNNING)

            # Calculate deadline (80% of timeout to give agent time to wrap up)
            start_time = time.time()
            deadline_unix = start_time + (self.timeout_sec * 0.8)

            # Create workspace
            with tempfile.TemporaryDirectory() as workspace:
                # Stage files
                for filename, content in files_dict.items():
                    filepath = os.path.join(workspace, filename)
                    with open(filepath, 'wb') as f:
                        f.write(content)

                # Build prompt with deadline
                prompt = self.build_prompt(goal, files_dict, deadline_unix=deadline_unix)
                
                # Get CLI command and args
                command = self.get_cli_command()
                args = self.get_cli_args(prompt)
                
                # Execute agent
                result = await self._execute_cli(
                    command, args, workspace, operation_id, prompt
                )
                
                # Process artifacts
                artifacts = await self._process_artifacts(
                    workspace, operation_id, context, result
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
        
        # Both Gemini and Qwen use -p flag for non-interactive prompt mode
        # No stdin needed since prompt is passed as argument
        stdin_input = None
        logger.info(f"[{self.AGENT_TYPE}] Using -p flag for non-interactive prompt mode (length: {len(prompt) if prompt else 0})")
        
        # Execute agent with appropriate runner (Docker or Process)
        result = await self.agent_runner.execute_agent(
            agent_type=self.AGENT_TYPE,
            command=command,
            args=args,
            workspace_files=workspace_files,
            env_vars=env_vars,
            operation_id=operation_id,
            task_store=self._task_store,  # Enable streaming logs
            stdin_input=stdin_input  # No stdin needed, using -p flag
        )
        
        return result
    
    
    async def _process_artifacts(
        self,
        workspace: str,
        operation_id: str,
        context: OperationContext,
        result: Dict
    ) -> List[Dict]:
        """Process and store artifacts from Docker agent execution."""
        import mimetypes

        artifacts_metadata = []

        # Docker runner already collected artifacts and included them in result
        artifacts = result.get("artifacts", [])

        # Collect all artifacts to store in a single batch
        artifacts_to_store = []

        for artifact in artifacts:
            content = artifact.get("content")
            filename = artifact.get("name")

            if content and filename:
                artifacts_to_store.append({
                    "name": filename,
                    "content": content
                })

                # Strip ./out/ prefix from path if present
                clean_path = filename
                if clean_path.startswith("./out/"):
                    clean_path = clean_path[6:]  # Remove "./out/"
                elif clean_path.startswith("out/"):
                    clean_path = clean_path[4:]  # Remove "out/"

                # Determine content type using mimetypes library
                content_type, _ = mimetypes.guess_type(clean_path)
                if not content_type:
                    content_type = "application/octet-stream"  # Default for unknown types

                # Calculate size from actual content
                size = len(content) if isinstance(content, bytes) else len(content.encode('utf-8'))

                # Add structured metadata for API response
                artifacts_metadata.append({
                    "path": clean_path,
                    "size": size,
                    "content_type": content_type
                })

        # Store all artifacts at once with a single encryption key
        if artifacts_to_store:
            await self.artifact_storage.store_artifacts(
                operation_id=operation_id,
                artifacts=artifacts_to_store,
                grantor_address=context.grantor,
                grantee_address=context.grantee
            )

        return artifacts_metadata