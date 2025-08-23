"""Secure secrets management for the DotMac ISP Framework."""

import os
import secrets
import base64
import hashlib
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class SecretsManager:
    """Secure secrets management with encryption at rest."""

    def __init__(self, secrets_dir: Optional[Path] = None):
        """Initialize secrets manager with optional custom directory."""
        self.secrets_dir = secrets_dir or Path.home() / ".dotmac_isp" / "secrets"
        self.secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Set restrictive permissions on secrets directory
        os.chmod(self.secrets_dir, 0o700)

        self._master_key_file = self.secrets_dir / "master.key"
        self._secrets_file = self.secrets_dir / "secrets.enc"

    def _get_master_key(self) -> bytes:
        """Get or create master encryption key."""
        if self._master_key_file.exists():
            with open(self._master_key_file, "rb") as f:
                return f.read()
        else:
            # Generate new master key
            key = Fernet.generate_key()
            with open(self._master_key_file, "wb") as f:
                f.write(key)
            os.chmod(self._master_key_file, 0o600)
            logger.info("Generated new master key for secrets encryption")
            return key

    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher with master key."""
        master_key = self._get_master_key()
        return Fernet(master_key)

    def store_secret(self, name: str, value: str) -> None:
        """Store an encrypted secret."""
        cipher = self._get_cipher()
        encrypted_value = cipher.encrypt(value.encode())

        # Store in simple format: name=base64_encrypted_value
        secret_line = f"{name}={base64.b64encode(encrypted_value).decode()}\n"

        # Read existing secrets
        existing_secrets = {}
        if self._secrets_file.exists():
            with open(self._secrets_file, "r") as f:
                for line in f:
                    if "=" in line:
                        key, enc_val = line.strip().split("=", 1)
                        existing_secrets[key] = enc_val

        # Update with new secret
        existing_secrets[name] = base64.b64encode(encrypted_value).decode()

        # Write all secrets back
        with open(self._secrets_file, "w") as f:
            for key, enc_val in existing_secrets.items():
                f.write(f"{key}={enc_val}\n")

        os.chmod(self._secrets_file, 0o600)
        logger.info(f"Stored encrypted secret: {name}")

    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve and decrypt a secret."""
        if not self._secrets_file.exists():
            return None

        cipher = self._get_cipher()

        with open(self._secrets_file, "r") as f:
            for line in f:
                if line.startswith(f"{name}="):
                    _, encrypted_b64 = line.strip().split("=", 1)
                    try:
                        encrypted_value = base64.b64decode(encrypted_b64)
                        decrypted_value = cipher.decrypt(encrypted_value)
                        return decrypted_value.decode()
                    except Exception as e:
                        logger.error(f"Failed to decrypt secret {name}: {e}")
                        return None

        return None

    def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        if not self._secrets_file.exists():
            return False

        # Read all secrets except the one to delete
        remaining_secrets = {}
        found = False

        with open(self._secrets_file, "r") as f:
            for line in f:
                if "=" in line:
                    key, enc_val = line.strip().split("=", 1)
                    if key == name:
                        found = True
                    else:
                        remaining_secrets[key] = enc_val

        if found:
            # Rewrite file without deleted secret
            with open(self._secrets_file, "w") as f:
                for key, enc_val in remaining_secrets.items():
                    f.write(f"{key}={enc_val}\n")
            logger.info(f"Deleted secret: {name}")

        return found

    def list_secrets(self) -> list[str]:
        """List all stored secret names."""
        if not self._secrets_file.exists():
            return []

        secret_names = []
        with open(self._secrets_file, "r") as f:
            for line in f:
                if "=" in line:
                    name = line.split("=", 1)[0]
                    secret_names.append(name)

        return secret_names


def generate_jwt_secret() -> str:
    """Generate a cryptographically secure JWT secret key."""
    return secrets.token_urlsafe(64)


def generate_database_password() -> str:
    """Generate a secure database password."""
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(48)


def get_jwt_secret() -> str:
    """Get JWT secret from environment or secrets manager."""
    # First check environment
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if jwt_secret and jwt_secret != "dev-secret-key-not-for-production-use":
        return jwt_secret

    # Check secrets manager
    secrets_manager = SecretsManager()
    stored_secret = secrets_manager.get_secret("jwt_secret_key")
    if stored_secret:
        return stored_secret

    # Generate and store new secret
    new_secret = generate_jwt_secret()
    secrets_manager.store_secret("jwt_secret_key", new_secret)

    logger.warning(
        "Generated new JWT secret key. Update your environment variables:\n"
        f"export JWT_SECRET_KEY='{new_secret}'"
    )

    return new_secret


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash password with salt using PBKDF2."""
    if salt is None:
        salt = secrets.token_hex(16)
    else:
        salt = salt.encode() if isinstance(salt, str) else salt

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode() if isinstance(salt, str) else salt,
        iterations=100000,
    )

    password_hash = base64.b64encode(kdf.derive(password.encode())).decode()
    salt_str = salt if isinstance(salt, str) else salt.decode()

    return password_hash, salt_str


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify password against stored hash."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)


def setup_production_secrets() -> dict[str, str]:
    """Set up all required secrets for production deployment."""
    secrets_manager = SecretsManager()

    production_secrets = {
        "jwt_secret_key": generate_jwt_secret(),
        "database_password": generate_database_password(),
        "redis_password": generate_database_password(),
        "admin_api_key": generate_api_key(),
        "webhook_secret": generate_jwt_secret(),
        "encryption_key": generate_jwt_secret(),
    }

    # Store all secrets
    for name, value in production_secrets.items():
        secrets_manager.store_secret(name, value)

    logger.info("Generated and stored all production secrets")
    return production_secrets


# Global secrets manager instance
_secrets_manager = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


# Convenience functions
def store_secret(name: str, value: str) -> None:
    """Store a secret using global manager."""
    get_secrets_manager().store_secret(name, value)


def get_secret(name: str) -> Optional[str]:
    """Get a secret using global manager."""
    return get_secrets_manager().get_secret(name)


def delete_secret(name: str) -> bool:
    """Delete a secret using global manager."""
    return get_secrets_manager().delete_secret(name)


def list_secrets() -> list[str]:
    """List all secrets using global manager."""
    return get_secrets_manager().list_secrets()
