"""Security utilities for PyAirtable ecosystem."""

from .airtable_sanitizer import (
    sanitize_airtable_formula,
    sanitize_field_name,
    sanitize_user_query,
    AirtableFormulaInjectionError
)

from .auth import (
    AuthConfig,
    SecurityError,
    AuthenticationError,
    AuthorizationError,
    constant_time_compare,
    generate_secure_api_key,
    verify_api_key_secure,
    JWTManager,
    APIKeyAuth,
    JWTAuth,
    SecurityMiddleware,
    require_api_key,
    create_auth_dependencies,
    validate_api_key_strength,
    RateLimiter
)

from .cors import (
    CORSConfig,
    create_cors_config,
    setup_cors_middleware,
    DEVELOPMENT_CORS,
    PRODUCTION_CORS_TEMPLATE
)

__all__ = [
    # Airtable sanitization
    "sanitize_airtable_formula",
    "sanitize_field_name", 
    "sanitize_user_query",
    "AirtableFormulaInjectionError",
    
    # Authentication & Authorization
    "AuthConfig",
    "SecurityError",
    "AuthenticationError", 
    "AuthorizationError",
    "constant_time_compare",
    "generate_secure_api_key",
    "verify_api_key_secure",
    "JWTManager",
    "APIKeyAuth",
    "JWTAuth", 
    "SecurityMiddleware",
    "require_api_key",
    "create_auth_dependencies",
    "validate_api_key_strength",
    "RateLimiter",
    
    # CORS Configuration
    "CORSConfig",
    "create_cors_config",
    "setup_cors_middleware",
    "DEVELOPMENT_CORS",
    "PRODUCTION_CORS_TEMPLATE"
]