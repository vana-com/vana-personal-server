"""
Application settings loaded from environment variables using Pydantic Settings.
"""

from typing import Optional, Literal, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with validation and type safety."""

    # Environment configuration
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )

    # API Configuration
    replicate_api_token: str = Field(
        ...,
        alias="REPLICATE_API_TOKEN",
        description="Replicate API token for ML model inference"
    )

    # Blockchain Configuration
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

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v

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