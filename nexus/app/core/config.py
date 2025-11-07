"""
Configuration management for the PDF Comparison Service.

This module handles all application configuration using Pydantic settings.
Environment variables are loaded from .env file or system environment.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings have sensible defaults and can be overridden via environment variables.
    """

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_title: str = Field(default="PDF Comparison Service", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    debug: bool = Field(default=False, description="Debug mode")

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=50, description="Redis connection pool size")

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    celery_task_timeout: int = Field(default=600, description="Task timeout in seconds")
    celery_max_retries: int = Field(default=3, description="Maximum task retries")
    celery_worker_concurrency: int = Field(default=4, description="Celery worker concurrency")

    # LLM Configuration
    llm_provider: str = Field(
        default="openai",
        description="LLM provider (openai or anthropic)"
    )
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    llm_model: str = Field(
        default="gpt-4-turbo-preview",
        description="LLM model to use"
    )
    llm_temperature: float = Field(default=0.1, description="LLM temperature")
    llm_max_tokens: int = Field(default=4096, description="LLM max tokens")
    llm_timeout: int = Field(default=120, description="LLM API timeout in seconds")

    # Processing Configuration
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    min_file_size_bytes: int = Field(default=100, description="Minimum file size in bytes")
    supported_formats: str = Field(default="pdf", description="Supported file formats")
    temp_dir: str = Field(default="/tmp/pdf_comparison", description="Temporary directory")
    output_dir: str = Field(default="./outputs", description="Output directory")
    cleanup_temp_files: bool = Field(default=True, description="Cleanup temporary files")
    cleanup_after_hours: int = Field(default=24, description="Cleanup after hours")

    # PDF Processing
    pdf_dpi: int = Field(default=300, description="DPI for image extraction")
    pdf_max_pages: int = Field(default=500, description="Maximum PDF pages to process")
    extract_images: bool = Field(default=True, description="Extract images from PDFs")
    extract_tables: bool = Field(default=True, description="Extract tables from PDFs")

    # Diff Analysis
    diff_context_lines: int = Field(default=3, description="Context lines for diff")
    similarity_threshold: float = Field(
        default=0.85,
        description="Similarity threshold for matching"
    )
    include_unchanged_sections: bool = Field(
        default=False,
        description="Include unchanged sections in results"
    )

    # Security
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    max_request_size_mb: int = Field(default=100, description="Max request size in MB")
    enable_cors: bool = Field(default=True, description="Enable CORS")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    api_keys: List[str] = Field(default_factory=list, description="Valid API keys")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: str = Field(default="./logs/app.log", description="Log file path")
    log_rotation: str = Field(default="10 MB", description="Log rotation size")
    log_retention: str = Field(default="30 days", description="Log retention period")

    # Database (optional)
    database_url: Optional[str] = Field(
        default=None,
        description="Database URL for persistence"
    )
    db_pool_size: int = Field(default=20, description="Database pool size")
    db_max_overflow: int = Field(default=10, description="Database max overflow")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=10, description="Rate limit per minute")
    rate_limit_burst: int = Field(default=20, description="Rate limit burst")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics")
    metrics_port: int = Field(default=9090, description="Metrics port")

    # Feature Flags
    enable_caching: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    enable_llm_fallback: bool = Field(
        default=True,
        description="Enable LLM fallback on error"
    )
    enable_async_processing: bool = Field(
        default=True,
        description="Enable async processing"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider is supported."""
        allowed = ["openai", "anthropic"]
        if v.lower() not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_request_size_bytes(self) -> int:
        """Convert max request size from MB to bytes."""
        return self.max_request_size_mb * 1024 * 1024

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def get_llm_api_key(self) -> Optional[str]:
        """Get the appropriate LLM API key based on provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "anthropic":
            return self.anthropic_api_key
        return None

    def validate_llm_config(self) -> bool:
        """Validate LLM configuration is complete."""
        api_key = self.get_llm_api_key()
        if not api_key:
            return False
        if not self.llm_model:
            return False
        return True

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        directories = [
            self.temp_dir,
            self.output_dir,
            os.path.dirname(self.log_file) if self.log_file else None
        ]

        for directory in directories:
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    This is the recommended way to access settings throughout the application.

    Returns:
        Settings: Application settings instance
    """
    settings = Settings()
    settings.ensure_directories()
    return settings


# Convenience function for backwards compatibility
settings = get_settings()
