"""
OpenBao client for secure secrets management.
Provides a unified interface for all DotMac services to retrieve secrets.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock, Thread
from functools import lru_cache
import hashlib

import hvac
from hvac.exceptions import InvalidPath, Forbidden, InvalidRequest

logger = logging.getLogger(__name__)


@dataclass
class Secret:
    """Represents a secret from OpenBao."""
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    lease_duration: int
    renewable: bool
    created_at: datetime
    
    def is_expired(self) -> bool:
        """Check if secret lease has expired."""
        if self.lease_duration == 0:
            return False  # No expiration
        expiry = self.created_at + timedelta(seconds=self.lease_duration)
        return datetime.now() > expiry
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from secret data."""
        return self.data.get(key, default)


class OpenBaoClient:
    """
    OpenBao client for DotMac services.
    Handles authentication, secret retrieval, and automatic renewal.
    """
    
    def __init__(
        self,
        service_name: str,
        bao_addr: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        namespace: Optional[str] = None,
        auto_renew: bool = True,
        cache_ttl: int = 300
    ):
        """
        Initialize OpenBao client.
        
        Args:
            service_name: Name of the service
            bao_addr: OpenBao server address
            role_id: AppRole role ID
            secret_id: AppRole secret ID
            namespace: OpenBao namespace (for multi-tenant)
            auto_renew: Enable automatic token renewal
            cache_ttl: Cache TTL in seconds
        """
        self.service_name = service_name
        self.bao_addr = bao_addr or os.getenv("BAO_ADDR", "http://localhost:8200")
        self.namespace = namespace or os.getenv("BAO_NAMESPACE")
        self.auto_renew = auto_renew
        self.cache_ttl = cache_ttl
        
        # Authentication credentials
        self.role_id = role_id or self._get_role_id()
        self.secret_id = secret_id or self._get_secret_id()
        
        # Initialize client
        self.client = hvac.Client(
            url=self.bao_addr,
            namespace=self.namespace
        )
        
        # Secret cache
        self._cache: Dict[str, Secret] = {}
        self._cache_lock = Lock()
        
        # Token renewal
        self._renewal_thread: Optional[Thread] = None
        self._stop_renewal = False
        
        # Authenticate
        self._authenticate()
        
        logger.info(f"OpenBao client initialized for {service_name}")
    
    def _get_role_id(self) -> str:
        """Get role ID from file or environment."""
        # Try environment variable first
        role_id = os.getenv(f"{self.service_name.upper()}_ROLE_ID")
        if role_id:
            return role_id
        
        # Try file
        role_file = f"/var/run/secrets/openbao/{self.service_name}-role-id"
        if os.path.exists(role_file):
            with open(role_file, "r") as f:
                return f.read().strip()
        
        # Fallback to generic env
        return os.getenv("BAO_ROLE_ID", "")
    
    def _get_secret_id(self) -> str:
        """Get secret ID from file or environment."""
        # Try environment variable first
        secret_id = os.getenv(f"{self.service_name.upper()}_SECRET_ID")
        if secret_id:
            return secret_id
        
        # Try file
        secret_file = f"/var/run/secrets/openbao/{self.service_name}-secret-id"
        if os.path.exists(secret_file):
            with open(secret_file, "r") as f:
                return f.read().strip()
        
        # Fallback to generic env
        return os.getenv("BAO_SECRET_ID", "")
    
    def _authenticate(self):
        """Authenticate with OpenBao using AppRole."""
        try:
            # Try token auth first (for development)
            token = os.getenv("BAO_TOKEN")
            if token:
                self.client.token = token
                if self.client.is_authenticated():
                    logger.info("Authenticated with token")
                    self._start_renewal()
                    return
            
            # Use AppRole authentication
            if not self.role_id or not self.secret_id:
                raise ValueError(
                    f"Missing AppRole credentials for {self.service_name}. "
                    "Set BAO_TOKEN or provide role_id and secret_id."
                )
            
            response = self.client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id
            )
            
            logger.info(f"Authenticated via AppRole for {self.service_name}")
            
            # Start token renewal if enabled
            if self.auto_renew:
                self._start_renewal()
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def _start_renewal(self):
        """Start automatic token renewal thread."""
        if not self.auto_renew:
            return
        
        def renew_token():
            while not self._stop_renewal:
                try:
                    # Renew token
                    self.client.auth.token.renew_self()
                    logger.debug("Token renewed successfully")
                    
                    # Sleep for half the TTL
                    ttl = self.client.auth.token.lookup_self()["data"]["ttl"]
                    time.sleep(max(ttl / 2, 60))
                    
                except Exception as e:
                    logger.error(f"Token renewal failed: {e}")
                    time.sleep(60)  # Retry after 1 minute
        
        self._renewal_thread = Thread(target=renew_token, daemon=True)
        self._renewal_thread.start()
    
    def _cache_key(self, path: str, **kwargs) -> str:
        """Generate cache key for a secret."""
        key_data = f"{path}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Secret]:
        """Get secret from cache if valid."""
        with self._cache_lock:
            secret = self._cache.get(cache_key)
            if secret:
                # Check if expired
                if secret.is_expired():
                    del self._cache[cache_key]
                    return None
                
                # Check cache TTL
                age = (datetime.now() - secret.created_at).total_seconds()
                if age > self.cache_ttl:
                    del self._cache[cache_key]
                    return None
                
                return secret
        return None
    
    def _add_to_cache(self, cache_key: str, secret: Secret):
        """Add secret to cache."""
        with self._cache_lock:
            self._cache[cache_key] = secret
    
    def get_secret(self, path: str, mount_point: str = "dotmac") -> Secret:
        """
        Get a secret from OpenBao.
        
        Args:
            path: Secret path
            mount_point: KV mount point
            
        Returns:
            Secret object
        """
        # Check cache
        cache_key = self._cache_key(path, mount_point=mount_point)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Using cached secret for {path}")
            return cached
        
        try:
            # Read from OpenBao
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount_point
            )
            
            secret = Secret(
                data=response["data"]["data"],
                metadata=response["data"]["metadata"],
                lease_duration=response.get("lease_duration", 0),
                renewable=response.get("renewable", False),
                created_at=datetime.now()
            )
            
            # Cache the secret
            self._add_to_cache(cache_key, secret)
            
            logger.debug(f"Retrieved secret from {path}")
            return secret
            
        except InvalidPath:
            logger.error(f"Secret not found at {path}")
            raise
        except Forbidden:
            logger.error(f"Access denied to {path}")
            raise
        except Exception as e:
            logger.error(f"Failed to get secret from {path}: {e}")
            raise
    
    def get_database_credentials(self, role: Optional[str] = None) -> Dict[str, str]:
        """
        Get dynamic database credentials.
        
        Args:
            role: Database role name (defaults to service name)
            
        Returns:
            Dictionary with username and password
        """
        role = role or self.service_name
        
        try:
            response = self.client.secrets.database.generate_credentials(
                name=role
            )
            
            return {
                "username": response["data"]["username"],
                "password": response["data"]["password"],
                "ttl": response["lease_duration"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get database credentials: {e}")
            raise
    
    def encrypt(self, plaintext: str, key_name: str = "dotmac") -> str:
        """
        Encrypt data using Transit engine.
        
        Args:
            plaintext: Data to encrypt
            key_name: Transit key name
            
        Returns:
            Ciphertext
        """
        try:
            import base64
            
            # Encode plaintext to base64
            encoded = base64.b64encode(plaintext.encode()).decode()
            
            # Encrypt using transit
            response = self.client.secrets.transit.encrypt_data(
                name=key_name,
                plaintext=encoded
            )
            
            return response["data"]["ciphertext"]
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str, key_name: str = "dotmac") -> str:
        """
        Decrypt data using Transit engine.
        
        Args:
            ciphertext: Data to decrypt
            key_name: Transit key name
            
        Returns:
            Plaintext
        """
        try:
            import base64
            
            # Decrypt using transit
            response = self.client.secrets.transit.decrypt_data(
                name=key_name,
                ciphertext=ciphertext
            )
            
            # Decode from base64
            plaintext = base64.b64decode(response["data"]["plaintext"]).decode()
            
            return plaintext
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def get_service_config(self) -> Dict[str, Any]:
        """
        Get complete service configuration from OpenBao.
        
        Returns:
            Dictionary with all service configuration
        """
        config = {}
        
        # Get service-specific secrets
        try:
            service_secret = self.get_secret(self.service_name)
            config.update(service_secret.data)
        except:
            logger.warning(f"No service-specific secrets for {self.service_name}")
        
        # Get JWT configuration
        try:
            jwt_secret = self.get_secret("jwt")
            config["jwt_secret_key"] = jwt_secret.get("secret_key")
            config["jwt_algorithm"] = jwt_secret.get("algorithm", "HS256")
            config["jwt_issuer"] = jwt_secret.get("issuer")
            config["jwt_audience"] = jwt_secret.get("audience")
        except:
            logger.warning("No JWT configuration found")
        
        # Get Redis configuration
        try:
            redis_secret = self.get_secret("redis")
            config["redis_password"] = redis_secret.get("password")
            config["redis_max_connections"] = redis_secret.get("max_connections", 100)
        except:
            logger.warning("No Redis configuration found")
        
        # Get observability configuration
        try:
            obs_secret = self.get_secret("observability")
            config["signoz_endpoint"] = obs_secret.get("signoz_endpoint")
            config["signoz_access_token"] = obs_secret.get("signoz_access_token")
            config["trace_sampling_rate"] = obs_secret.get("trace_sampling_rate", 0.1)
        except:
            logger.warning("No observability configuration found")
        
        # Get external API keys if needed
        try:
            external_secret = self.get_secret("external")
            config.update(external_secret.data)
        except:
            logger.warning("No external API configuration found")
        
        return config
    
    def close(self):
        """Close the client and stop renewal thread."""
        self._stop_renewal = True
        if self._renewal_thread:
            self._renewal_thread.join(timeout=5)
        logger.info(f"OpenBao client closed for {self.service_name}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance management
_instances: Dict[str, OpenBaoClient] = {}
_lock = Lock()


def get_openbao_client(
    service_name: Optional[str] = None,
    force_new: bool = False
) -> OpenBaoClient:
    """
    Get or create an OpenBao client instance.
    
    Args:
        service_name: Service name (auto-detected if not provided)
        force_new: Force creation of new instance
        
    Returns:
        OpenBaoClient instance
    """
    if not service_name:
        service_name = os.getenv("SERVICE_NAME", "unknown")
    
    if not force_new:
        with _lock:
            if service_name in _instances:
                return _instances[service_name]
    
    # Create new instance
    client = OpenBaoClient(service_name)
    
    with _lock:
        _instances[service_name] = client
    
    return client


# Convenience functions
def get_secret(path: str, service_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get a secret from OpenBao.
    
    Args:
        path: Secret path
        service_name: Service name for client
        
    Returns:
        Secret data dictionary
    """
    client = get_openbao_client(service_name)
    secret = client.get_secret(path)
    return secret.data


def get_database_url(service_name: Optional[str] = None) -> str:
    """
    Get database URL with dynamic credentials from OpenBao.
    
    Args:
        service_name: Service name
        
    Returns:
        PostgreSQL connection URL
    """
    client = get_openbao_client(service_name)
    
    # Get dynamic credentials
    creds = client.get_database_credentials()
    
    # Get base database configuration
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", f"dotmac_{service_name or 'db'}")
    
    # Build URL with dynamic credentials
    return (
        f"postgresql://{creds['username']}:{creds['password']}@"
        f"{db_host}:{db_port}/{db_name}"
    )


def encrypt_pii(data: str, service_name: Optional[str] = None) -> str:
    """
    Encrypt PII data using OpenBao Transit.
    
    Args:
        data: Data to encrypt
        service_name: Service name
        
    Returns:
        Encrypted ciphertext
    """
    client = get_openbao_client(service_name)
    return client.encrypt(data)


def decrypt_pii(ciphertext: str, service_name: Optional[str] = None) -> str:
    """
    Decrypt PII data using OpenBao Transit.
    
    Args:
        ciphertext: Encrypted data
        service_name: Service name
        
    Returns:
        Decrypted plaintext
    """
    client = get_openbao_client(service_name)
    return client.decrypt(ciphertext)


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenBao client testing")
    parser.add_argument("--service", default="test", help="Service name")
    parser.add_argument("--get-secret", help="Get a secret by path")
    parser.add_argument("--get-db-creds", action="store_true", help="Get database credentials")
    parser.add_argument("--encrypt", help="Encrypt text")
    parser.add_argument("--decrypt", help="Decrypt ciphertext")
    parser.add_argument("--get-config", action="store_true", help="Get service configuration")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        with OpenBaoClient(args.service) as client:
            if args.get_secret:
                secret = client.get_secret(args.get_secret)
                print(f"Secret data: {json.dumps(secret.data, indent=2)}")
            
            elif args.get_db_creds:
                creds = client.get_database_credentials()
                print(f"Database credentials: {json.dumps(creds, indent=2)}")
            
            elif args.encrypt:
                ciphertext = client.encrypt(args.encrypt)
                print(f"Encrypted: {ciphertext}")
            
            elif args.decrypt:
                plaintext = client.decrypt(args.decrypt)
                print(f"Decrypted: {plaintext}")
            
            elif args.get_config:
                config = client.get_service_config()
                # Redact sensitive values
                for key in config:
                    if any(s in key.lower() for s in ["secret", "key", "password", "token"]):
                        config[key] = "***REDACTED***"
                print(f"Service configuration: {json.dumps(config, indent=2)}")
            
            else:
                print("No action specified. Use --help for options.")
                
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)