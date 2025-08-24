"""
Base class for CLI-based AI agents (Qwen Code, Gemini CLI, etc).

Provides shared functionality for headless, one-shot agent execution
with a strict sentinel + JSON contract for deterministic results.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pexpect

from compute.base import BaseCompute, ExecuteResponse, GetResponse
from domain.entities import GrantFile

logger = logging.getLogger(__name__)

SENTINEL = "__AGENT_DONE__"
JSON_LINE_RE = re.compile(r'^\s*\{.*\}\s*$')


def _redact_sensitive_data(text: str, api_key: str = None) -> str:
    """Redact sensitive information from logs and outputs."""
    if api_key and api_key in text:
        text = text.replace(api_key, "****REDACTED****")
    return text


class BaseAgentProvider(BaseCompute):
    """
    Base class for CLI-based AI agent providers.
    
    Handles common functionality like:
    - Secure workspace creation and cleanup
    - PTY-based process spawning
    - Output capture and timeout handling
    - Artifact collection
    - JSON response parsing
    """
    
    # Subclasses should override these
    CLI_NAME = "agent"  # Name of the CLI tool (e.g., "qwen", "gemini")
    AGENT_TYPE = "base"  # Type identifier for logging
    
    def __init__(self):
        self.settings = None  # Subclasses should set this
        self.api_key = None
        self.timeout_sec = 180
        self.max_stdout_bytes = 2_000_000
        self.cli_path = None
        self.use_api_auth = False
        
        # Store results and running tasks in memory
        if not hasattr(self.__class__, "_results"):
            self.__class__._results = {}
        if not hasattr(self.__class__, "_tasks"):
            self.__class__._tasks = {}
    
    def get_cli_command(self) -> str:
        """Get the CLI command to execute. Subclasses can override."""
        return self.cli_path or self.CLI_NAME
    
    def get_cli_args(self, prompt: str) -> List[str]:
        """Get CLI arguments. Subclasses should override based on their CLI."""
        return ["-p", prompt]
    
    def get_env_overrides(self) -> Dict[str, str]:
        """Get environment variable overrides for API authentication."""
        return {}
    
    def build_prompt(self, goal: str, files_dict: Dict[str, bytes] = None) -> str:
        """Build the prompt for the agent. Can be overridden by subclasses."""
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
            f"Generate the code/commands needed but don't try to execute them.\n"
            f"Instead, describe what would be done and output the final result.\n\n"
            f"CONSTRAINTS:\n"
            f"- No follow-up questions. Assume sensible defaults.\n"
            f"- Read the provided data files to understand the available information.\n"
            f"- Describe creating the ./out/ directory if needed.\n"
            f"- Describe work products that would go in ./out/.\n"
            f"- At completion, print exactly one JSON line (no backticks) describing results:\n"
            f'  {{"status":"ok|error","summary":"<one line>","artifacts":["./out/..."],"notes":"<optional>"}}\n'
            f"- Then print exactly: {SENTINEL}\n"
            f"- Do not print anything after {SENTINEL}.\n\n"
            f"GOAL:\n{goal}\n"
        )
    
    def execute(self, grant_file: GrantFile, files_content: list[str]) -> ExecuteResponse:
        """
        Start an agentic task using the CLI agent (returns immediately).
        
        Args:
            grant_file: Grant containing operation parameters including 'goal'
            files_content: List of decrypted file contents as strings
        
        Returns:
            ExecuteResponse with operation ID and timestamp (task runs in background)
        """
        goal = grant_file.parameters.get("goal")
        if not goal or not isinstance(goal, str):
            raise ValueError(f"{self.AGENT_TYPE} operation requires 'goal' parameter (string)")

        # Convert file contents to workspace format with descriptive names
        files_dict = {}
        for i, content in enumerate(files_content):
            # Try to determine file type from content
            if "chatgpt" in content.lower() or "conversation history" in content.lower():
                filename = f"chatgpt_conversations_{i:02d}.txt"
            elif "spotify" in content.lower() or "listening_history" in content.lower():
                filename = f"spotify_data_{i:02d}.json"
            elif "linkedin" in content.lower() or "professional" in content.lower():
                filename = f"linkedin_profile_{i:02d}.txt"
            elif "fitness" in content.lower() or "health" in content.lower():
                filename = f"fitness_data_{i:02d}.json"
            else:
                filename = f"personal_data_{i:02d}.txt"
            
            files_dict[filename] = content.encode("utf-8")

        # Create a unique operation ID
        operation_id = f"{self.AGENT_TYPE}_{int(time.time() * 1000)}"
        created_at = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        logger.info(f"[{self.AGENT_TYPE}] Starting task: {operation_id} - {goal[:100]}...")

        # Initialize operation status
        self._results[operation_id] = {
            "status": "running",
            "summary": "Task is running in background",
            "result": {},
            "artifacts": [],
            "logs": [],
            "stdout": "",
        }

        # Start background task
        task = asyncio.create_task(self._run_agent_async(operation_id, goal, files_dict, grant_file.grantee))
        self._tasks[operation_id] = task

        logger.info(f"[{self.AGENT_TYPE}] Task started in background: {operation_id}")

        return ExecuteResponse(
            id=operation_id,
            created_at=created_at
        )

    def get(self, prediction_id: str) -> GetResponse:
        """
        Get results from an agentic task (running or completed).
        """
        if prediction_id not in self._results:
            raise ValueError(f"Operation {prediction_id} not found")

        # Check if task is still running
        if prediction_id in self._tasks:
            task = self._tasks[prediction_id]
            if not task.done():
                # Task still running
                return GetResponse(
                    id=prediction_id,
                    status="running",
                    started_at=None,
                    finished_at=None,
                    result=json.dumps({
                        "status": "running",
                        "summary": "Task is running in background",
                        "result": {},
                        "artifacts": [],
                        "logs": [],
                        "stdout": "",
                    }, indent=2)
                )
            else:
                # Task completed, clean up
                if task.exception():
                    logger.error(f"[{self.AGENT_TYPE}] Task {prediction_id} failed with exception: {task.exception()}")
                del self._tasks[prediction_id]

        result = self._results[prediction_id]
        
        # Create artifact metadata (no content - stored in R2)
        artifacts_metadata = []
        for artifact in result.get("artifacts", []):
            artifacts_metadata.append({
                "name": artifact["name"],
                "size": len(artifact["content"]),
                "download_url": f"/api/v1/artifacts/{prediction_id}/{artifact['name']}"
            })

        # Format result as string for compatibility
        result_str = json.dumps({
            "status": result["status"],
            "summary": result["summary"], 
            "result": result.get("result", {}),
            "artifacts": artifacts_metadata,  # Just metadata, not content
            "logs": result.get("logs", []),
            "stdout": result.get("stdout", ""),  # Include for debugging
        }, indent=2)

        # Map internal status to API status
        if result["status"] == "running":
            api_status = "running"
        elif result["status"] == "ok":
            api_status = "succeeded"
        else:
            api_status = "failed"

        return GetResponse(
            id=prediction_id,
            status=api_status,
            started_at=None,
            finished_at=None,
            result=result_str
        )

    def cancel(self, prediction_id: str) -> bool:
        """Cancel operation - attempts to cancel running task."""
        if prediction_id in self._tasks:
            task = self._tasks[prediction_id]
            if not task.done():
                task.cancel()
                logger.info(f"[{self.AGENT_TYPE}] Cancelled task: {prediction_id}")
                # Update status
                if prediction_id in self._results:
                    self._results[prediction_id].update({
                        "status": "error",
                        "summary": "Task cancelled by user"
                    })
                return True
        return False
    
    async def _run_agent_async(self, operation_id: str, goal: str, files_dict: Dict[str, bytes], grantee_address: str):
        """
        Async wrapper that runs the agent in a background task.
        """
        try:
            logger.info(f"[{self.AGENT_TYPE}] Background task started: {operation_id}")
            
            # Run the synchronous agent execution in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # Use default thread pool
                self._run_agent_headless,
                goal,
                files_dict
            )
            
            # Store artifacts in cloud storage
            try:
                from services.artifact_storage import ArtifactStorageService
                storage_service = ArtifactStorageService()
                
                # Store artifacts if any
                if result.get("artifacts"):
                    await storage_service.store_artifacts(
                        operation_id=operation_id,
                        artifacts=result["artifacts"],
                        grantee_address=grantee_address
                    )
                    logger.info(f"[{self.AGENT_TYPE}] Stored {len(result['artifacts'])} artifacts in cloud storage")
            except Exception as e:
                logger.warning(f"[{self.AGENT_TYPE}] Failed to store artifacts in cloud: {e}")
                result.setdefault("logs", []).append(f"Artifact storage failed: {e}")
            
            # Update results
            self._results[operation_id] = result
            
            logger.info(f"[{self.AGENT_TYPE}] Background task completed: {operation_id} (status: {result['status']})")
            
        except asyncio.CancelledError:
            logger.info(f"[{self.AGENT_TYPE}] Background task cancelled: {operation_id}")
            self._results[operation_id] = {
                "status": "error",
                "summary": "Task was cancelled",
                "result": {},
                "artifacts": [],
                "logs": ["Task cancelled"],
                "stdout": "",
            }
        except Exception as e:
            logger.error(f"[{self.AGENT_TYPE}] Background task failed: {operation_id} - {e}")
            self._results[operation_id] = {
                "status": "error", 
                "summary": f"Task failed: {type(e).__name__}",
                "result": {},
                "artifacts": [],
                "logs": [str(e)],
                "stdout": "",
            }

    def _run_agent_headless(
        self,
        goal: str,
        files_content: Dict[str, bytes],
    ) -> Dict[str, Any]:
        """
        Execute the CLI agent in headless mode with strict contract enforcement.
        """
        t0 = time.time()
        workspace = Path(tempfile.mkdtemp(prefix=f"{self.AGENT_TYPE}_", dir=None))
        outdir = workspace / "out"
        outdir.mkdir(parents=True, exist_ok=True)
        os.chmod(workspace, 0o700)

        logger.info(f"[{self.AGENT_TYPE}] Created secure workspace: {workspace}")

        # Stage input files
        for rel_path, content in files_content.items():
            dest = workspace / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            logger.debug(f"[{self.AGENT_TYPE}] Staged file: {rel_path} ({len(content)} bytes)")

        # Create task description for the agent
        files_list = "\n".join([f"- {filename}" for filename in files_content.keys()])
        (workspace / "README_TASK.md").write_text(
            f"# Headless One-Shot Agent Run\n\n"
            f"**Goal:** {goal}\n\n"
            f"**Available Data Files:**\n{files_list}\n\n"
            f"**Instructions:**\n"
            f"- Read and analyze the data files listed above\n"
            f"- Work only inside the current directory\n"
            f"- Write all outputs under ./out/\n"
            f"- When complete, print exactly one JSON line then {SENTINEL}\n"
            f"- Do not print anything after {SENTINEL}\n",
            encoding="utf-8",
        )

        # Setup environment
        env = os.environ.copy()
        env["CI"] = "1"
        env["NO_COLOR"] = "1"
        
        # Add any API authentication environment variables
        env_overrides = self.get_env_overrides()
        if env_overrides:
            env.update(env_overrides)

        # Build the prompt with file information
        prompt = self.build_prompt(goal, files_content)

        # Get CLI command and arguments
        cli_cmd = self.get_cli_command()
        cli_args = self.get_cli_args(prompt)

        child = None
        captured = bytearray()
        logs = []
        artifacts = []
        parsed_json = None

        try:
            logger.info(f"[{self.AGENT_TYPE}] Spawning {cli_cmd} with args: {cli_args[:2]}...")
            
            child = pexpect.spawn(
                cli_cmd,
                args=cli_args,
                cwd=str(workspace),
                env=env,
                encoding="utf-8",
                timeout=self.timeout_sec,
            )

            logger.info(f"[{self.AGENT_TYPE}] Process spawned, waiting for output...")

            # Read output until sentinel or timeout
            last_progress_log = time.time()
            while True:
                try:
                    chunk = child.read_nonblocking(size=4096, timeout=5)
                except pexpect.TIMEOUT:
                    # Check global timeout
                    elapsed = time.time() - t0
                    if elapsed > self.timeout_sec:
                        logs.append(f"Global timeout {self.timeout_sec}s reached")
                        break
                    
                    # Log progress every 5 seconds
                    if time.time() - last_progress_log > 5:
                        logger.info(f"[{self.AGENT_TYPE}] Still processing... ({elapsed:.1f}s elapsed, {len(captured)} chars captured)")
                        last_progress_log = time.time()
                    continue
                except pexpect.EOF:
                    logger.info(f"[{self.AGENT_TYPE}] Process exited (EOF)")
                    break
                else:
                    captured.extend(chunk.encode("utf-8", errors="ignore"))
                    
                    # Check output size limit
                    if len(captured) >= self.max_stdout_bytes:
                        logs.append("Maximum stdout size reached")
                        break
                    
                    # Check for completion sentinel
                    if SENTINEL in chunk:
                        logger.info(f"[{self.AGENT_TYPE}] Found completion sentinel")
                        break

            # Ensure process is terminated
            try:
                if child.isalive():
                    child.terminate(force=True)
                child.close(force=True)
            except Exception as e:
                logger.warning(f"[{self.AGENT_TYPE}] Error closing process: {e}")

            # Process captured output
            stdout_text = captured.decode("utf-8", errors="ignore")
            stdout_text = _redact_sensitive_data(stdout_text, self.api_key)
            
            execution_time = time.time() - t0
            logs.append(f"Execution time: {execution_time:.2f}s")
            logs.append(f"Captured stdout: {len(stdout_text)} chars")

            # Find the last valid JSON line
            last_json_line = None
            for line in stdout_text.splitlines()[::-1]:
                if JSON_LINE_RE.match(line.strip()):
                    last_json_line = line.strip()
                    break

            if last_json_line:
                try:
                    parsed_json = json.loads(last_json_line)
                    logger.info(f"[{self.AGENT_TYPE}] Successfully parsed JSON response")
                except json.JSONDecodeError as e:
                    logs.append(f"Failed to parse JSON line: {e}")

            # Collect declared artifacts
            artifacts_list = []
            if parsed_json and isinstance(parsed_json.get("artifacts"), list):
                artifacts_list = parsed_json["artifacts"]

            for rel_path in artifacts_list:
                artifact_path = (workspace / rel_path).resolve()
                try:
                    # Ensure artifact is within workspace (security check)
                    artifact_path.relative_to(workspace)
                except ValueError:
                    logs.append(f"Ignored artifact outside workspace: {rel_path}")
                    continue

                if artifact_path.is_file():
                    artifacts.append({
                        "name": str(Path(rel_path)),
                        "content": artifact_path.read_bytes(),
                    })
                    logger.info(f"[{self.AGENT_TYPE}] Collected artifact: {rel_path}")
                elif artifact_path.is_dir():
                    logs.append(f"Directory artifact not packaged: {rel_path}")

            # Determine final status
            has_sentinel = SENTINEL in stdout_text
            status = (parsed_json or {}).get("status") or ("ok" if has_sentinel else "error")
            summary = (parsed_json or {}).get("summary") or ("completed" if status == "ok" else "incomplete")

            return {
                "status": status,
                "summary": summary,
                "result": parsed_json or {},
                "artifacts": artifacts,
                "logs": logs,
                "stdout": stdout_text,
            }

        except Exception as e:
            logger.error(f"[{self.AGENT_TYPE}] Exception in execution: {e}")
            return {
                "status": "error",
                "summary": f"execution failed: {type(e).__name__}",
                "result": {},
                "artifacts": [],
                "logs": logs + [str(e)],
                "stdout": "",
            }
        finally:
            # Always cleanup workspace
            try:
                shutil.rmtree(workspace, ignore_errors=True)
                logger.debug(f"[{self.AGENT_TYPE}] Cleaned up workspace: {workspace}")
            except Exception as e:
                logger.warning(f"[{self.AGENT_TYPE}] Failed to cleanup workspace: {e}")