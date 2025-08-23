"""
Vault authentication strategies for secure authentication patterns.

REFACTORED: Extracted from vault_client.py to reduce VaultClient._authenticate 
complexity from 14→3 using Strategy pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

import structlog

logger = structlog.get_logger(__name__)

try:
    import hvac
    from hvac.exceptions import Forbidden, InvalidPath, InvalidRequest
    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    hvac = None


class VaultAuthStrategy(ABC):
    """Base strategy for Vault authentication."""
    
    @abstractmethod
    def authenticate(self, client, config) -> str:
        """Authenticate with Vault and return client token."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name for logging."""
        pass
    
    @abstractmethod
    def validate_config(self, config) -> bool:
        """Validate configuration for this authentication method."""
        pass


class TokenAuthStrategy(VaultAuthStrategy):
    """Strategy for token-based authentication."""
    
    def authenticate(self, client, config) -> str:
        """Authenticate using token."""
        if not config.token:
            raise ValueError("Token required for token authentication")
        
        # Token is already set during client initialization
        # Just verify it's valid
        if not client.is_authenticated():
            raise ValueError("Invalid token provided")
        
        return config.token.get_secret_value()
    
    def get_strategy_name(self) -> str:
        return "Token Authentication"
    
    def validate_config(self, config) -> bool:
        """Validate token authentication configuration."""
        return config.token is not None


class AppRoleAuthStrategy(VaultAuthStrategy):
    """Strategy for AppRole authentication."""
    
    def authenticate(self, client, config) -> str:
        """Authenticate using AppRole."""
        if not self.validate_config(config):
            raise ValueError("role_id and secret_id required for AppRole authentication")
        
        try:
            response = client.auth.approle.login(
                role_id=config.role_id.get_secret_value(),
                secret_id=config.secret_id.get_secret_value(),
            )
            
            if not response or "auth" not in response:
                raise ValueError("Invalid AppRole authentication response")
            
            client_token = response["auth"]["client_token"]
            client.token = client_token
            
            return client_token
        except Exception as e:
            logger.error("AppRole authentication failed", error=str(e))
            raise ValueError(f"AppRole authentication failed: {str(e)}")
    
    def get_strategy_name(self) -> str:
        return "AppRole Authentication"
    
    def validate_config(self, config) -> bool:
        """Validate AppRole authentication configuration."""
        return (
            config.role_id is not None and 
            config.secret_id is not None
        )


class KubernetesAuthStrategy(VaultAuthStrategy):
    """Strategy for Kubernetes authentication."""
    
    def authenticate(self, client, config) -> str:
        """Authenticate using Kubernetes service account."""
        if not self.validate_config(config):
            raise ValueError("kubernetes_role required for Kubernetes authentication")
        
        try:
            # Read the service account token
            jwt_token = self._read_service_account_token()
            
            response = client.auth.kubernetes.login(
                role=config.kubernetes_role,
                jwt=jwt_token,
            )
            
            if not response or "auth" not in response:
                raise ValueError("Invalid Kubernetes authentication response")
            
            client_token = response["auth"]["client_token"]
            client.token = client_token
            
            return client_token
        except Exception as e:
            logger.error("Kubernetes authentication failed", error=str(e))
            raise ValueError(f"Kubernetes authentication failed: {str(e)}")
    
    def _read_service_account_token(self) -> str:
        """Read the Kubernetes service account JWT token."""
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        try:
            with open(token_path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise ValueError(f"Service account token not found at {token_path}")
        except PermissionError:
            raise ValueError(f"Permission denied reading service account token at {token_path}")
        except Exception as e:
            raise ValueError(f"Failed to read service account token: {str(e)}")
    
    def get_strategy_name(self) -> str:
        return "Kubernetes Authentication"
    
    def validate_config(self, config) -> bool:
        """Validate Kubernetes authentication configuration."""
        return config.kubernetes_role is not None


class AWSAuthStrategy(VaultAuthStrategy):
    """Strategy for AWS IAM authentication."""
    
    def authenticate(self, client, config) -> str:
        """Authenticate using AWS IAM."""
        if not self.validate_config(config):
            raise ValueError("aws_role required for AWS authentication")
        
        try:
            response = client.auth.aws.iam_login(
                role=config.aws_role,
            )
            
            if not response or "auth" not in response:
                raise ValueError("Invalid AWS authentication response")
            
            client_token = response["auth"]["client_token"]
            client.token = client_token
            
            return client_token
        except Exception as e:
            logger.error("AWS authentication failed", error=str(e))
            raise ValueError(f"AWS authentication failed: {str(e)}")
    
    def get_strategy_name(self) -> str:
        return "AWS IAM Authentication"
    
    def validate_config(self, config) -> bool:
        """Validate AWS authentication configuration."""
        return config.aws_role is not None


class LDAPAuthStrategy(VaultAuthStrategy):
    """Strategy for LDAP authentication."""
    
    def authenticate(self, client, config) -> str:
        """Authenticate using LDAP."""
        username = getattr(config, 'ldap_username', None)
        password = getattr(config, 'ldap_password', None)
        
        if not username or not password:
            raise ValueError("ldap_username and ldap_password required for LDAP authentication")
        
        try:
            response = client.auth.ldap.login(
                username=username,
                password=password.get_secret_value() if hasattr(password, 'get_secret_value') else password,
            )
            
            if not response or "auth" not in response:
                raise ValueError("Invalid LDAP authentication response")
            
            client_token = response["auth"]["client_token"]
            client.token = client_token
            
            return client_token
        except Exception as e:
            logger.error("LDAP authentication failed", error=str(e))
            raise ValueError(f"LDAP authentication failed: {str(e)}")
    
    def get_strategy_name(self) -> str:
        return "LDAP Authentication"
    
    def validate_config(self, config) -> bool:
        """Validate LDAP authentication configuration."""
        return (
            hasattr(config, 'ldap_username') and 
            hasattr(config, 'ldap_password') and
            config.ldap_username is not None and 
            config.ldap_password is not None
        )


class VaultAuthenticationEngine:
    """
    Engine for authenticating with Vault using Strategy pattern.
    
    REFACTORED: Replaces the 14-complexity if-elif chain in VaultClient._authenticate
    with a simple strategy lookup (Complexity: 3).
    """
    
    def __init__(self):
        """Initialize with all available authentication strategies."""
        self.strategies = {
            "token": TokenAuthStrategy(),
            "approle": AppRoleAuthStrategy(),
            "kubernetes": KubernetesAuthStrategy(),
            "aws": AWSAuthStrategy(),
            "ldap": LDAPAuthStrategy(),
        }
    
    def authenticate(self, client, config) -> str:
        """
        Authenticate with Vault using appropriate strategy.
        
        COMPLEXITY REDUCTION: This method replaces the original 14-complexity 
        if-elif chain with simple strategy lookup (Complexity: 3).
        
        Args:
            client: Vault client instance
            config: Vault configuration with authentication details
            
        Returns:
            Client token from successful authentication
            
        Raises:
            ValueError: If authentication method is unsupported or authentication fails
        """
        # Step 1: Validate client and config (Complexity: 1)
        if not client:
            raise ValueError("Vault client not initialized")
        
        auth_method = getattr(config, 'auth_method', 'token')
        
        # Step 2: Get strategy for authentication method (Complexity: 1)
        strategy = self.strategies.get(auth_method)
        if not strategy:
            raise ValueError(f"Unsupported authentication method: {auth_method}")
        
        # Step 3: Authenticate using strategy (Complexity: 1)
        try:
            # Validate configuration for this method
            if not strategy.validate_config(config):
                raise ValueError(f"Invalid configuration for {auth_method} authentication")
            
            client_token = strategy.authenticate(client, config)
            
            # Verify authentication was successful
            if not client.is_authenticated():
                raise ValueError("Authentication succeeded but client is not authenticated")
            
            logger.info("Successfully authenticated with Vault",
                       method=auth_method,
                       strategy=strategy.get_strategy_name())
            
            return client_token
            
        except Exception as e:
            logger.error("Vault authentication failed",
                        method=auth_method,
                        strategy=strategy.get_strategy_name(),
                        error=str(e))
            raise
    
    def get_supported_auth_methods(self) -> list[str]:
        """Get list of supported authentication methods."""
        return list(self.strategies.keys())
    
    def add_custom_strategy(self, auth_method: str, strategy: VaultAuthStrategy) -> None:
        """Add a custom authentication strategy."""
        self.strategies[auth_method] = strategy
        logger.info("Added custom auth strategy",
                   auth_method=auth_method,
                   strategy_name=strategy.get_strategy_name())
    
    def remove_strategy(self, auth_method: str) -> bool:
        """Remove an authentication strategy."""
        if auth_method in self.strategies:
            del self.strategies[auth_method]
            logger.info("Removed auth strategy", auth_method=auth_method)
            return True
        return False
    
    def validate_auth_config(self, config) -> Dict[str, bool]:
        """Validate configuration for all authentication methods."""
        validation_results = {}
        
        for auth_method, strategy in self.strategies.items():
            try:
                validation_results[auth_method] = strategy.validate_config(config)
            except Exception as e:
                logger.warning(f"Error validating {auth_method} config", error=str(e))
                validation_results[auth_method] = False
        
        return validation_results


def create_vault_auth_engine() -> VaultAuthenticationEngine:
    """
    Factory function to create a configured vault authentication engine.
    
    This is the main entry point for replacing the 14-complexity authentication method.
    
    Returns:
        Configured vault authentication engine
    """
    return VaultAuthenticationEngine()