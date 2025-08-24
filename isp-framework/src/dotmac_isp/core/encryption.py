"""Encryption service for data protection.

This module provides enterprise-grade encryption services for protecting sensitive data
in the DotMac platform. It implements symmetric encryption using Fernet (AES-128 in CBC
mode with HMAC authentication) and password-based key derivation.

Features:
    - Symmetric encryption using Fernet (AES-128)
    - Password-based key derivation (PBKDF2)
    - Automatic base64 encoding/decoding
    - Password hashing and verification
    - Support for both string and binary data

Security Considerations:
    - Always use unique salts in production
    - Store encryption keys in secure vault (OpenBao/Vault)
    - Rotate encryption keys regularly
    - Never log or expose encryption keys
    - Use strong passwords for key derivation

Example:
    >>> # Initialize with generated key
    >>> service = EncryptionService()
    >>> 
    >>> # Encrypt sensitive data
    >>> encrypted = service.encrypt("sensitive_data")
    >>> 
    >>> # Decrypt data
    >>> decrypted = service.decrypt(encrypted)
    >>> assert decrypted == "sensitive_data"
    
    >>> # Initialize with password
    >>> service = EncryptionService(password="strong_password_123")
    >>> encrypted = service.encrypt("user_ssn")
"""

import base64
import hashlib
from typing import Union, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.
    
    This service provides symmetric encryption capabilities using the Fernet
    encryption scheme, which guarantees that a message encrypted using it cannot
    be manipulated or read without the key.
    
    Attributes:
        _fernet: The Fernet cipher instance used for encryption/decryption.
    
    Note:
        In production, encryption keys should be:
        - Generated using cryptographically secure random sources
        - Stored in secure key management systems (OpenBao/Vault)
        - Rotated regularly according to security policies
        - Never hardcoded or committed to version control
    """
    
    def __init__(self, key: Optional[bytes] = None, password: Optional[str] = None):
        """Initialize encryption service with key or password.
        
        The service can be initialized in three ways:
        1. With an existing Fernet key (for key rotation scenarios)
        2. With a password (derives key using PBKDF2)
        3. With no parameters (generates a new random key)
        
        Args:
            key: Optional Fernet key (32 bytes, base64-encoded).
                If provided, this key will be used for encryption.
            password: Optional password string for key derivation.
                If provided, a key will be derived using PBKDF2.
        
        Raises:
            ValueError: If the provided key is invalid.
            
        Example:
            >>> # With generated key
            >>> service = EncryptionService()
            >>> 
            >>> # With existing key
            >>> key = Fernet.generate_key()
            >>> service = EncryptionService(key=key)
            >>> 
            >>> # With password
            >>> service = EncryptionService(password="secure_password")
        """
        if key:
            self._fernet = Fernet(key)
        elif password:
            self._fernet = self._create_fernet_from_password(password)
        else:
            # Generate a random key
            self._fernet = Fernet(Fernet.generate_key())
    
    def _create_fernet_from_password(self, password: str, salt: Optional[bytes] = None) -> Fernet:
        """Create Fernet cipher from password using PBKDF2.
        
        This method derives an encryption key from a password using PBKDF2
        (Password-Based Key Derivation Function 2) with SHA-256 as the hash
        function. This provides resistance against brute-force attacks.
        
        Args:
            password: The password to derive the key from.
            salt: Optional salt for key derivation. If not provided,
                uses a default salt (should be random in production).
        
        Returns:
            Fernet: A Fernet cipher instance initialized with the derived key.
        
        Security Note:
            In production environments:
            - Always use a unique, random salt for each key derivation
            - Store the salt alongside the encrypted data
            - Use at least 100,000 iterations (more for higher security)
            - Consider using Argon2 for password hashing instead
        """
        if salt is None:
            salt = b"default_salt_change_in_production"  # TODO: Use os.urandom(16) in production
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded string.
        
        This method encrypts the provided data using Fernet symmetric encryption
        and returns the result as a base64-encoded string for safe storage or
        transmission.
        
        Args:
            data: The data to encrypt. Can be either a string or bytes.
                Strings will be UTF-8 encoded before encryption.
        
        Returns:
            str: Base64-encoded encrypted data that can be safely stored
                in databases or transmitted over networks.
        
        Raises:
            TypeError: If data is not a string or bytes.
            
        Example:
            >>> service = EncryptionService()
            >>> encrypted = service.encrypt("credit_card_number")
            >>> print(encrypted)  # Base64 string like "Z0FBQUFBQmg..."
        
        Performance Note:
            For large data (>1MB), consider chunking or using streaming encryption.
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        encrypted_data = self._fernet.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded data.
        
        This method decrypts data that was previously encrypted using the
        encrypt() method. It handles base64 decoding and returns the original
        plaintext string.
        
        Args:
            encrypted_data: Base64-encoded encrypted data string.
        
        Returns:
            str: The decrypted plaintext string.
        
        Raises:
            InvalidToken: If the encrypted data is invalid, corrupted,
                or was encrypted with a different key.
            ValueError: If the base64 encoding is invalid.
            
        Example:
            >>> service = EncryptionService()
            >>> encrypted = service.encrypt("secret_data")
            >>> decrypted = service.decrypt(encrypted)
            >>> assert decrypted == "secret_data"
        
        Security Note:
            Failed decryption attempts should be logged and monitored
            as they may indicate attempted data tampering or key mismatch.
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self._fernet.decrypt(encrypted_bytes)
        return decrypted_data.decode('utf-8')
    
    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypt bytes directly without base64 encoding.
        
        This method is useful when working with binary data that doesn't
        need to be stored as text.
        
        Args:
            data: Raw bytes to encrypt.
        
        Returns:
            bytes: Encrypted bytes (includes Fernet formatting).
        
        Example:
            >>> service = EncryptionService()
            >>> file_data = b"\x00\x01\x02\x03"
            >>> encrypted = service.encrypt_bytes(file_data)
        """
        return self._fernet.encrypt(data)
    
    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypt bytes directly without base64 decoding.
        
        Args:
            encrypted_data: Encrypted bytes from encrypt_bytes().
        
        Returns:
            bytes: Original decrypted bytes.
        
        Raises:
            InvalidToken: If decryption fails.
        """
        return self._fernet.decrypt(encrypted_data)
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """Hash password with SHA-256.
        
        Warning:
            This method uses simple SHA-256 hashing and is NOT suitable for
            password storage in production. Use bcrypt, scrypt, or Argon2
            for password hashing in production systems.
        
        Args:
            password: The password to hash.
            salt: Optional salt string. Should be unique per password
                in production.
        
        Returns:
            str: Hexadecimal string representation of the hash.
        
        Deprecated:
            Use bcrypt or Argon2 for production password hashing:
            >>> from passlib.hash import bcrypt
            >>> hashed = bcrypt.hash(password)
        """
        if salt is None:
            salt = "default_salt_change_in_production"  # TODO: Use secrets.token_hex(16)
        
        password_salt = (password + salt).encode('utf-8')
        hashed = hashlib.sha256(password_salt).hexdigest()
        return hashed
    
    def verify_password(self, password: str, hashed: str, salt: Optional[str] = None) -> bool:
        """Verify password against hash.
        
        Args:
            password: The password to verify.
            hashed: The expected hash value.
            salt: The salt used during hashing.
        
        Returns:
            bool: True if password matches, False otherwise.
        
        Security Note:
            This method is vulnerable to timing attacks. Use
            constant-time comparison in production.
        """
        return self.hash_password(password, salt) == hashed
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new encryption key.
        
        Generates a cryptographically secure random Fernet key suitable
        for use with this encryption service.
        
        Returns:
            bytes: A new 32-byte Fernet key (base64-encoded).
        
        Example:
            >>> key = EncryptionService.generate_key()
            >>> service = EncryptionService(key=key)
        
        Security Note:
            Generated keys should be immediately stored in a secure
            key management system and never logged or displayed.
        """
        return Fernet.generate_key()
    
    def get_key(self) -> bytes:
        """Get the current encryption key.
        
        Warning:
            This method exposes the encryption key and should only be
            used for key rotation or backup purposes. Never log or
            display the key in production.
        
        Returns:
            bytes: The current Fernet encryption key.
        
        Security Note:
            Access to this method should be strictly controlled and
            audited in production environments.
        """
        return self._fernet._encryption_key