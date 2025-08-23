"""Encryption service for data protection."""

import base64
import hashlib
from typing import Union, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self, key: Optional[bytes] = None, password: Optional[str] = None):
        """Initialize encryption service with key or password."""
        if key:
            self._fernet = Fernet(key)
        elif password:
            self._fernet = self._create_fernet_from_password(password)
        else:
            # Generate a random key
            self._fernet = Fernet(Fernet.generate_key())
    
    def _create_fernet_from_password(self, password: str, salt: Optional[bytes] = None) -> Fernet:
        """Create Fernet cipher from password."""
        if salt is None:
            salt = b"default_salt_change_in_production"  # Should be random in production
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded string."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted_data = self._fernet.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded data."""
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self._fernet.decrypt(encrypted_bytes)
        return decrypted_data.decode('utf-8')
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt bytes directly."""
        return self._fernet.encrypt(data)
    
    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt bytes directly."""
        return self._fernet.decrypt(encrypted_data)
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """Hash password with SHA-256."""
        if salt is None:
            salt = "default_salt_change_in_production"
        
        password_salt = (password + salt).encode('utf-8')
        hashed = hashlib.sha256(password_salt).hexdigest()
        return hashed
    
    def verify_password(self, password: str, hashed: str, salt: Optional[str] = None) -> bool:
        """Verify password against hash."""
        return self.hash_password(password, salt) == hashed
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    def get_key(self) -> bytes:
        """Get the current encryption key."""
        return self._fernet._encryption_key