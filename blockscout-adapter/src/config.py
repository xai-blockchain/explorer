"""
Configuration management for XAI Blockscout Adapter
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AdapterConfig:
    """Main configuration for the RPC adapter"""

    # XAI Node URLs
    xai_primary_url: str = "http://127.0.0.1:12570"
    xai_fallback_url: str = "http://127.0.0.1:12571"

    # Chain configuration
    chain_id: int = 1337
    chain_name: str = "XAI Testnet"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8545

    # CORS
    cors_origins: list[str] = None

    # Logging
    log_level: str = "INFO"

    # Timeouts
    request_timeout: float = 30.0
    max_retries: int = 3

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]

    @classmethod
    def from_env(cls) -> "AdapterConfig":
        """Load configuration from environment variables"""
        cors_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = [o.strip() for o in cors_str.split(",")]

        return cls(
            xai_primary_url=os.getenv("XAI_PRIMARY_URL", "http://127.0.0.1:12570"),
            xai_fallback_url=os.getenv("XAI_FALLBACK_URL", "http://127.0.0.1:12571"),
            chain_id=int(os.getenv("XAI_CHAIN_ID", "1337")),
            chain_name=os.getenv("XAI_CHAIN_NAME", "XAI Testnet"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8545")),
            cors_origins=cors_origins,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            request_timeout=float(os.getenv("REQUEST_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
        )


# Singleton instance
_config: Optional[AdapterConfig] = None


def get_config() -> AdapterConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = AdapterConfig.from_env()
    return _config
