"""
Application settings loaded from environment variables using Pydantic Settings.
"""

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