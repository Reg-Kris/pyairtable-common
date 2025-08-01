"""
Secure Configuration Management for PyAirtable
Implements fail-fast secret loading with validation
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, ValidationError
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing"""
    pass


class SecretValidationError(ConfigurationError):
    """Raised when secret validation fails"""
    pass


@dataclass
class SecretConfig:
    """Configuration for a secret"""
    name: str
    required: bool = True
    min_length: int = 8
    description: str = ""
    
    def validate(self, value: Optional[str]) -> str:
        """Validate secret value"""
        if self.required and not value:
            raise SecretValidationError(f"Required secret '{self.name}' is missing or empty")
        
        if value and len(value) < self.min_length:
            raise SecretValidationError(
                f"Secret '{self.name}' must be at least {self.min_length} characters long"
            )
        
        return value or ""


class SecretProvider(ABC):
    """Abstract base class for secret providers"""
    
    @abstractmethod
    async def get_secret(self, name: str) -> Optional[str]:
        """Get a secret by name"""
        pass
    
    @abstractmethod 
    async def get_secrets(self, names: List[str]) -> Dict[str, str]:
        """Get multiple secrets at once"""
        pass
    
    async def close(self):
        """Close any resources"""
        pass


class EnvironmentSecretProvider(SecretProvider):
    """Load secrets from environment variables"""
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from environment variable"""
        env_name = f"{self.prefix}{name}" if self.prefix else name
        return os.getenv(env_name)
    
    async def get_secrets(self, names: List[str]) -> Dict[str, str]:
        """Get multiple secrets from environment"""
        secrets = {}
        for name in names:
            value = await self.get_secret(name)
            if value:
                secrets[name] = value
        return secrets


class FileSecretProvider(SecretProvider):
    """Load secrets from a JSON file (for development)"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._secrets: Optional[Dict[str, str]] = None
    
    async def _load_secrets(self):
        """Load secrets from file"""
        if self._secrets is None:
            try:
                with open(self.file_path, 'r') as f:
                    self._secrets = json.load(f)
                logger.info(f"Loaded secrets from {self.file_path}")
            except FileNotFoundError:
                logger.warning(f"Secret file {self.file_path} not found")
                self._secrets = {}
            except json.JSONDecodeError as e:
                raise ConfigurationError(f"Invalid JSON in secret file {self.file_path}: {e}")
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from file"""
        await self._load_secrets()
        return self._secrets.get(name)
    
    async def get_secrets(self, names: List[str]) -> Dict[str, str]:
        """Get multiple secrets from file"""
        await self._load_secrets()
        return {name: self._secrets[name] for name in names if name in self._secrets}


class CompositeSecretProvider(SecretProvider):
    """Combine multiple secret providers with priority order"""
    
    def __init__(self, providers: List[SecretProvider]):
        self.providers = providers
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from first provider that has it"""
        for provider in self.providers:
            try:
                value = await provider.get_secret(name)
                if value:
                    return value
            except Exception as e:
                logger.warning(f"Error getting secret '{name}' from provider {provider}: {e}")
                continue
        return None
    
    async def get_secrets(self, names: List[str]) -> Dict[str, str]:
        """Get multiple secrets from providers"""
        secrets = {}
        for name in names:
            value = await self.get_secret(name)
            if value:
                secrets[name] = value
        return secrets
    
    async def close(self):
        """Close all providers"""
        for provider in self.providers:
            await provider.close()


class SecureConfigManager:
    """
    Secure configuration manager that validates secrets at startup
    """
    
    def __init__(self, provider: SecretProvider):
        self.provider = provider
        self.secret_configs: Dict[str, SecretConfig] = {}
        self.secrets: Dict[str, str] = {}
        self._initialized = False
    
    def register_secret(self, config: SecretConfig):
        """Register a secret configuration"""
        self.secret_configs[config.name] = config
    
    def register_secrets(self, configs: List[SecretConfig]):
        """Register multiple secret configurations"""
        for config in configs:
            self.register_secret(config)
    
    async def initialize(self):
        """Initialize and validate all secrets"""
        if self._initialized:
            return
        
        logger.info("Initializing secure configuration manager...")
        
        # Get all secrets at once for efficiency
        secret_names = list(self.secret_configs.keys())
        raw_secrets = await self.provider.get_secrets(secret_names)
        
        # Validate each secret
        errors = []
        for name, config in self.secret_configs.items():
            try:
                raw_value = raw_secrets.get(name)
                validated_value = config.validate(raw_value)
                
                if validated_value:
                    self.secrets[name] = validated_value
                    # Don't log actual secret values
                    logger.info(f"✅ Secret '{name}' loaded and validated")
                elif config.required:
                    errors.append(f"Required secret '{name}' is missing")
                else:
                    logger.info(f"ℹ️ Optional secret '{name}' not provided")
                    
            except SecretValidationError as e:
                errors.append(str(e))
        
        # Fail fast if any required secrets are invalid
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        self._initialized = True
        logger.info(f"✅ Secure configuration initialized with {len(self.secrets)} secrets")
    
    def get_secret(self, name: str) -> str:
        """Get a validated secret"""
        if not self._initialized:
            raise ConfigurationError("Configuration manager not initialized. Call initialize() first.")
        
        if name not in self.secrets:
            config = self.secret_configs.get(name)
            if config and config.required:
                raise ConfigurationError(f"Required secret '{name}' is not available")
            return ""  # Return empty string for optional secrets
        
        return self.secrets[name]
    
    def has_secret(self, name: str) -> bool:
        """Check if a secret is available"""
        return name in self.secrets
    
    async def close(self):
        """Close the secret provider"""
        await self.provider.close()


# Pre-defined secret configurations for PyAirtable services
PYAIRTABLE_SECRETS = [
    SecretConfig(
        name="AIRTABLE_TOKEN",
        required=True,
        min_length=20,
        description="Airtable Personal Access Token"
    ),
    SecretConfig(
        name="GEMINI_API_KEY", 
        required=True,
        min_length=20,
        description="Google Gemini API Key"
    ),
    SecretConfig(
        name="API_KEY",
        required=True,
        min_length=32,
        description="Internal service API key"
    ),
    SecretConfig(
        name="POSTGRES_PASSWORD",
        required=True,
        min_length=16,
        description="PostgreSQL database password"
    ),
    SecretConfig(
        name="REDIS_PASSWORD",
        required=True,
        min_length=16,
        description="Redis password"
    ),
    SecretConfig(
        name="JWT_SECRET",
        required=False,  # Optional for now
        min_length=32,
        description="JWT signing secret"
    ),
]


def create_development_provider() -> SecretProvider:
    """Create provider for development environment"""
    return CompositeSecretProvider([
        FileSecretProvider("secrets.json"),  # Local file first
        EnvironmentSecretProvider(),  # Environment as fallback
    ])


def create_production_provider() -> SecretProvider:
    """Create provider for production environment"""
    return EnvironmentSecretProvider()  # Environment only in production


def create_config_manager(environment: str = "production") -> SecureConfigManager:
    """Create configured secret manager for environment"""
    if environment == "development":
        provider = create_development_provider()
    else:
        provider = create_production_provider()
    
    manager = SecureConfigManager(provider)
    manager.register_secrets(PYAIRTABLE_SECRETS)
    
    return manager


# Global instance for convenience (initialize in lifespan)
config_manager: Optional[SecureConfigManager] = None


async def initialize_secrets() -> SecureConfigManager:
    """Initialize the global config manager"""
    global config_manager
    
    environment = os.getenv("ENVIRONMENT", "production")
    config_manager = create_config_manager(environment)
    
    try:
        await config_manager.initialize()
        return config_manager
    except ConfigurationError:
        # Clean up on failure
        await config_manager.close()
        raise


async def get_secret(name: str) -> str:
    """Get a secret from the global config manager"""
    if not config_manager:
        raise ConfigurationError("Configuration manager not initialized")
    return config_manager.get_secret(name)


async def close_secrets():
    """Close the global config manager"""
    global config_manager
    if config_manager:
        await config_manager.close()
        config_manager = None