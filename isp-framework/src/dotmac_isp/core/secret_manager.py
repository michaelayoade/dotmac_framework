"""
Strategic Secret Management System

Centralized secret management with OpenBao/Vault integration for production
and secure fallbacks for development environments.
"""
import os
import logging
from typing import Dict, Optional, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecretManager:
    """
    Strategic secret management with multiple backends.
    
    Priority order:
    1. OpenBao/Vault (production)
    2. Environment variables (development/staging)  
    3. Default development values (local only)
    """

    def __init__(self):
        """  Init   operation."""
        self.vault_client: Optional[Any] = None
        self.use_vault = os.getenv("USE_VAULT", "false").lower() == "true"
        self.vault_url = os.getenv("VAULT_URL", "http://openbao:8200")
        self.vault_token = os.getenv("VAULT_TOKEN")
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        
        if self.use_vault and self.vault_token:
            self._init_vault_client()

    def _init_vault_client(self):
        """Initialize OpenBao/Vault client."""
        try:
            import hvac
            self.vault_client = hvac.Client(
                url=self.vault_url,
                token=self.vault_token
            )
            if self.vault_client.is_authenticated():
                logger.info("✅ OpenBao/Vault client initialized successfully")
            else:
                logger.warning("⚠️ Vault client not authenticated, falling back to env vars")
                self.vault_client = None
        except ImportError:
            logger.warning("⚠️ hvac not available, falling back to environment variables")
        except Exception as e:
            logger.warning(f"⚠️ Vault initialization failed: {e}, falling back to env vars")
            self.vault_client = None

    @lru_cache(maxsize=128)
    def get_secret(self, secret_path: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret with strategic fallback chain.
        
        Args:
            secret_path: Path to secret (e.g., 'database/password')
            default: Default value for development environments
            
        Returns:
            Secret value or None
        """
        # 1. Try OpenBao/Vault (production)
        if self.vault_client:
            try:
                response = self.vault_client.secrets.kv.v2.read_secret_version(
                    path=secret_path
                )
                secret_value = response['data']['data'].get('value')
                if secret_value:
                    logger.debug(f"✅ Retrieved secret from Vault: {secret_path}")
                    return secret_value
            except Exception as e:
                logger.warning(f"⚠️ Failed to get secret from Vault {secret_path}: {e}")

        # 2. Try environment variables
        env_key = secret_path.replace('/', '_').replace('-', '_').upper()
        env_value = os.getenv(env_key)
        if env_value:
            logger.debug(f"✅ Retrieved secret from env: {env_key}")
            return env_value

        # 3. Use development default (only in non-production)
        if self.environment in ['development', 'local', 'test'] and default:
            logger.debug(f"✅ Using development default for: {secret_path}")
            return default

        # 4. Production security: fail secure
        if self.environment == 'production':
            logger.error(f"❌ Secret not found in production: {secret_path}")
            raise ValueError(f"Required secret not found: {secret_path}")

        logger.warning(f"⚠️ Secret not found: {secret_path}")
        return None

    def get_database_config(self) -> Dict[str, str]:
        """Get complete database configuration."""
        return {
            'host': self.get_secret('database/host', 'postgres'),
            'port': self.get_secret('database/port', '5432'),
            'username': self.get_secret('database/username', 'dotmac'),
            'password': self.get_secret('database/password', 'dotmac'),
            'database': self.get_secret('database/name', 'dotmac_isp'),
        }

    def get_redis_config(self) -> Dict[str, str]:
        """Get complete Redis configuration."""
        return {
            'host': self.get_secret('redis/host', 'redis-shared'),
            'port': self.get_secret('redis/port', '6379'),
            'password': self.get_secret('redis/password', 'dotmac_redis_password'),
            'database': self.get_secret('redis/database', '0'),
        }

    def get_jwt_secret(self) -> str:
        """Get JWT secret key with strong validation."""
        jwt_secret = self.get_secret(
            'security/jwt_secret', 
            'dev-secret-key-32-chars-minimum!'
        )
        
        if not jwt_secret or len(jwt_secret) < 32:
            if self.environment == 'production':
                raise ValueError("JWT secret must be at least 32 characters in production")
            logger.warning("⚠️ JWT secret is weak - update for production")
            
        return jwt_secret

    def build_database_url(self, async_driver: bool = False) -> str:
        """Build database URL from configuration."""
        config = self.get_database_config()
        driver = "postgresql+asyncpg" if async_driver else "postgresql"
        
        return (
            f"{driver}://{config['username']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}"
        )

    def build_redis_url(self, database: str = "0") -> str:
        """Build Redis URL from configuration."""
        config = self.get_redis_config()
        password_part = f":{config['password']}@" if config['password'] else ""
        
        return f"redis://{password_part}{config['host']}:{config['port']}/{database}"


# Global instance for easy access
@lru_cache(maxsize=1)
def get_secret_manager() -> SecretManager:
    """Get global secret manager instance."""
    return SecretManager()