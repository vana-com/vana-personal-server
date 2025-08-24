"""
Qwen Code Agent provider for headless, one-shot agentic tasks.

Inherits from BaseAgentProvider to leverage shared functionality
for PTY-based headless execution of qwen-code CLI.
"""
import logging
from typing import Dict, List

from compute.base_agent import BaseAgentProvider
from settings import get_settings

logger = logging.getLogger(__name__)


class QwenCodeAgentProvider(BaseAgentProvider):
    """
    Compute provider for headless qwen-code agent execution.
    
    Executes qwen-code CLI in a controlled, isolated environment
    with a strict contract for deterministic results.
    """
    
    CLI_NAME = "qwen"
    AGENT_TYPE = "qwen"
    
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        
        # Check if API credentials are provided (production mode)
        if all([
            self.settings.qwen_api_url,
            self.settings.qwen_model_name,
            self.settings.qwen_api_key
        ]):
            logger.info("Using API credentials for qwen-code (production mode)")
            self.use_api_auth = True
            self.api_url = self.settings.qwen_api_url
            self.model_name = self.settings.qwen_model_name
            self.api_key = self.settings.qwen_api_key
        else:
            logger.info("No API credentials found, using OAuth/cached credentials (development mode)")
            self.use_api_auth = False
            self.api_url = None
            self.model_name = None
            self.api_key = None

        self.timeout_sec = self.settings.qwen_timeout_sec
        self.max_stdout_bytes = self.settings.qwen_max_stdout_mb * 1_000_000
        self.cli_path = self.settings.qwen_cli_path

        logger.info(f"Initialized QwenCodeAgentProvider (auth mode: {'API' if self.use_api_auth else 'OAuth'})")

    def get_cli_command(self) -> str:
        """Get the CLI command to execute."""
        return "qwen"
    
    def get_cli_args(self, prompt: str) -> List[str]:
        """Get CLI arguments for qwen-code."""
        # Use -p for prompt mode and -y for YOLO mode (auto-accept)
        return ["-p", prompt, "-y"]
    
    def get_env_overrides(self) -> Dict[str, str]:
        """Get environment variable overrides for API authentication."""
        if self.use_api_auth:
            # Production mode: use API credentials
            # Note: qwen-code uses OPENAI_* env vars for compatibility
            return {
                "OPENAI_API_KEY": self.api_key,
                "OPENAI_BASE_URL": self.api_url,
                "OPENAI_MODEL": self.model_name,
            }
        # Development mode: use OAuth/cached credentials (no env vars needed)
        return {}