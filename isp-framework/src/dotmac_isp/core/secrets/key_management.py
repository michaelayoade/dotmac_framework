"""
Key Management Module

Extracted from encryption.py for better organization.
Handles encryption key generation, rotation, storage, and retrieval.
"""

import base64
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, MultiFernet
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from dotmac_isp.sdks.platform.utils.datetime_compat import UTC


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""

    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"


@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata"""

    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    created_at: datetime
    expires_at: datetime | None = None
    is_active: bool = True
    version: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if key has expired"""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert key to dictionary (excluding sensitive data)"""
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "version": self.version,
            "metadata": self.metadata,
            "is_expired": self.is_expired(),
        }


class KeyManager:
    """Encryption key management service"""

    def __init__(self, master_key: bytes | None = None):
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("Cryptography library not available")

        self.master_key = master_key or self._generate_master_key()
        self.keys: dict[str, EncryptionKey] = {}
        self.active_keys: dict[EncryptionAlgorithm, str] = {}
        self._fernet = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))

        # Generate default keys for each algorithm
        self._initialize_default_keys()

    def _generate_master_key(self) -> bytes:
        """Generate a new master key"""
        master_key = secrets.token_bytes(32)
        logger.info("Generated new master key")
        return master_key

    def _initialize_default_keys(self):
        """Initialize default keys for each algorithm"""
        for algorithm in EncryptionAlgorithm:
            try:
                key = self.generate_key(algorithm)
                self.active_keys[algorithm] = key.key_id
                logger.info(
                    "Generated default key",
                    algorithm=algorithm.value,
                    key_id=key.key_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to generate default key",
                    algorithm=algorithm.value,
                    error=str(e),
                )

    def generate_key(
        self, algorithm: EncryptionAlgorithm, expires_in_days: int | None = None
    ) -> EncryptionKey:
        """Generate a new encryption key"""
        key_id = self._generate_key_id()

        if algorithm == EncryptionAlgorithm.FERNET:
            key_data = Fernet.generate_key()
        elif algorithm == EncryptionAlgorithm.AES_256_GCM:
            key_data = secrets.token_bytes(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.RSA_2048:
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            key_data = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        elif algorithm == EncryptionAlgorithm.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=4096, backend=default_backend()
            )
            key_data = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        # Create key object
        encryption_key = EncryptionKey(
            key_id=key_id,
            algorithm=algorithm,
            key_data=key_data,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
        )

        # Store key
        self.keys[key_id] = encryption_key

        logger.info(
            "Generated encryption key",
            key_id=key_id,
            algorithm=algorithm.value,
            expires_at=expires_at.isoformat() if expires_at else None,
        )

        return encryption_key

    def get_key(self, key_id: str) -> EncryptionKey | None:
        """Get a key by ID"""
        key = self.keys.get(key_id)

        if key and key.is_expired():
            logger.warning("Attempted to use expired key", key_id=key_id)
            return None

        return key

    def get_active_key(self, algorithm: EncryptionAlgorithm) -> EncryptionKey | None:
        """Get the active key for an algorithm"""
        key_id = self.active_keys.get(algorithm)
        if not key_id:
            return None

        return self.get_key(key_id)

    def rotate_key(
        self, algorithm: EncryptionAlgorithm, expires_in_days: int | None = None
    ) -> EncryptionKey:
        """Rotate the active key for an algorithm"""
        # Deactivate current key
        current_key_id = self.active_keys.get(algorithm)
        if current_key_id and current_key_id in self.keys:
            self.keys[current_key_id].is_active = False
            logger.info(
                "Deactivated old key", key_id=current_key_id, algorithm=algorithm.value
            )

        # Generate new key
        new_key = self.generate_key(algorithm, expires_in_days)
        self.active_keys[algorithm] = new_key.key_id

        logger.info(
            "Key rotated",
            algorithm=algorithm.value,
            old_key_id=current_key_id,
            new_key_id=new_key.key_id,
        )

        return new_key

    def list_keys(
        self, algorithm: EncryptionAlgorithm | None = None
    ) -> list[EncryptionKey]:
        """List all keys, optionally filtered by algorithm"""
        keys = list(self.keys.values())

        if algorithm:
            keys = [k for k in keys if k.algorithm == algorithm]

        return sorted(keys, key=lambda k: k.created_at, reverse=True)

    def cleanup_expired_keys(self) -> int:
        """Remove expired keys and return count"""
        expired_keys = [
            key_id
            for key_id, key in self.keys.items()
            if key.is_expired() and not key.is_active
        ]

        for key_id in expired_keys:
            del self.keys[key_id]
            logger.info("Removed expired key", key_id=key_id)

        return len(expired_keys)

    def get_key_stats(self) -> dict[str, Any]:
        """Get key management statistics"""
        total_keys = len(self.keys)
        active_keys = sum(1 for k in self.keys.values() if k.is_active)
        expired_keys = sum(1 for k in self.keys.values() if k.is_expired())

        by_algorithm = {}
        for algorithm in EncryptionAlgorithm:
            count = sum(1 for k in self.keys.values() if k.algorithm == algorithm)
            by_algorithm[algorithm.value] = count

        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "keys_by_algorithm": by_algorithm,
            "active_key_ids": dict(self.active_keys),
        }

    def export_public_keys(self) -> dict[str, str]:
        """Export public keys for RSA algorithms"""
        public_keys = {}

        for key_id, key in self.keys.items():
            if key.algorithm in [
                EncryptionAlgorithm.RSA_2048,
                EncryptionAlgorithm.RSA_4096,
            ]:
                try:
                    private_key = serialization.load_pem_private_key(
                        key.key_data, password=None, backend=default_backend()
                    )
                    public_key = private_key.public_key()
                    public_pem = public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                    public_keys[key_id] = public_pem.decode("utf-8")
                except Exception as e:
                    logger.warning(
                        "Failed to extract public key", key_id=key_id, error=str(e)
                    )

        return public_keys

    def _generate_key_id(self) -> str:
        """Generate unique key identifier"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"key_{timestamp}_{random_suffix}"

    async def auto_rotate_keys(self, max_age_days: int = 90):
        """Automatically rotate keys older than max_age_days"""
        cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
        rotated_count = 0

        for algorithm in EncryptionAlgorithm:
            active_key = self.get_active_key(algorithm)
            if active_key and active_key.created_at < cutoff_date:
                try:
                    self.rotate_key(algorithm, expires_in_days=max_age_days)
                    rotated_count += 1
                    logger.info("Auto-rotated key", algorithm=algorithm.value)
                except Exception as e:
                    logger.error(
                        "Failed to auto-rotate key",
                        algorithm=algorithm.value,
                        error=str(e),
                    )

        return rotated_count


__all__ = ["EncryptionAlgorithm", "EncryptionKey", "KeyManager"]
