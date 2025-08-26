"""
Configuration encryption and sensitive data protection.
Provides field-level encryption for configuration values and secure handling.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union, List, Set
from datetime import datetime
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from pydantic import BaseModel, Field
from enum import Enum
import re

logger = logging.getLogger(__name__, timezone)


class FieldEncryptionLevel(str, Enum):
    """Encryption levels for configuration fields."""

    NONE = "none"  # No encryption
    BASIC = "basic"  # Basic encryption
    STRONG = "strong"  # Strong encryption with key rotation
    VAULT = "vault"  # Use external vault (OpenBao)


class SensitiveFieldType(str, Enum):
    """Types of sensitive configuration fields."""

    PASSWORD = "password"
    SECRET_KEY = "secret_key"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"
    WEBHOOK_URL = "webhook_url"


class EncryptedField(BaseModel):
    """Encrypted configuration field."""

    value: str
    encryption_level: FieldEncryptionLevel
    field_type: SensitiveFieldType
    encrypted_at: datetime
    key_version: int
    checksum: str


class ConfigurationEncryption:
    """
    Configuration encryption manager for sensitive data protection.
    Supports field-level encryption with multiple keys and rotation.
    """

    # Patterns to identify sensitive fields
    SENSITIVE_PATTERNS = {
        SensitiveFieldType.PASSWORD: [r".*password.*", r".*passwd.*", r".*pwd.*"],
        SensitiveFieldType.SECRET_KEY: [r".*secret.*", r".*key.*"],
        SensitiveFieldType.API_KEY: [r".*api_key.*", r".*apikey.*"],
        SensitiveFieldType.TOKEN: [r".*token.*", r".*auth.*"],
        SensitiveFieldType.CONNECTION_STRING: [
            r".*_url.*",
            r".*_uri.*",
            r".*connection.*",
        ],
        SensitiveFieldType.CERTIFICATE: [r".*cert.*", r".*certificate.*"],
        SensitiveFieldType.PRIVATE_KEY: [r".*private_key.*", r".*privkey.*"],
    }

    def __init__(
        self,
        master_key: Optional[str] = None,
        key_rotation_enabled: bool = True,
        auto_detect_sensitive: bool = True,
    ):
        """
        Initialize configuration encryption.

        Args:
            master_key: Master encryption key (if None, uses environment)
            key_rotation_enabled: Enable automatic key rotation
            auto_detect_sensitive: Automatically detect sensitive fields
        """
        self.key_rotation_enabled = key_rotation_enabled
        self.auto_detect_sensitive = auto_detect_sensitive

        # Initialize encryption keys
        self.master_key = master_key or os.getenv("CONFIG_MASTER_KEY")
        if not self.master_key:
            logger.warning("No master key provided, generating temporary key")
            self.master_key = Fernet.generate_key().decode()

        # Create encryption keys with rotation support
        self.encryption_keys = self._initialize_encryption_keys()
        self.current_key_version = len(self.encryption_keys) - 1

        # Track encrypted fields
        self.encrypted_fields: Dict[str, EncryptedField] = {}

        # Sensitive field registry
        self.sensitive_fields: Set[str] = set()
        self._load_sensitive_field_registry()

    def _initialize_encryption_keys(self) -> List[Fernet]:
        """Initialize encryption keys with rotation support."""
        keys = []

        # Primary key from master key
        primary_key = self._derive_key(self.master_key, salt=b"dotmac_primary")
        keys.append(Fernet(primary_key))

        # Additional keys for rotation (if enabled)
        if self.key_rotation_enabled:
            # Previous generation keys (for decryption of old data)
            for i in range(1, 4):  # Keep 3 previous generations
                rotation_key = self._derive_key(
                    self.master_key, salt=f"dotmac_rotation_{i}".encode()
                )
                keys.append(Fernet(rotation_key)

        return keys

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()

    def _load_sensitive_field_registry(self):
        """Load registry of known sensitive fields."""
        # Default sensitive fields
        default_sensitive = {
            "jwt_secret_key",
            "database_url",
            "async_database_url",
            "redis_url",
            "smtp_password",
            "twilio_auth_token",
            "stripe_secret_key",
            "stripe_webhook_secret",
            "minio_secret_key",
            "openbao_token",
            "signoz_access_token",
        }
        self.sensitive_fields.update(default_sensitive)

        # Load from configuration file if exists
        registry_file = "/etc/dotmac/sensitive_fields.json"
        if os.path.exists(registry_file):
            try:
                with open(registry_file, "r") as f:
                    additional_fields = json.load(f)
                    self.sensitive_fields.update(additional_fields)
                logger.info(
                    f"Loaded {len(additional_fields)} additional sensitive fields"
                )
            except Exception as e:
                logger.warning(f"Failed to load sensitive field registry: {e}")

    def detect_sensitive_field(
        self, field_name: str, field_value: Any
    ) -> Optional[SensitiveFieldType]:
        """
        Automatically detect if a field contains sensitive data.

        Args:
            field_name: Name of the configuration field
            field_value: Value of the field

        Returns:
            SensitiveFieldType if sensitive, None otherwise
        """
        if not self.auto_detect_sensitive:
            return None

        field_name_lower = field_name.lower()

        # Check against known sensitive fields
        if field_name in self.sensitive_fields:
            # Determine type based on patterns
            for field_type, patterns in self.SENSITIVE_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, field_name_lower):
                        return field_type
            return SensitiveFieldType.SECRET_KEY  # Default

        # Check patterns
        for field_type, patterns in self.SENSITIVE_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, field_name_lower):
                    return field_type

        # Check value characteristics
        if isinstance(field_value, str):
            # Check for URL patterns with credentials
            if "://" in field_value and (
                "@" in field_value or "password" in field_value.lower()
            ):
                return SensitiveFieldType.CONNECTION_STRING

            # Check for long random strings (likely secrets)
            if (
                len(field_value) >= 32
                and any(c.isalnum() for c in field_value)
                and not field_value.isalpha()
            ):
                return SensitiveFieldType.SECRET_KEY

        return None

    def encrypt_field(
        self,
        field_name: str,
        field_value: str,
        field_type: Optional[SensitiveFieldType] = None,
        encryption_level: FieldEncryptionLevel = FieldEncryptionLevel.STRONG,
    ) -> EncryptedField:
        """
        Encrypt a configuration field.

        Args:
            field_name: Name of the field
            field_value: Value to encrypt
            field_type: Type of sensitive field
            encryption_level: Level of encryption to apply

        Returns:
            EncryptedField object
        """
        if encryption_level == FieldEncryptionLevel.NONE:
            raise ValueError("Cannot encrypt field with NONE encryption level")

        # Auto-detect field type if not provided
        if field_type is None:
            field_type = self.detect_sensitive_field(field_name, field_value)
            if field_type is None:
                field_type = SensitiveFieldType.SECRET_KEY

        # Select encryption method based on level
        if encryption_level == FieldEncryptionLevel.VAULT:
            # Use external vault (implemented separately)
            encrypted_value = self._encrypt_with_vault(field_value)
        elif encryption_level == FieldEncryptionLevel.STRONG:
            # Use MultiFernet for key rotation support
            multi_fernet = MultiFernet(self.encryption_keys)
            encrypted_value = multi_fernet.encrypt(field_value.encode().decode()
        else:  # BASIC
            # Use single key
            encrypted_value = (
                self.encryption_keys[0].encrypt(field_value.encode().decode()
            )

        # Calculate checksum
        checksum = self._calculate_checksum(field_value)

        # Create encrypted field
        encrypted_field = EncryptedField(
            value=encrypted_value,
            encryption_level=encryption_level,
            field_type=field_type,
            encrypted_at=datetime.now(timezone.utc),
            key_version=self.current_key_version,
            checksum=checksum,
        )

        # Store in registry
        self.encrypted_fields[field_name] = encrypted_field

        logger.debug(
            f"Encrypted field: {field_name} (type: {field_type}, level: {encryption_level})"
        )
        return encrypted_field

    def decrypt_field(self, field_name: str, encrypted_field: EncryptedField) -> str:
        """
        Decrypt a configuration field.

        Args:
            field_name: Name of the field
            encrypted_field: EncryptedField object

        Returns:
            Decrypted value
        """
        try:
            if encrypted_field.encryption_level == FieldEncryptionLevel.VAULT:
                return self._decrypt_with_vault(encrypted_field.value)
            elif encrypted_field.encryption_level == FieldEncryptionLevel.STRONG:
                # Use MultiFernet for backward compatibility
                multi_fernet = MultiFernet(self.encryption_keys)
                decrypted_value = multi_fernet.decrypt(
                    encrypted_field.value.encode()
                ).decode()
            else:  # BASIC
                # Try current key first, then fallback to older keys
                for key in self.encryption_keys:
                    try:
                        decrypted_value = key.decrypt(
                            encrypted_field.value.encode()
                        ).decode()
                        break
                    except:
                        continue
                else:
                    raise ValueError("Unable to decrypt with any available key")

            # Verify checksum
            if self._calculate_checksum(decrypted_value) != encrypted_field.checksum:
                logger.warning(f"Checksum mismatch for field {field_name}")

            return decrypted_value

        except Exception as e:
            logger.error(f"Failed to decrypt field {field_name}: {e}")
            raise

    def encrypt_configuration(
        self,
        config_dict: Dict[str, Any],
        encryption_rules: Optional[Dict[str, FieldEncryptionLevel]] = None,
    ) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a configuration dictionary.

        Args:
            config_dict: Configuration dictionary
            encryption_rules: Custom encryption rules per field

        Returns:
            Configuration with encrypted sensitive fields
        """
        encrypted_config = {}
        encryption_rules = encryption_rules or {}

        for key, value in config_dict.items():
            if isinstance(value, dict):
                # Recursively encrypt nested dictionaries
                encrypted_config[key] = self.encrypt_configuration(
                    value, encryption_rules
                )
            elif isinstance(value, str):
                # Check if field should be encrypted
                encryption_level = encryption_rules.get(key)
                if encryption_level is None:
                    # Auto-detect sensitive fields
                    field_type = self.detect_sensitive_field(key, value)
                    if field_type:
                        encryption_level = FieldEncryptionLevel.STRONG

                if encryption_level and encryption_level != FieldEncryptionLevel.NONE:
                    # Encrypt the field
                    encrypted_field = self.encrypt_field(
                        key, value, encryption_level=encryption_level
                    )
                    encrypted_config[key] = {
                        "_encrypted": True,
                        "data": encrypted_field.model_dump(),
                    }
                else:
                    # Keep as-is
                    encrypted_config[key] = value
            else:
                # Non-string values are not encrypted
                encrypted_config[key] = value

        return encrypted_config

    def decrypt_configuration(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt encrypted fields in a configuration dictionary.

        Args:
            config_dict: Configuration dictionary with encrypted fields

        Returns:
            Configuration with decrypted values
        """
        decrypted_config = {}

        for key, value in config_dict.items():
            if isinstance(value, dict):
                if value.get("_encrypted"):
                    # Decrypt encrypted field
                    encrypted_field = EncryptedField(**value["data"])
                    decrypted_config[key] = self.decrypt_field(key, encrypted_field)
                else:
                    # Recursively decrypt nested dictionaries
                    decrypted_config[key] = self.decrypt_configuration(value)
            else:
                # Non-encrypted value
                decrypted_config[key] = value

        return decrypted_config

    def rotate_encryption_keys(self) -> int:
        """
        Rotate encryption keys and re-encrypt all fields.

        Returns:
            Number of fields re-encrypted
        """
        if not self.key_rotation_enabled:
            raise ValueError("Key rotation is disabled")

        logger.info("Starting encryption key rotation")

        # Generate new primary key
        new_primary_key = self._derive_key(
            self.master_key,
            salt=f"dotmac_rotation_{datetime.now(timezone.utc).timestamp()}".encode(),
        )

        # Update key list (new key becomes primary, old keys kept for decryption)
        self.encryption_keys.insert(0, Fernet(new_primary_key)
        self.current_key_version += 1

        # Re-encrypt all fields with new key
        re_encrypted_count = 0
        for field_name, encrypted_field in self.encrypted_fields.items():
            try:
                # Decrypt with old key
                decrypted_value = self.decrypt_field(field_name, encrypted_field)

                # Re-encrypt with new key
                new_encrypted_field = self.encrypt_field(
                    field_name,
                    decrypted_value,
                    encrypted_field.field_type,
                    encrypted_field.encryption_level,
                )

                self.encrypted_fields[field_name] = new_encrypted_field
                re_encrypted_count += 1

            except Exception as e:
                logger.error(f"Failed to re-encrypt field {field_name}: {e}")

        # Cleanup old keys (keep only last 5 versions)
        if len(self.encryption_keys) > 5:
            self.encryption_keys = self.encryption_keys[:5]

        logger.info(f"Key rotation completed, re-encrypted {re_encrypted_count} fields")
        return re_encrypted_count

    def export_encrypted_config(self, config_dict: Dict[str, Any], output_file: str):
        """
        Export encrypted configuration to file.

        Args:
            config_dict: Configuration dictionary
            output_file: Output file path
        """
        encrypted_config = self.encrypt_configuration(config_dict)

        # Add metadata
        export_data = {
            "version": "1.0",
            "encrypted_at": datetime.now(timezone.utc).isoformat(),
            "key_version": self.current_key_version,
            "config": encrypted_config,
        }

        # Ensure secure file permissions
        os.umask(0o077)  # Only owner can read/write

        with open(output_file, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Encrypted configuration exported to {output_file}")

    def import_encrypted_config(self, input_file: str) -> Dict[str, Any]:
        """
        Import and decrypt configuration from file.

        Args:
            input_file: Input file path

        Returns:
            Decrypted configuration dictionary
        """
        with open(input_file, "r") as f:
            import_data = json.load(f)

        encrypted_config = import_data["config"]
        decrypted_config = self.decrypt_configuration(encrypted_config)

        logger.info(f"Configuration imported and decrypted from {input_file}")
        return decrypted_config

    def _encrypt_with_vault(self, value: str) -> str:
        """Encrypt value using external vault (placeholder)."""
        # This would integrate with the SecretsManager
        # For now, fallback to strong encryption
        return self.encryption_keys[0].encrypt(value.encode().decode()

    def _decrypt_with_vault(self, encrypted_value: str) -> str:
        """Decrypt value using external vault (placeholder)."""
        # This would integrate with the SecretsManager
        # For now, fallback to strong decryption
        return self.encryption_keys[0].decrypt(encrypted_value.encode().decode()

    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for value integrity."""
        import hashlib

        return hashlib.sha256(value.encode().hexdigest()

    def get_encryption_status(self) -> Dict[str, Any]:
        """
        Get encryption system status.

        Returns:
            Status information
        """
        return {
            "master_key_set": bool(self.master_key),
            "key_rotation_enabled": self.key_rotation_enabled,
            "current_key_version": self.current_key_version,
            "total_keys": len(self.encryption_keys),
            "encrypted_fields_count": len(self.encrypted_fields),
            "sensitive_fields_count": len(self.sensitive_fields),
            "auto_detect_enabled": self.auto_detect_sensitive,
        }


# Global encryption manager
_config_encryption: Optional[ConfigurationEncryption] = None


def get_config_encryption() -> ConfigurationEncryption:
    """Get global configuration encryption manager."""
    global _config_encryption
    if _config_encryption is None:
        _config_encryption = ConfigurationEncryption()
    return _config_encryption


def init_config_encryption(
    master_key: Optional[str] = None,
    key_rotation_enabled: bool = True,
    auto_detect_sensitive: bool = True,
) -> ConfigurationEncryption:
    """Initialize global configuration encryption manager."""
    global _config_encryption
    _config_encryption = ConfigurationEncryption(
        master_key=master_key,
        key_rotation_enabled=key_rotation_enabled,
        auto_detect_sensitive=auto_detect_sensitive,
    )
    return _config_encryption
