"""
Gemini CLI Agent provider for headless, one-shot agentic tasks.

Inherits from BaseAgentProvider to leverage shared functionality
for PTY-based headless execution of Google's Gemini CLI.
"""
import logging
from typing import Dict, List

from compute.base_agent import BaseAgentProvider
from settings import get_settings

logger = logging.getLogger(__name__)


class GeminiAgentProvider(BaseAgentProvider):
    """
    Compute provider for headless Gemini CLI agent execution.

    Executes gemini CLI in a controlled, isolated environment
    with a strict contract for deterministic results.
    """

    CLI_NAME = "gemini"
    AGENT_TYPE = "gemini"
    REQUIRES_NETWORK = True  # Gemini needs to reach Google's API

    def __init__(self):
        super().__init__()
        self.settings = get_settings()

        # Check authentication mode for Gemini
        # Gemini supports: Google OAuth, API Key, or Vertex AI
        if self.settings.gemini_api_key:
            logger.info("Using API key for Gemini CLI (production mode)")
            self.use_api_auth = True
            self.api_key = self.settings.gemini_api_key
            self.use_vertex_ai = self.settings.gemini_use_vertex_ai
        else:
            logger.info("No API key found, using Google OAuth/cached credentials (development mode)")
            self.use_api_auth = False
            self.api_key = None
            self.use_vertex_ai = False

        self.timeout_sec = self.settings.gemini_timeout_sec
        self.max_stdout_bytes = self.settings.gemini_max_stdout_mb * 1_000_000
        self.cli_path = self.settings.gemini_cli_path

        logger.info(f"Initialized GeminiAgentProvider (auth mode: {'API' if self.use_api_auth else 'OAuth'})")

    def get_cli_command(self) -> str:
        """Get the CLI command to execute."""
        return "gemini"

    def get_cli_args(self, prompt: str) -> List[str]:
        """Get CLI arguments for Gemini CLI."""
        # Use -y (yolo mode) to enable write tools and auto-approve
        # Use --sandbox=false to disable Gemini's built-in Docker sandbox
        # (we're already running inside our own sandbox container)
        # Prompt will be passed via stdin to handle long inputs
        return ["-y", "--sandbox=false"]

    def build_prompt(self, goal: str, files_dict: Dict[str, bytes] = None) -> str:
        """Build a prompt for Gemini CLI that requests artifacts."""
        files_info = ""
        if files_dict:
            files_list = []
            for filename, content in files_dict.items():
                size_kb = len(content) / 1024
                files_list.append(f"  - {filename} ({size_kb:.1f}KB)")
            files_info = f"\n\nData files available:\n" + "\n".join(files_list) + "\n"

        return (
            f"You are a helpful AI assistant running in batch mode. "
            f"Read and analyze any data files in the current directory.{files_info}\n\n"
            f"Task: {goal}\n\n"
            f"IMPORTANT INSTRUCTIONS:\n"
            f"1. Create a directory called 'out' for your outputs\n"
            f"2. Generate useful artifacts like reports, summaries, or analysis files\n"
            f"3. Save your main output as ./out/analysis_report.md\n"
            f"4. Create additional files as needed (./out/insights.json, ./out/recommendations.txt, etc.)\n"
            f"5. When complete, output a JSON line with your results:\n"
            f'   {{"status":"ok","summary":"Brief summary","artifacts":["./out/analysis_report.md","./out/other_file.json"]}}\n'
            f"6. Then output exactly: __AGENT_DONE__\n"
        )

    def get_env_overrides(self) -> Dict[str, str]:
        """Get environment variable overrides for API authentication."""
        # Base environment to disable data collection and telemetry
        env_vars = {
            "GOOGLE_GENAI_DISABLE_TELEMETRY": "1",
            "GEMINI_USAGE_STATISTICS_ENABLED": "false",  # Disable usage statistics
        }

        if self.use_api_auth:
            # Production mode: use API credentials
            # Use GEMINI_API_KEY (preferred) or GOOGLE_API_KEY as fallback
            env_vars.update({
                "GEMINI_API_KEY": self.api_key,
            })
            logger.debug(f"GEMINI_API_KEY present in environment: {bool(self.api_key)}")

            # Add Vertex AI flag if enabled
            if self.use_vertex_ai:
                env_vars["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

            return env_vars

        # Development mode: use Google OAuth/cached credentials
        return env_vars