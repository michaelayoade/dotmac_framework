"""
Encryption at Rest Implementation

Comprehensive encryption service for protecting sensitive data at rest.
Supports field-level encryption, key rotation, and data classification.
"""

import asyncio
import base64
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ..utils.datetime_compat import utcnow
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from enum import Enum
from typing import Any, TypeVar

import structlog
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class DataClassification(Enum):
    """Data classification levels for encryption policies"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""

    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"


@dataclass
class EncryptionKey:
    """Encryption key metadata and material"""

    key_id: str
    algorithm: EncryptionAlgorithm
    key_material: bytes
    created_at: datetime = field(default_factory=utcnow)
    expires_at: datetime | None = None
    version: int = 1
    is_active: bool = True

    def is_expired(self) -> bool:
        """Check if key has expired"""
        if not self.expires_at:
            return False
        return utcnow() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (excluding sensitive key material)"""
        return {
            "key_id": self.key_id,
            "algorithm": self.algorithm.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "version": self.version,
            "is_active": self.is_active,
        }


@dataclass
class EncryptionPolicy:
    """Encryption policy for data classification"""

    classification: DataClassification
    algorithm: EncryptionAlgorithm
    key_rotation_days: int
    require_key_escrow: bool = False
    allow_key_caching: bool = True
    max_cache_time_minutes: int = 60

    @classmethod
    def for_classification(
        cls, classification: DataClassification
    ) -> "EncryptionPolicy":
        """Get default encryption policy for classification level"""
        policies = {
            DataClassification.PUBLIC: cls(
                classification=classification,
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_rotation_days=365,
                require_key_escrow=False,
                allow_key_caching=True,
                max_cache_time_minutes=120,
            ),
            DataClassification.INTERNAL: cls(
                classification=classification,
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_rotation_days=180,
                require_key_escrow=False,
                allow_key_caching=True,
                max_cache_time_minutes=60,
            ),
            DataClassification.CONFIDENTIAL: cls(
                classification=classification,
                algorithm=EncryptionAlgorithm.FERNET,
                key_rotation_days=90,
                require_key_escrow=True,
                allow_key_caching=True,
                max_cache_time_minutes=30,
            ),
            DataClassification.RESTRICTED: cls(
                classification=classification,
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                key_rotation_days=30,
                require_key_escrow=True,
                allow_key_caching=False,
                max_cache_time_minutes=0,
            ),
            DataClassification.TOP_SECRET: cls(
                classification=classification,
                algorithm=EncryptionAlgorithm.RSA_4096,
                key_rotation_days=7,
                require_key_escrow=True,
                allow_key_caching=False,
                max_cache_time_minutes=0,
            ),
        }
        return policies[classification]


class EncryptionConfig(BaseModel):
    """Configuration for encryption service."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    master_key: str | None = Field(
        default=None, description="Master encryption key (base64 encoded)"
    )

    default_algorithm: EncryptionAlgorithm = Field(
        default=EncryptionAlgorithm.AES_256_GCM,
        description="Default encryption algorithm",
    )

    key_rotation_days: int = Field(
        default=90, description="Default key rotation period in days", ge=1, le=365
    )

    enable_key_caching: bool = Field(
        default=True, description="Enable encryption key caching"
    )

    cache_ttl_minutes: int = Field(
        default=60, description="Key cache TTL in minutes", ge=1, le=1440
    )

    require_key_escrow: bool = Field(
        default=False, description="Require key escrow for compliance"
    )


class EncryptedField(BaseModel):
    """Encrypted field container"""

    encrypted_data: str = Field(..., description="Base64 encoded encrypted data")
    key_id: str = Field(..., description="Encryption key identifier")
    algorithm: str = Field(..., description="Encryption algorithm used")
    iv: str | None = Field(None, description="Initialization vector if used")
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("encrypted_data")
    def validate_encrypted_data(cls, v):
        """Validate encrypted data is base64 encoded"""
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError("encrypted_data must be valid base64")


class KeyManager:
    """Encryption key management service"""

    def __init__(self, master_key: bytes | None = None):
        self.keys: dict[str, EncryptionKey] = {}
        self.key_cache: dict[str, tuple[Any, datetime]] = {}
        self.master_key = master_key or self._generate_master_key()
        self.key_escrow: dict[str, bytes] = {}

    def _generate_master_key(self) -> bytes:
        """Generate master key for key encryption"""
        return Fernet.generate_key()

    def generate_key(
        self,
        algorithm: EncryptionAlgorithm,
        classification: DataClassification,
        expires_in_days: int | None = None,
    ) -> EncryptionKey:
        """Generate new encryption key"""
        key_id = self._generate_key_id()

        if algorithm == EncryptionAlgorithm.FERNET:
            key_material = Fernet.generate_key()
        elif algorithm in [EncryptionAlgorithm.AES_256_GCM]:
            key_material = secrets.token_bytes(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.RSA_2048:
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            key_material = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        elif algorithm == EncryptionAlgorithm.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=4096, backend=default_backend()
            )
            key_material = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        # Set expiration
        expires_at = None
        if expires_in_days:
            expires_at = utcnow() + timedelta(days=expires_in_days)

        encryption_key = EncryptionKey(
            key_id=key_id,
            algorithm=algorithm,
            key_material=key_material,
            expires_at=expires_at,
        )

        # Store key
        self.keys[key_id] = encryption_key

        # Store in key escrow if required
        policy = EncryptionPolicy.for_classification(classification)
        if policy.require_key_escrow:
            self._escrow_key(encryption_key)

        logger.info(
            "Encryption key generated",
            key_id=key_id,
            algorithm=algorithm.value,
            classification=classification.value,
        )

        return encryption_key

    def get_key(self, key_id: str) -> EncryptionKey | None:
        """Get encryption key by ID"""
        key = self.keys.get(key_id)
        if key and key.is_expired():
            logger.warning("Attempted to use expired key", key_id=key_id)
            return None
        return key

    def get_active_key(self, algorithm: EncryptionAlgorithm) -> EncryptionKey | None:
        """Get active key for algorithm"""
        for key in self.keys.values():
            if key.algorithm == algorithm and key.is_active and not key.is_expired():
                return key
        return None

    def rotate_key(
        self, old_key_id: str, classification: DataClassification
    ) -> EncryptionKey:
        """Rotate encryption key"""
        old_key = self.keys.get(old_key_id)
        if not old_key:
            raise ValueError(f"Key not found: {old_key_id}")

        # Generate new key
        policy = EncryptionPolicy.for_classification(classification)
        new_key = self.generate_key(
            old_key.algorithm, classification, policy.key_rotation_days
        )

        # Deactivate old key
        old_key.is_active = False

        logger.info("Key rotated", old_key_id=old_key_id, new_key_id=new_key.key_id)

        return new_key

    def _generate_key_id(self) -> str:
        """Generate unique key identifier"""
        return f"key_{secrets.token_hex(16)}"

    def _escrow_key(self, key: EncryptionKey) -> None:
        """Store key in secure escrow"""
        # Encrypt key with master key for escrow
        f = Fernet(self.master_key)
        escrowed_key = f.encrypt(key.key_material)
        self.key_escrow[key.key_id] = escrowed_key

        logger.info("Key escrowed", key_id=key.key_id)

    def recover_key(self, key_id: str) -> EncryptionKey | None:
        """Recover key from escrow"""
        escrowed_key = self.key_escrow.get(key_id)
        if not escrowed_key:
            return None

        # Decrypt from escrow
        f = Fernet(self.master_key)
        f.decrypt(escrowed_key)

        # Reconstruct key (you'd need to store metadata separately)
        # This is simplified for demonstration
        logger.info("Key recovered from escrow", key_id=key_id)
        return None  # Implementation would reconstruct the full key


class EncryptionService:
    """Main encryption service for data at rest"""

    def __init__(self, key_manager: KeyManager | None = None):
        self.key_manager = key_manager or KeyManager()
        self.policies: dict[DataClassification, EncryptionPolicy] = {}
        self._setup_default_policies()

    def _setup_default_policies(self) -> None:
        """Setup default encryption policies"""
        for classification in DataClassification:
            self.policies[classification] = EncryptionPolicy.for_classification(
                classification
            )

    async def encrypt(
        self,
        data: str | bytes,
        classification: DataClassification,
        key_id: str | None = None,
    ) -> EncryptedField:
        """Encrypt data with appropriate policy"""
        try:
            policy = self.policies[classification]

            # Get or generate encryption key
            if key_id:
                encryption_key = self.key_manager.get_key(key_id)
                if not encryption_key:
                    raise ValueError(f"Key not found: {key_id}")
            else:
                # Always generate a new key for each encryption operation for better security
                encryption_key = self.key_manager.generate_key(
                    policy.algorithm, classification, policy.key_rotation_days
                )

            # Convert to bytes if string
            data_bytes = data.encode("utf-8") if isinstance(data, str) else data

            # Encrypt based on algorithm
            if encryption_key.algorithm == EncryptionAlgorithm.FERNET:
                encrypted_data = self._encrypt_fernet(
                    data_bytes, encryption_key.key_material
                )
                iv = None
            elif encryption_key.algorithm == EncryptionAlgorithm.AES_256_GCM:
                encrypted_data, iv = self._encrypt_aes_gcm(
                    data_bytes, encryption_key.key_material
                )
            elif encryption_key.algorithm in [
                EncryptionAlgorithm.RSA_2048,
                EncryptionAlgorithm.RSA_4096,
            ]:
                encrypted_data = self._encrypt_rsa(
                    data_bytes, encryption_key.key_material
                )
                iv = None
            else:
                raise ValueError(f"Unsupported algorithm: {encryption_key.algorithm}")

            return EncryptedField(
                encrypted_data=base64.b64encode(encrypted_data).decode("utf-8"),
                key_id=encryption_key.key_id,
                algorithm=encryption_key.algorithm.value,
                iv=base64.b64encode(iv).decode("utf-8") if iv else None,
            )

        except Exception as e:
            logger.error(
                "Encryption failed", classification=classification.value, error=str(e)
            )
            raise

    async def decrypt(self, encrypted_field: EncryptedField) -> bytes:
        """Decrypt encrypted field"""
        try:
            # Get encryption key
            encryption_key = self.key_manager.get_key(encrypted_field.key_id)
            if not encryption_key:
                raise ValueError(f"Encryption key not found: {encrypted_field.key_id}")

            # Decode encrypted data
            encrypted_data = base64.b64decode(encrypted_field.encrypted_data)

            # Decrypt based on algorithm
            algorithm = EncryptionAlgorithm(encrypted_field.algorithm)

            if algorithm == EncryptionAlgorithm.FERNET:
                return self._decrypt_fernet(encrypted_data, encryption_key.key_material)
            elif algorithm == EncryptionAlgorithm.AES_256_GCM:
                iv = (
                    base64.b64decode(encrypted_field.iv) if encrypted_field.iv else None
                )
                return self._decrypt_aes_gcm(
                    encrypted_data, encryption_key.key_material, iv
                )
            elif algorithm in [
                EncryptionAlgorithm.RSA_2048,
                EncryptionAlgorithm.RSA_4096,
            ]:
                return self._decrypt_rsa(encrypted_data, encryption_key.key_material)
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")

        except Exception as e:
            logger.error(
                "Decryption failed", key_id=encrypted_field.key_id, error=str(e)
            )
            raise

    def _encrypt_fernet(self, data: bytes, key: bytes) -> bytes:
        """Encrypt data using Fernet"""
        f = Fernet(key)
        return f.encrypt(data)

    def _decrypt_fernet(self, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data using Fernet"""
        f = Fernet(key)
        return f.decrypt(encrypted_data)

    def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> tuple[bytes, bytes]:
        """Encrypt data using AES-256-GCM"""
        # Generate random IV
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()

        # Combine ciphertext and authentication tag
        encrypted_data = ciphertext + encryptor.tag

        return encrypted_data, iv

    def _decrypt_aes_gcm(self, encrypted_data: bytes, key: bytes, iv: bytes) -> bytes:
        """Decrypt data using AES-256-GCM"""
        # Extract tag (last 16 bytes) and ciphertext
        tag = encrypted_data[-16:]
        ciphertext = encrypted_data[:-16]

        cipher = Cipher(
            algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend()
        )
        decryptor = cipher.decryptor()

        # Decrypt data
        decrypted_data = decryptor.update(ciphertext)
        decryptor.finalize()
        return decrypted_data

    def _encrypt_rsa(self, data: bytes, key_material: bytes) -> bytes:
        """Encrypt data using RSA with OAEP padding"""
        # Load the private key and extract public key for encryption
        private_key = serialization.load_pem_private_key(
            key_material, password=None, backend=default_backend()
        )
        public_key = private_key.public_key()

        # RSA can only encrypt small amounts of data, so we use OAEP padding
        encrypted_data = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return encrypted_data

    def _decrypt_rsa(self, encrypted_data: bytes, key_material: bytes) -> bytes:
        """Decrypt data using RSA with OAEP padding"""
        # Load the private key from key material
        private_key = serialization.load_pem_private_key(
            key_material, password=None, backend=default_backend()
        )

        # Decrypt using OAEP padding
        decrypted_data = private_key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return decrypted_data

    async def encrypt_string(
        self, data: str, classification: DataClassification
    ) -> str:
        """Convenience method to encrypt string and return JSON"""
        encrypted_field = await self.encrypt(data, classification)
        return encrypted_field.json()

    async def decrypt_string(self, encrypted_json: str) -> str:
        """Convenience method to decrypt from JSON string"""
        encrypted_field = EncryptedField.parse_raw(encrypted_json)
        decrypted_bytes = await self.decrypt(encrypted_field)
        return decrypted_bytes.decode("utf-8")

    def add_policy(
        self, classification: DataClassification, policy: EncryptionPolicy
    ) -> None:
        """Add custom encryption policy"""
        self.policies[classification] = policy
        logger.info("Encryption policy added", classification=classification.value)

    async def rotate_keys(self, classification: DataClassification) -> list[str]:
        """Rotate all keys for a classification level"""
        rotated_keys = []
        policy = self.policies[classification]

        for key in list(self.key_manager.keys.values()):
            if key.is_active and not key.is_expired():
                # Check if rotation is needed
                age = utcnow() - key.created_at
                if age.days >= policy.key_rotation_days:
                    new_key = self.key_manager.rotate_key(key.key_id, classification)
                    rotated_keys.append(new_key.key_id)

        logger.info(
            "Key rotation completed",
            classification=classification.value,
            rotated_count=len(rotated_keys),
        )

        return rotated_keys


class FieldEncryption:
    """Decorator for automatic field encryption in Pydantic models"""

    def __init__(
        self,
        encryption_service: EncryptionService,
        classification: DataClassification = DataClassification.CONFIDENTIAL,
    ):
        self.encryption_service = encryption_service
        self.classification = classification

    def __call__(self, cls: type[T]) -> type[T]:
        """Apply field encryption to Pydantic model"""
        original_init = cls.__init__

        def new_init(self, **kwargs):
            # Encrypt sensitive fields before initialization
            for field_name, field_info in cls.__fields__.items():
                if hasattr(
                    field_info, "field_info"
                ) and field_info.field_info.extra.get("encrypt"):
                    if field_name in kwargs and kwargs[field_name] is not None:
                        # Encrypt the field value
                        encrypted_field = asyncio.run(
                            self.encryption_service.encrypt(
                                str(kwargs[field_name]), self.classification
                            )
                        )
                        kwargs[field_name] = encrypted_field.json()

            original_init(self, **kwargs)

        cls.__init__ = new_init
        return cls


# Usage example with automatic encryption
def encrypted_field(
    classification: DataClassification = DataClassification.CONFIDENTIAL, **kwargs
):
    """Field definition for automatic encryption"""
    kwargs["encrypt"] = True
    kwargs["classification"] = classification
    return Field(**kwargs)


class SecureDataModel(BaseModel):
    """Base model with encryption capabilities"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def with_encryption(
        cls,
        encryption_service: EncryptionService,
        classification: DataClassification = DataClassification.CONFIDENTIAL,
    ):
        """Create model class with automatic field encryption"""
        return FieldEncryption(encryption_service, classification)(cls)


class KeyRotationManager:
    """Manages encryption key rotation and lifecycle."""

    def __init__(self, key_manager: KeyManager, encryption_service: EncryptionService):
        self.key_manager = key_manager
        self.encryption_service = encryption_service
        self._rotation_schedule: dict[str, datetime] = {}

    async def schedule_rotation(self, key_id: str, rotation_date: datetime):
        """Schedule key rotation for a specific date."""
        self._rotation_schedule[key_id] = rotation_date
        logger.info(
            "Key rotation scheduled", key_id=key_id, rotation_date=rotation_date
        )

    async def rotate_key(self, key_id: str) -> str:
        """Rotate a specific encryption key."""
        old_key = self.key_manager.get_key(key_id)
        if not old_key:
            raise ValueError(f"Key {key_id} not found")

        # Generate new key with same algorithm
        new_key = self.key_manager.generate_key(
            algorithm=old_key.algorithm, key_size=getattr(old_key, "key_size", None)
        )

        # Deactivate old key
        old_key.is_active = False

        # Add new key
        self.key_manager.add_key(new_key)

        logger.info(
            "Key rotated successfully", old_key_id=key_id, new_key_id=new_key.key_id
        )
        return new_key.key_id

    async def check_rotation_schedule(self):
        """Check and execute scheduled key rotations."""
        now = utcnow()
        for key_id, rotation_date in list(self._rotation_schedule.items()):
            if now >= rotation_date:
                try:
                    await self.rotate_key(key_id)
                    del self._rotation_schedule[key_id]
                except Exception as e:
                    logger.error("Key rotation failed", key_id=key_id, error=str(e))

    def get_rotation_status(self) -> dict[str, datetime]:
        """Get current rotation schedule."""
        return self._rotation_schedule.copy()


# Example usage models
class CustomerData(SecureDataModel):
    """Customer data with encrypted PII"""

    customer_id: str
    name: str = encrypted_field(classification=DataClassification.CONFIDENTIAL)
    email: str = encrypted_field(classification=DataClassification.CONFIDENTIAL)
    phone: str = encrypted_field(classification=DataClassification.RESTRICTED)
    ssn: str = encrypted_field(classification=DataClassification.TOP_SECRET)
    address: str = encrypted_field(classification=DataClassification.CONFIDENTIAL)
    created_at: datetime = Field(default_factory=utcnow)


class PaymentData(SecureDataModel):
    """Payment data with encrypted financial information"""

    payment_id: str
    customer_id: str
    card_number: str = encrypted_field(classification=DataClassification.TOP_SECRET)
    card_holder: str = encrypted_field(classification=DataClassification.RESTRICTED)
    expiry_date: str = encrypted_field(classification=DataClassification.RESTRICTED)
    cvv: str = encrypted_field(classification=DataClassification.TOP_SECRET)
    amount: float
    created_at: datetime = Field(default_factory=utcnow)
