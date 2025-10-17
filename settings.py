"""
Application settings loaded from environment variables using Pydantic Settings.
"""

from typing import Optional, Literal, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and type safety."""
    
    replicate_api_token: str = Field(
        ...,
        alias="REPLICATE_API_TOKEN",
        description="Replicate API token for ML model inference"
    )
    
    wallet_mnemonic: str = Field(
        ...,
        alias="WALLET_MNEMONIC",
        description="Wallet mnemonic for key derivation"
    )

    chain_id: int = Field(
        ...,
        alias="CHAIN_ID",
        description="Blockchain chain ID"
    )
    
    # Mock mode for local testing
    mock_mode: bool = Field(
        default=False,
        alias="MOCK_MODE",
        description="Enable mock mode to bypass blockchain validation for testing"
    )
    
    # Cloudflare R2 Configuration
    r2_account_id: str = Field(
        default="",
        alias="R2_ACCOUNT_ID",
        description="Cloudflare R2 account ID"
    )
    
    r2_access_key_id: str = Field(
        default="",
        alias="R2_ACCESS_KEY_ID", 
        description="Cloudflare R2 access key ID"
    )
    
    r2_secret_access_key: str = Field(
        default="",
        alias="R2_SECRET_ACCESS_KEY",
        description="Cloudflare R2 secret access key"
    )
    
    r2_bucket_name: str = Field(
        default="personal-server-artifacts",
        alias="R2_BUCKET_NAME",
        description="R2 bucket name for artifact storage"
    )
    
    mnemonic_language: str = Field(
        default="english",
        alias="MNEMONIC_LANGUAGE",
        description="Language for mnemonic phrase"
    )
    
    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level"
    )
    
    # Security Configuration
    enable_debug_logging: bool = Field(
        default=False,
        alias="ENABLE_DEBUG_LOGGING",
        description="Enable debug logging (may contain sensitive data)"
    )
    
    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        alias="API_HOST",
        description="API host address"
    )
    
    api_port: int = Field(
        default=8000,
        alias="API_PORT",
        description="API port"
    )
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(
        default=300,
        alias="CACHE_TTL_SECONDS",
        description="Cache TTL in seconds"
    )
    
    # Request Configuration
    request_timeout_seconds: int = Field(
        default=30,
        alias="REQUEST_TIMEOUT_SECONDS",
        description="Request timeout in seconds"
    )

    # Upstash Redis Configuration
    upstash_redis_rest_url: Optional[str] = Field(
        default=None,
        alias="UPSTASH_REDIS_REST_URL",
        description="Upstash Redis REST URL"
    )

    upstash_redis_rest_token: Optional[str] = Field(
        default=None,
        alias="UPSTASH_REDIS_REST_TOKEN",
        description="Upstash Redis REST token"
    )

    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(
        default=True,
        alias="RATE_LIMIT_ENABLED",
        description="Enable rate limiting"
    )

    rate_limit_use_ip: bool = Field(
        default=True,
        alias="RATE_LIMIT_USE_IP",
        description="Use IP address for rate limiting"
    )

    rate_limit_use_signature: bool = Field(
        default=True,
        alias="RATE_LIMIT_USE_SIGNATURE",
        description="Use signature for rate limiting"
    )

    # Rate Limits
    rate_limit_default_rpm: int = Field(
        default=60,
        alias="RATE_LIMIT_DEFAULT_RPM",
        description="Default requests per minute"
    )

    rate_limit_operations_per_hour: int = Field(
        default=100,
        alias="RATE_LIMIT_OPERATIONS_PER_HOUR",
        description="Operations per hour"
    )

    rate_limit_identity_rpm: int = Field(
        default=120,
        alias="RATE_LIMIT_IDENTITY_RPM",
        description="Identity requests per minute"
    )

    # Whitelist
    rate_limit_whitelist_ips: Optional[List[str]] = Field(
        default=None,
        alias="RATE_LIMIT_WHITELIST_IPS",
        description="Comma-separated list of whitelisted IPs"
    )

    # Qwen Code Configuration (headless agent)
    qwen_api_url: Optional[str] = Field(
        default=None,
        alias="QWEN_API_URL",
        description="OpenAI-compatible API endpoint URL"
    )
    
    qwen_model_name: Optional[str] = Field(
        default=None,
        alias="QWEN_MODEL_NAME",
        description="Model name (e.g., qwen/qwen3-coder)"
    )
    
    qwen_api_key: Optional[str] = Field(
        default=None,
        alias="QWEN_API_KEY",
        description="API key for authentication"
    )
    
    qwen_timeout_sec: int = Field(
        default=180,
        alias="QWEN_TIMEOUT_SEC",
        description="Wall-clock timeout for agent runs in seconds"
    )
    
    qwen_max_stdout_mb: int = Field(
        default=2,
        alias="QWEN_MAX_STDOUT_MB",
        description="Maximum stdout size in megabytes"
    )
    
    qwen_cli_path: Optional[str] = Field(
        default=None,
        alias="QWEN_CLI_PATH",
        description="Path to qwen CLI binary (defaults to 'qwen' on PATH)"
    )

    # Gemini CLI Configuration (headless agent)
    gemini_api_key: Optional[str] = Field(
        default=None,
        alias="GEMINI_API_KEY",
        description="Google API key for Gemini"
    )
    
    gemini_use_vertex_ai: bool = Field(
        default=False,
        alias="GEMINI_USE_VERTEX_AI",
        description="Use Vertex AI for Gemini (requires GCP project setup)"
    )
    
    gemini_timeout_sec: int = Field(
        default=180,
        alias="GEMINI_TIMEOUT_SEC",
        description="Wall-clock timeout for Gemini agent runs in seconds"
    )
    
    gemini_max_stdout_mb: int = Field(
        default=2,
        alias="GEMINI_MAX_STDOUT_MB",
        description="Maximum stdout size in megabytes for Gemini"
    )
    
    gemini_cli_path: Optional[str] = Field(
        default=None,
        alias="GEMINI_CLI_PATH",
        description="Path to gemini CLI binary (defaults to 'gemini' on PATH)"
    )

    # Docker Agent Execution Configuration
    docker_agent_image: str = Field(
        default="vana-agent-sandbox",
        alias="DOCKER_AGENT_IMAGE",
        description="Docker image name for agent sandbox execution"
    )
    
    docker_agent_memory_limit: str = Field(
        default="512m",
        alias="DOCKER_AGENT_MEMORY_LIMIT",
        description="Memory limit for Docker agent containers (e.g., '512m', '1g')"
    )
    
    docker_agent_timeout_sec: int = Field(
        default=300,
        alias="DOCKER_AGENT_TIMEOUT_SEC",
        description="Docker container execution timeout in seconds"
    )
    
    docker_agent_max_output_mb: int = Field(
        default=10,
        alias="DOCKER_AGENT_MAX_OUTPUT_MB",
        description="Maximum output capture size for Docker agents in megabytes"
    )
    
    docker_agent_cpu_limit: Optional[str] = Field(
        default="1.0",
        alias="DOCKER_AGENT_CPU_LIMIT",
        description="CPU limit for Docker agents (e.g., '0.5', '1.0', '2.0')"
    )

    # Agent Runtime Configuration
    agent_runtime: str = Field(
        default="process",
        alias="AGENT_RUNTIME",
        description="Agent execution runtime: 'process' for Cloud Run (default), 'docker' for local/dev"
    )
    
    # Process Agent Configuration (for Cloud Run)
    agent_max_concurrent_per_instance: int = Field(
        default=1,
        alias="AGENT_MAX_CONCURRENT_PER_INSTANCE",
        description="Maximum concurrent agent processes per container instance"
    )
    
    agent_memory_limit_mb: int = Field(
        default=1024,
        alias="AGENT_MEMORY_LIMIT_MB",
        description="V8 heap limit for Node.js agents via --max-old-space-size (MB). Cloud Run container limit enforces instance-level memory."
    )
    
    agent_timeout_sec: int = Field(
        default=300,
        alias="AGENT_TIMEOUT_SEC",
        description="Agent process execution timeout in seconds"
    )
    
    agent_file_size_limit_mb: int = Field(
        default=100,
        alias="AGENT_FILE_SIZE_LIMIT_MB",
        description="Maximum file size per write operation in megabytes"
    )
    
    agent_max_output_mb: int = Field(
        default=10,
        alias="AGENT_MAX_OUTPUT_MB",
        description="Maximum output capture size for agents in megabytes"
    )

    @field_validator('replicate_api_token')
    @classmethod
    def validate_replicate_token(cls, v):
        """Validate Replicate API token format."""
        if not v or len(v) < 10:
            raise ValueError('Replicate API token must be at least 10 characters')
        return v

    @field_validator('wallet_mnemonic')
    @classmethod
    def validate_wallet_mnemonic(cls, v):
        """Validate wallet mnemonic."""
        if not v or len(v.split()) < 12:
            raise ValueError('Wallet mnemonic must contain at least 12 words')
        return v

    @field_validator('rate_limit_whitelist_ips', mode='before')
    @classmethod
    def parse_whitelist_ips(cls, v):
        """Parse comma-separated whitelist IPs."""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            ips = [ip.strip() for ip in v.split(',') if ip.strip()]
            return ips
        return v or []

    @model_validator(mode='after')
    def validate_debug_logging_in_production(self):
        """Warn about debug logging in production."""
        if self.enable_debug_logging and self.environment == 'production':
            import warnings
            warnings.warn(
                "Debug logging is enabled in production environment. "
                "This may expose sensitive data in logs.",
                UserWarning
            )
        return self

    @model_validator(mode='after')
    def validate_rate_limiting_config(self):
        """Validate rate limiting configuration."""
        if self.rate_limit_enabled:
            if not self.upstash_redis_rest_url or not self.upstash_redis_rest_token:
                import warnings
                warnings.warn(
                    "Rate limiting is enabled but Upstash Redis credentials are not configured. "
                    "Rate limiting will be disabled.",
                    UserWarning
                )
                self.rate_limit_enabled = False
        return self

    # Pydantic V2 configuration
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance for backward compatibility
settings = get_settings()