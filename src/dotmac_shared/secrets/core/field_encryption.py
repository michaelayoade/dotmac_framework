"""
Field-Level Encryption Module

Extracted from encryption.py for better organization.
Provides field-level encryption decorators and utilities for Pydantic models.
"""

import base64
import hashlib
import json
import secrets
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional, TypeVar, Union

# Safe datetime handling
try:
    from datetime import timezone

    UTC = timezone.utc
except ImportError:
    # Python < 3.7 fallback
    import pytz

    UTC = pytz.UTC

# Handle optional dependencies gracefully
try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object
    PYDANTIC_AVAILABLE = False

    # Mock decorators and functions
    def field_validator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def Field(*args, **kwargs):
        return kwargs.get("default", None)

    class ConfigDict:
        """ConfigDict implementation."""

        def __init__(self, **kwargs):
            pass


try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None
    InvalidSignature = Exception

T = TypeVar("T", bound=BaseModel)


class DataClassification:
    """Data classification levels for encryption policies"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"

    @classmethod
    def get_encryption_required_levels(cls) -> List[str]:
        """Get classification levels that require encryption."""
        return [cls.CONFIDENTIAL, cls.RESTRICTED, cls.TOP_SECRET]

    @classmethod
    def get_all_levels(cls) -> List[str]:
        """Get all classification levels."""
        return [
            cls.PUBLIC,
            cls.INTERNAL,
            cls.CONFIDENTIAL,
            cls.RESTRICTED,
            cls.TOP_SECRET,
        ]


if PYDANTIC_AVAILABLE:

    class EncryptedField(BaseModel):
        """Represents an encrypted field with metadata"""

        encrypted_data: str = Field(..., description="Base64 encoded encrypted data")
        key_id: str = Field(..., description="Encryption key identifier")
        algorithm: str = Field(..., description="Encryption algorithm used")
        iv: Optional[str] = Field(None, description="Initialization vector if used")
        created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

        model_config = ConfigDict(
            json_encoders={
                datetime: lambda v: v.isoformat(),
            }
        )

        @field_validator("encrypted_data")
        def validate_encrypted_data(cls, v):
            """Validate encrypted data is base64 encoded"""
            try:
                base64.b64decode(v)
                return v
            except Exception:
                raise ValueError("encrypted_data must be valid base64")

else:
    # Fallback class when Pydantic is not available
    class EncryptedField:
        """EncryptedField implementation."""

        def __init__(
            self,
            encrypted_data: str,
            key_id: str,
            algorithm: str,
            iv: Optional[str] = None,
        ):
            self.encrypted_data = encrypted_data
            self.key_id = key_id
            self.algorithm = algorithm
            self.iv = iv
            self.created_at = datetime.now(UTC)


class FieldEncryptionManager:
    """
    Manages field-level encryption and decryption operations.

    Features:
    - Multiple encryption algorithms (Fernet, AES-GCM)
    - Key derivation from master keys
    - Automatic IV generation
    - Key rotation support
    - Classification-based encryption policies
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the field encryption manager.

        Args:
            master_key: Master encryption key (base64 encoded)
        """
        self._master_key = master_key
        self._key_cache: Dict[str, bytes] = {}
        self._default_algorithm = "Fernet"

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning(
                "Cryptography library not available, encryption functionality will be limited"
            )

    def generate_master_key(self) -> str:
        """
        Generate a new master key.

        Returns:
            Base64 encoded master key
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            # Fallback to secrets module
            key_bytes = secrets.token_bytes(32)
            return base64.b64encode(key_bytes).decode()

        key = Fernet.generate_key()
        return key.decode()

    def derive_key(self, key_id: str, context: Optional[str] = None) -> bytes:
        """
        Derive an encryption key from the master key.

        Args:
            key_id: Unique identifier for the derived key
            context: Additional context for key derivation

        Returns:
            Derived encryption key
        """
        cache_key = f"{key_id}:{context or ''}"

        if cache_key in self._key_cache:
            return self._key_cache[cache_key]

        if not self._master_key:
            raise ValueError("Master key not configured")

        if not CRYPTOGRAPHY_AVAILABLE:
            # Simple fallback using hashlib
            data = f"{self._master_key}:{key_id}:{context or ''}".encode()
            key = hashlib.sha256(data).digest()
            self._key_cache[cache_key] = key
            return key

        # Use PBKDF2 for proper key derivation
        master_key_bytes = base64.b64decode(self._master_key)
        salt = hashlib.sha256(f"{key_id}:{context or ''}".encode()).digest()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        key = kdf.derive(master_key_bytes)
        self._key_cache[cache_key] = key
        return key

    def encrypt_field(
        self,
        plaintext: str,
        key_id: str,
        algorithm: str = "Fernet",
        context: Optional[str] = None,
    ) -> EncryptedField:
        """
        Encrypt a field value.

        Args:
            plaintext: Value to encrypt
            key_id: Key identifier for encryption
            algorithm: Encryption algorithm to use
            context: Additional context

        Returns:
            Encrypted field object
        """
        if not CRYPTOGRAPHY_AVAILABLE and algorithm != "Base64":
            logger.warning(
                f"Cryptography not available, falling back to Base64 encoding"
            )
            algorithm = "Base64"

        try:
            if algorithm == "Fernet":
                key = self.derive_key(key_id, context)
                fernet_key = base64.urlsafe_b64encode(key[:32])
                fernet = Fernet(fernet_key)

                encrypted_bytes = fernet.encrypt(plaintext.encode())
                encrypted_data = base64.b64encode(encrypted_bytes).decode()
                iv = None

            elif algorithm == "AES-GCM":
                key = self.derive_key(key_id, context)
                iv = secrets.token_bytes(12)  # 96-bit IV for GCM

                cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
                encryptor = cipher.encryptor()

                ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()

                # Combine ciphertext and auth tag
                encrypted_bytes = ciphertext + encryptor.tag
                encrypted_data = base64.b64encode(encrypted_bytes).decode()
                iv_b64 = base64.b64encode(iv).decode()

            elif algorithm == "Base64":
                # Fallback encoding (not secure encryption!)
                encrypted_data = base64.b64encode(plaintext.encode()).decode()
                iv = None

            else:
                raise ValueError(f"Unsupported encryption algorithm: {algorithm}")

            return EncryptedField(
                encrypted_data=encrypted_data,
                key_id=key_id,
                algorithm=algorithm,
                iv=iv,
            )

        except Exception as e:
            logger.error(f"Field encryption failed: {e}")
            raise

    def decrypt_field(
        self,
        encrypted_field: Union[EncryptedField, Dict[str, Any]],
        context: Optional[str] = None,
    ) -> str:
        """
        Decrypt a field value.

        Args:
            encrypted_field: Encrypted field object or dict
            context: Additional context

        Returns:
            Decrypted plaintext value
        """
        # Handle dict input (for JSON serialization compatibility)
        if isinstance(encrypted_field, dict):
            encrypted_data = encrypted_field["encrypted_data"]
            key_id = encrypted_field["key_id"]
            algorithm = encrypted_field["algorithm"]
            iv = encrypted_field.get("iv")
        else:
            encrypted_data = encrypted_field.encrypted_data
            key_id = encrypted_field.key_id
            algorithm = encrypted_field.algorithm
            iv = encrypted_field.iv

        if not CRYPTOGRAPHY_AVAILABLE and algorithm != "Base64":
            logger.warning(f"Cryptography not available, attempting Base64 decode")
            algorithm = "Base64"

        try:
            if algorithm == "Fernet":
                key = self.derive_key(key_id, context)
                fernet_key = base64.urlsafe_b64encode(key[:32])
                fernet = Fernet(fernet_key)

                encrypted_bytes = base64.b64decode(encrypted_data)
                plaintext_bytes = fernet.decrypt(encrypted_bytes)
                return plaintext_bytes.decode()

            elif algorithm == "AES-GCM":
                key = self.derive_key(key_id, context)
                iv_bytes = base64.b64decode(iv)
                encrypted_bytes = base64.b64decode(encrypted_data)

                # Split ciphertext and auth tag
                ciphertext = encrypted_bytes[:-16]
                tag = encrypted_bytes[-16:]

                cipher = Cipher(algorithms.AES(key), modes.GCM(iv_bytes, tag))
                decryptor = cipher.decryptor()

                plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()
                return plaintext_bytes.decode()

            elif algorithm == "Base64":
                # Fallback decoding (not secure decryption!)
                plaintext_bytes = base64.b64decode(encrypted_data)
                return plaintext_bytes.decode()

            else:
                raise ValueError(f"Unsupported encryption algorithm: {algorithm}")

        except Exception as e:
            logger.error(f"Field decryption failed: {e}")
            raise

    def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str,
        encrypted_field: EncryptedField,
        context: Optional[str] = None,
    ) -> EncryptedField:
        """
        Rotate encryption key for a field.

        Args:
            old_key_id: Current key identifier
            new_key_id: New key identifier
            encrypted_field: Field to re-encrypt
            context: Additional context

        Returns:
            Re-encrypted field with new key
        """
        # Decrypt with old key
        plaintext = self.decrypt_field(encrypted_field, context)

        # Re-encrypt with new key
        return self.encrypt_field(
            plaintext, new_key_id, encrypted_field.algorithm, context
        )


# Global encryption manager instance
_encryption_manager: Optional[FieldEncryptionManager] = None


def get_encryption_manager() -> FieldEncryptionManager:
    """Get the global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = FieldEncryptionManager()
    return _encryption_manager


def set_encryption_manager(manager: FieldEncryptionManager) -> None:
    """Set the global encryption manager instance."""
    global _encryption_manager
    _encryption_manager = manager


def encrypted_field(
    classification: str = DataClassification.CONFIDENTIAL,
    key_id: Optional[str] = None,
    algorithm: str = "Fernet",
    **kwargs,
) -> Any:
    """
    Create an encrypted field descriptor for Pydantic models.

    Args:
        classification: Data classification level
        key_id: Encryption key identifier
        algorithm: Encryption algorithm to use
        **kwargs: Additional Field arguments

    Returns:
        Pydantic Field configured for encryption
    """
    if not PYDANTIC_AVAILABLE:
        logger.warning("Pydantic not available, encrypted field will not work properly")
        return kwargs.get("default", None)

    # Store encryption metadata in field info
    kwargs.setdefault(
        "description", f"Encrypted field (classification: {classification})"
    )
    kwargs["json_schema_extra"] = {
        "classification": classification,
        "encrypted": True,
        "algorithm": algorithm,
        "key_id": key_id,
    }

    return Field(**kwargs)


def encrypt_sensitive_fields(
    model: BaseModel, key_id: Optional[str] = None
) -> BaseModel:
    """
    Encrypt sensitive fields in a Pydantic model.

    Args:
        model: Pydantic model instance
        key_id: Optional key identifier for encryption

    Returns:
        Model with sensitive fields encrypted
    """
    if not PYDANTIC_AVAILABLE:
        logger.warning("Pydantic not available, cannot encrypt model fields")
        return model

    manager = get_encryption_manager()
    model_dict = model.model_dump()

    # Get field information
    for field_name, field_info in model.model_fields.items():
        if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
            extra = field_info.json_schema_extra
            if extra.get("encrypted", False):
                field_value = model_dict.get(field_name)
                if field_value is not None and not isinstance(
                    field_value, (dict, EncryptedField)
                ):
                    # Field needs encryption
                    field_key_id = key_id or extra.get("key_id", field_name)
                    algorithm = extra.get("algorithm", "Fernet")

                    encrypted_field = manager.encrypt_field(
                        str(field_value), field_key_id, algorithm
                    )

                    # Store as dict for JSON serialization
                    model_dict[field_name] = {
                        "encrypted_data": encrypted_field.encrypted_data,
                        "key_id": encrypted_field.key_id,
                        "algorithm": encrypted_field.algorithm,
                        "iv": encrypted_field.iv,
                        "created_at": encrypted_field.created_at.isoformat(),
                    }

    # Return new model instance with encrypted fields
    return model.__class__(**model_dict)


def decrypt_sensitive_fields(model: BaseModel) -> BaseModel:
    """
    Decrypt sensitive fields in a Pydantic model.

    Args:
        model: Pydantic model instance with encrypted fields

    Returns:
        Model with sensitive fields decrypted
    """
    if not PYDANTIC_AVAILABLE:
        logger.warning("Pydantic not available, cannot decrypt model fields")
        return model

    manager = get_encryption_manager()
    model_dict = model.model_dump()

    # Get field information
    for field_name, field_info in model.model_fields.items():
        if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
            extra = field_info.json_schema_extra
            if extra.get("encrypted", False):
                field_value = model_dict.get(field_name)
                if field_value is not None and isinstance(field_value, dict):
                    # Field needs decryption
                    if "encrypted_data" in field_value:
                        try:
                            decrypted_value = manager.decrypt_field(field_value)
                            model_dict[field_name] = decrypted_value
                        except Exception as e:
                            logger.error(f"Failed to decrypt field {field_name}: {e}")
                            # Keep encrypted value if decryption fails

    # Return new model instance with decrypted fields
    return model.__class__(**model_dict)


def secure_compare(a: str, b: str) -> bool:
    """
    Securely compare two strings to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)

    return result == 0


def generate_salt(length: int = 32) -> str:
    """
    Generate a cryptographically secure random salt.

    Args:
        length: Length of salt in bytes

    Returns:
        Base64 encoded salt
    """
    salt_bytes = secrets.token_bytes(length)
    return base64.b64encode(salt_bytes).decode()


def hash_with_salt(data: str, salt: str) -> str:
    """
    Hash data with a salt using SHA-256.

    Args:
        data: Data to hash
        salt: Salt to use

    Returns:
        Base64 encoded hash
    """
    combined = f"{data}:{salt}".encode()
    hash_bytes = hashlib.sha256(combined).digest()
    return base64.b64encode(hash_bytes).decode()


class SecureString:
    """
    A string wrapper that attempts to clear memory on deletion.

    Note: This provides basic protection but cannot guarantee complete
    memory clearing due to Python's memory management.
    """

    def __init__(self, value: str):
        self._value = value
        self._cleared = False

    def get(self) -> str:
        """Get the string value."""
        if self._cleared:
            raise ValueError("SecureString has been cleared")
        return self._value

    def clear(self) -> None:
        """Clear the string value from memory."""
        if not self._cleared:
            # Basic attempt to overwrite memory
            self._value = "0" * len(self._value)
            self._cleared = True

    def __del__(self):
        """Clear on deletion."""
        self.clear()

    def __str__(self) -> str:
        return "[SECURE STRING]" if not self._cleared else "[CLEARED]"

    def __repr__(self) -> str:
        return f"SecureString(cleared={self._cleared})"
