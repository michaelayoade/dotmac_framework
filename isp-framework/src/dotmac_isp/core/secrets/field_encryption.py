"""
Field-Level Encryption Module

Extracted from encryption.py for better organization.
Provides field-level encryption decorators and utilities for Pydantic models.
"""

import base64
import json
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar

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

try:
    from cryptography.fernet import Fernet

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


# Import DataClassification from the main module
class DataClassification:
    """Data classification levels for encryption policies"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

T = TypeVar("T", bound=BaseModel)


class EncryptedField(BaseModel):
    """Represents an encrypted field with metadata"""

    encrypted_data: str = Field(..., description="Base64 encoded encrypted data")
    key_id: str = Field(..., description="Encryption key identifier")
    algorithm: str = Field(..., description="Encryption algorithm used")
    iv: str | None = Field(None, description="Initialization vector if used")
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


def encrypted_field(
    classification: DataClassification = DataClassification.CONFIDENTIAL, **kwargs
) -> Any:
    """
    Create an encrypted field descriptor for Pydantic models.

    Args:
        classification: Data classification level
        **kwargs: Additional Field arguments

    Returns:
        Pydantic Field configured for encryption
    """
    if not PYDANTIC_AVAILABLE:
        raise ImportError("Pydantic not available for encrypted fields")

    # Store encryption metadata in field info
    kwargs.setdefault(
        "description", f"Encrypted field (classification: {classification.value})"
    )
    kwargs["json_schema_extra"] = {
        "encrypted": True,
        "classification": classification.value,
    }

    return Field(**kwargs)


class FieldEncryption:
    """Field-level encryption utilities"""

    def __init__(self, encryption_service):
        """  Init   operation."""
        self.encryption_service = encryption_service

    def encrypt_model_fields(
        self, model: BaseModel, field_classifications: dict[str, DataClassification]
    ) -> BaseModel:
        """
        Encrypt specified fields in a Pydantic model.

        Args:
            model: Pydantic model instance
            field_classifications: Mapping of field names to classification levels

        Returns:
            Model with encrypted fields
        """
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic not available")

        model_dict = model.dict() if hasattr(model, "dict") else model.model_dump()

        for field_name, classification in field_classifications.items():
            if field_name in model_dict and model_dict[field_name] is not None:
                # Convert value to string for encryption
                field_value = model_dict[field_name]
                if not isinstance(field_value, str):
                    field_value = json.dumps(field_value)

                # Encrypt the field
                encrypted_field = self.encryption_service.encrypt(
                    field_value, classification
                )
                model_dict[field_name] = (
                    encrypted_field.dict()
                    if hasattr(encrypted_field, "dict")
                    else encrypted_field.model_dump()
                )

        # Create new model instance with encrypted fields
        return type(model)(**model_dict)

    def decrypt_model_fields(
        self,
        model: BaseModel,
        field_names: list[str],
        target_types: dict[str, type] | None = None,
    ) -> BaseModel:
        """
        Decrypt specified fields in a Pydantic model.

        Args:
            model: Pydantic model instance with encrypted fields
            field_names: List of field names to decrypt
            target_types: Optional mapping of field names to target types

        Returns:
            Model with decrypted fields
        """
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic not available")

        model_dict = model.dict() if hasattr(model, "dict") else model.model_dump()
        target_types = target_types or {}

        for field_name in field_names:
            if field_name in model_dict and model_dict[field_name] is not None:
                encrypted_data = model_dict[field_name]

                # Handle both EncryptedField objects and raw encrypted data
                if isinstance(encrypted_data, dict):
                    encrypted_field = EncryptedField(**encrypted_data)
                else:
                    encrypted_field = encrypted_data

                # Decrypt the field
                decrypted_value = self.encryption_service.decrypt(encrypted_field)

                # Convert back to target type if specified
                if field_name in target_types:
                    target_type = target_types[field_name]
                    if target_type != str:
                        try:
                            decrypted_value = json.loads(decrypted_value)
                        except (json.JSONDecodeError, TypeError):
                            pass  # Keep as string if JSON decode fails

                model_dict[field_name] = decrypted_value

        # Create new model instance with decrypted fields
        return type(model)(**model_dict)

    def get_encrypted_fields(self, model: BaseModel) -> list[str]:
        """
        Get list of field names that are encrypted in a model.

        Args:
            model: Pydantic model instance

        Returns:
            List of encrypted field names
        """
        if not PYDANTIC_AVAILABLE:
            return []

        encrypted_fields = []
        model_dict = model.dict() if hasattr(model, "dict") else model.model_dump()

        for field_name, field_value in model_dict.items():
            if isinstance(field_value, dict):
                # Check if it looks like an EncryptedField
                if all(
                    key in field_value
                    for key in ["encrypted_data", "key_id", "algorithm"]
                ):
                    encrypted_fields.append(field_name)
            elif hasattr(field_value, "encrypted_data"):
                encrypted_fields.append(field_name)

        return encrypted_fields


class SecureDataModel(BaseModel):
    """Base model with encryption capabilities"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def with_encryption(
        cls,
        encryption_service,
        classification: DataClassification = DataClassification.CONFIDENTIAL,
    ):
        """
        Create a model class with automatic field encryption.

        Args:
            encryption_service: Encryption service instance
            classification: Default classification for encrypted fields

        Returns:
            Model class with encryption support
        """

        class EncryptedModel(cls):
            """Class for EncryptedModel operations."""
            _encryption_service = encryption_service
            _classification = classification

            def encrypt_sensitive_fields(
                self, field_names: list[str]
            ) -> "EncryptedModel":
                """Encrypt specified fields in this model instance"""
                field_classifications = dict.fromkeys(field_names, self._classification)
                field_encryptor = FieldEncryption(self._encryption_service)
                return field_encryptor.encrypt_model_fields(self, field_classifications)

            def decrypt_fields(self, field_names: list[str]) -> "EncryptedModel":
                """Decrypt specified fields in this model instance"""
                field_encryptor = FieldEncryption(self._encryption_service)
                return field_encryptor.decrypt_model_fields(self, field_names)

            def get_encrypted_fields(self) -> list[str]:
                """Get list of encrypted fields in this model"""
                field_encryptor = FieldEncryption(self._encryption_service)
                return field_encryptor.get_encrypted_fields(self)

        return EncryptedModel


def encrypt_sensitive_data(  # noqa: C901
    classification: DataClassification = DataClassification.CONFIDENTIAL,
    fields: list[str] | None = None,
):
    """
    Decorator for automatically encrypting sensitive fields in Pydantic models.

    Args:
        classification: Data classification level for encryption
        fields: List of field names to encrypt (if None, encrypts all fields marked as encrypted)

    Returns:
        Decorator function
    """

    def decorator(cls):  # noqa: C901
        """Decorator operation."""
        if not issubclass(cls, BaseModel):
            raise TypeError(
                "encrypt_sensitive_data can only be used on Pydantic models"
            )

        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, **kwargs):
            """New Init operation."""
            # Initialize normally first
            original_init(self, **kwargs)

            # Get encryption service from kwargs or class attribute
            encryption_service = kwargs.pop("_encryption_service", None)
            if not encryption_service and hasattr(cls, "_encryption_service"):
                encryption_service = cls._encryption_service

            if encryption_service:
                # Determine fields to encrypt
                target_fields = fields
                if not target_fields:
                    # Auto-detect fields marked for encryption
                    target_fields = []
                    for field_name, field_info in cls.model_fields.items():
                        if hasattr(field_info, "json_schema_extra"):
                            extra = field_info.json_schema_extra or {}
                            if extra.get("encrypted", False):
                                target_fields.append(field_name)

                if target_fields:
                    # Encrypt the specified fields
                    field_classifications = dict.fromkeys(target_fields, classification)
                    field_encryptor = FieldEncryption(encryption_service)
                    encrypted_model = field_encryptor.encrypt_model_fields(
                        self, field_classifications
                    )

                    # Update self with encrypted data
                    for field_name in target_fields:
                        if hasattr(encrypted_model, field_name):
                            setattr(
                                self, field_name, getattr(encrypted_model, field_name)
                            )

        cls.__init__ = new_init
        return cls

    return decorator


def selective_encryption(field_mapping: dict[str, DataClassification]):
    """
    Decorator for encrypting specific fields with different classification levels.

    Args:
        field_mapping: Dictionary mapping field names to classification levels

    Returns:
        Decorator function
    """

    def decorator(cls):
        """Decorator operation."""
        if not issubclass(cls, BaseModel):
            raise TypeError("selective_encryption can only be used on Pydantic models")

        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, **kwargs):
            """New Init operation."""
            # Initialize normally first
            original_init(self, **kwargs)

            # Get encryption service
            encryption_service = kwargs.pop("_encryption_service", None)
            if not encryption_service and hasattr(cls, "_encryption_service"):
                encryption_service = cls._encryption_service

            if encryption_service:
                # Encrypt mapped fields
                field_encryptor = FieldEncryption(encryption_service)
                encrypted_model = field_encryptor.encrypt_model_fields(
                    self, field_mapping
                )

                # Update self with encrypted data
                for field_name in field_mapping:
                    if hasattr(encrypted_model, field_name):
                        setattr(self, field_name, getattr(encrypted_model, field_name))

        cls.__init__ = new_init
        return cls

    return decorator


__all__ = [
    "EncryptedField",
    "encrypted_field",
    "FieldEncryption",
    "SecureDataModel",
    "encrypt_sensitive_data",
    "selective_encryption",
]
