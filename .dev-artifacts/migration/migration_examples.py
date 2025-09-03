#!/usr/bin/env python3
"""
Migration Examples for dotmac.secrets

This file shows examples of how to migrate from the old dotmac_shared.secrets
to the new dotmac.secrets package.

These examples are for reference only and will be cleaned up after validation.
"""

# ===== BEFORE: Using dotmac_shared.secrets =====

# OLD WAY (deprecated)
def old_usage_example():
    """Example of the old way - now deprecated"""
    from dotmac_shared.secrets import SecretsManager, from_env
    
    # This will show deprecation warnings
    manager = SecretsManager()  # Uses from_env() behind the scenes
    secrets = from_env()  # Also deprecated
    
    return manager, secrets


# ===== AFTER: Using new dotmac.secrets =====

async def new_usage_example():
    """Example of the new recommended way"""
    from dotmac.secrets import from_env
    
    # New unified interface
    async with from_env() as secrets_manager:
        # Get JWT keypair for app
        keypair = await secrets_manager.get_jwt_keypair("auth")
        
        # Get database credentials
        db_creds = await secrets_manager.get_database_credentials("primary")
        
        # Get service signing secret
        signing_secret = await secrets_manager.get_service_signing_secret("auth")
        
        # Get custom secrets
        custom_config = await secrets_manager.get_custom_secret("external/api-config")
        
        return keypair, db_creds, signing_secret, custom_config


# ===== MIGRATION FOR dotmac.auth =====

def auth_migration_example():
    """Example of migrating dotmac.auth to use new secrets"""
    
    # OPTION 1: Use the adapter (temporary compatibility)
    from dotmac.auth.providers import DotMacSecretsAdapter
    
    # This works with existing auth code but shows deprecation warnings
    provider = DotMacSecretsAdapter(app_name="auth")
    
    # OPTION 2: Direct migration (recommended)
    from dotmac.secrets import from_env
    
    async def setup_auth_with_new_secrets():
        secrets_manager = from_env()
        
        # Get auth keypair directly
        keypair = await secrets_manager.get_jwt_keypair("auth")
        
        # Use in JWT service configuration
        jwt_config = {
            "algorithm": keypair.algorithm,
            "private_key": keypair.private_pem,
            "public_key": keypair.public_pem,
            "key_id": keypair.kid
        }
        
        return jwt_config


# ===== ENVIRONMENT VARIABLE EXAMPLES =====

def environment_examples():
    """
    Examples of environment variables for different providers
    """
    
    # For OpenBao/Vault (production)
    openbao_env = {
        "SECRETS_PROVIDER": "openbao",
        "OPENBAO_URL": "https://vault.company.com:8200",
        "OPENBAO_TOKEN": "hvs.CAESIJ...",  # Or use other auth methods
        "OPENBAO_MOUNT": "secret",
    }
    
    # For environment variables (development only)
    env_provider_env = {
        "SECRETS_PROVIDER": "env",
        "ENVIRONMENT": "development",
        "EXPLICIT_ALLOW_ENV_SECRETS": "true",  # Required for safety
        "JWT_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----",
        "JWT_PUBLIC_KEY": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
        "JWT_ALGORITHM": "RS256",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "SERVICE_SIGNING_SECRET": "your-service-secret-here",
    }
    
    # Auto-detection will choose provider based on available env vars
    auto_detection_priority = [
        "OPENBAO_URL + OPENBAO_TOKEN -> OpenBao provider",
        "VAULT_ADDR + VAULT_TOKEN -> OpenBao provider", 
        "EXPLICIT_ALLOW_ENV_SECRETS=true -> Environment provider",
        "Default -> Environment provider (dev only)"
    ]
    
    return openbao_env, env_provider_env, auto_detection_priority


if __name__ == "__main__":
    print("Migration examples for dotmac.secrets")
    print("See function docstrings for usage patterns")
    
    # Show deprecation warnings
    try:
        old_manager, old_secrets = old_usage_example()
        print("✅ Old usage still works (with deprecation warnings)")
    except Exception as e:
        print(f"❌ Old usage failed: {e}")
    
    print("✅ Migration examples created")