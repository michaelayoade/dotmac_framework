"""
Plugin signature verification and security validation.

Provides cryptographic signature verification for plugins to ensure
authenticity and integrity. Supports multiple signature algorithms
and certificate-based verification.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    from cryptography.exceptions import InvalidSignature
    from cryptography import x509
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    InvalidSignature = Exception
    RSAPublicKey = None

from .interfaces import IPlugin
from .types import PluginSecurityError


class PluginSignatureVerifier:
    """
    Plugin signature verification system.
    
    Provides cryptographic verification of plugin signatures to ensure
    plugins are authentic and haven't been tampered with.
    """
    
    def __init__(
        self, 
        trusted_keys: Optional[List[Union[str, Path, RSAPublicKey]]] = None,
        require_signature: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize signature verifier.
        
        Args:
            trusted_keys: List of trusted public keys (paths, PEM strings, or key objects)
            require_signature: Whether to require valid signatures
            logger: Optional logger instance
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            if require_signature:
                raise PluginSecurityError(
                    "Cryptography library not available. "
                    "Install with: pip install 'dotmac-plugins[security]'"
                )
            else:
                logger = logger or logging.getLogger(__name__)
                logger.warning(
                    "Cryptography library not available. "
                    "Plugin signature verification disabled."
                )
        
        self._logger = logger or logging.getLogger(__name__)
        self.require_signature = require_signature
        self._trusted_keys: List[RSAPublicKey] = []
        
        if trusted_keys and CRYPTOGRAPHY_AVAILABLE:
            for key in trusted_keys:
                try:
                    public_key = self._load_public_key(key)
                    self._trusted_keys.append(public_key)
                except Exception as e:
                    self._logger.error(f"Failed to load trusted key: {e}")
    
    def _load_public_key(self, key: Union[str, Path, RSAPublicKey]) -> RSAPublicKey:
        """Load public key from various sources."""
        if isinstance(key, RSAPublicKey):
            return key
        
        if isinstance(key, (str, Path)):
            key_path = Path(key)
            
            if key_path.exists():
                # Load from file
                with open(key_path, 'rb') as f:
                    key_data = f.read()
            else:
                # Treat as PEM string
                key_data = str(key).encode('utf-8')
            
            try:
                # Try loading as public key
                public_key = serialization.load_pem_public_key(key_data)
                if isinstance(public_key, RSAPublicKey):
                    return public_key
                else:
                    raise PluginSecurityError(f"Key is not RSA public key: {type(public_key)}")
            except Exception:
                # Try loading as certificate
                try:
                    cert = x509.load_pem_x509_certificate(key_data)
                    public_key = cert.public_key()
                    if isinstance(public_key, RSAPublicKey):
                        return public_key
                    else:
                        raise PluginSecurityError(f"Certificate key is not RSA: {type(public_key)}")
                except Exception as e:
                    raise PluginSecurityError(f"Failed to load key or certificate: {e}")
        
        raise PluginSecurityError(f"Unsupported key type: {type(key)}")
    
    def verify_plugin(
        self, 
        plugin: IPlugin, 
        signature: Optional[bytes] = None,
        signature_file: Optional[Union[str, Path]] = None
    ) -> bool:
        """
        Verify plugin signature.
        
        Args:
            plugin: Plugin to verify
            signature: Plugin signature bytes
            signature_file: Path to signature file
            
        Returns:
            True if signature is valid or not required
            
        Raises:
            PluginSecurityError: If signature verification fails and is required
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            if self.require_signature:
                raise PluginSecurityError("Signature verification required but cryptography not available")
            self._logger.warning(f"Skipping signature verification for plugin {plugin.name}")
            return True
        
        # Get signature data
        sig_data = None
        if signature:
            sig_data = signature
        elif signature_file:
            sig_path = Path(signature_file)
            if sig_path.exists():
                with open(sig_path, 'rb') as f:
                    sig_data = f.read()
            else:
                if self.require_signature:
                    raise PluginSecurityError(f"Signature file not found: {signature_file}")
                self._logger.warning(f"Signature file not found for plugin {plugin.name}")
                return not self.require_signature
        
        if not sig_data:
            if self.require_signature:
                raise PluginSecurityError(f"No signature provided for plugin {plugin.name}")
            self._logger.info(f"No signature provided for plugin {plugin.name}")
            return True
        
        # Generate plugin hash for verification
        plugin_data = self._get_plugin_data_for_signing(plugin)
        plugin_hash = hashlib.sha256(plugin_data).digest()
        
        # Try to verify with each trusted key
        verification_successful = False
        
        for public_key in self._trusted_keys:
            try:
                public_key.verify(
                    sig_data,
                    plugin_hash,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                verification_successful = True
                self._logger.info(f"Signature verification successful for plugin {plugin.name}")
                break
                
            except InvalidSignature:
                continue
            except Exception as e:
                self._logger.error(f"Error verifying signature for plugin {plugin.name}: {e}")
                continue
        
        if not verification_successful:
            if self.require_signature:
                raise PluginSecurityError(
                    f"Signature verification failed for plugin {plugin.name}. "
                    f"No trusted key could verify the signature."
                )
            else:
                self._logger.warning(f"Signature verification failed for plugin {plugin.name}")
                return False
        
        return True
    
    def _get_plugin_data_for_signing(self, plugin: IPlugin) -> bytes:
        """
        Get plugin data for signature generation/verification.
        
        This creates a canonical representation of the plugin for signing.
        """
        # Create canonical plugin data
        plugin_info = {
            "name": plugin.name,
            "version": plugin.version,
            "kind": plugin.kind.value,
        }
        
        # Add metadata if available
        if hasattr(plugin.metadata, 'to_dict'):
            metadata = plugin.metadata.to_dict()
            # Remove mutable fields that shouldn't be part of signature
            metadata.pop('permissions_required', None)
            plugin_info["metadata"] = metadata
        
        # Create deterministic string representation
        import json
        canonical_data = json.dumps(plugin_info, sort_keys=True, separators=(',', ':'))
        return canonical_data.encode('utf-8')
    
    def verify_file_checksum(
        self, 
        file_path: Union[str, Path], 
        expected_checksum: str,
        algorithm: str = "sha256"
    ) -> bool:
        """
        Verify file checksum.
        
        Args:
            file_path: Path to file to verify
            expected_checksum: Expected checksum (hex string)
            algorithm: Hash algorithm (sha256, sha512, md5)
            
        Returns:
            True if checksum matches
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise PluginSecurityError(f"File not found: {file_path}")
        
        # Select hash algorithm
        if algorithm == "sha256":
            hasher = hashlib.sha256()
        elif algorithm == "sha512":
            hasher = hashlib.sha512()
        elif algorithm == "md5":
            hasher = hashlib.md5()
        else:
            raise PluginSecurityError(f"Unsupported hash algorithm: {algorithm}")
        
        # Calculate file hash
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            actual_checksum = hasher.hexdigest().lower()
            expected_checksum = expected_checksum.lower()
            
            matches = actual_checksum == expected_checksum
            
            if matches:
                self._logger.debug(f"Checksum verification successful for {file_path}")
            else:
                self._logger.warning(
                    f"Checksum mismatch for {file_path}: "
                    f"expected {expected_checksum}, got {actual_checksum}"
                )
            
            return matches
            
        except Exception as e:
            self._logger.error(f"Error calculating checksum for {file_path}: {e}")
            raise PluginSecurityError(f"Checksum calculation failed: {e}")
    
    def get_trusted_key_count(self) -> int:
        """Get number of trusted keys loaded."""
        return len(self._trusted_keys)
    
    def add_trusted_key(self, key: Union[str, Path, RSAPublicKey]) -> None:
        """Add a trusted public key."""
        if CRYPTOGRAPHY_AVAILABLE:
            public_key = self._load_public_key(key)
            self._trusted_keys.append(public_key)
            self._logger.info("Added trusted public key")
    
    def clear_trusted_keys(self) -> None:
        """Clear all trusted public keys."""
        self._trusted_keys.clear()
        self._logger.info("Cleared all trusted public keys")


class PluginSigner:
    """
    Plugin signing system for generating signatures.
    
    Note: This is typically used by plugin publishers, not the plugin system itself.
    """
    
    def __init__(self, private_key: Union[str, Path], logger: Optional[logging.Logger] = None):
        """
        Initialize plugin signer.
        
        Args:
            private_key: Path to private key file or PEM string
            logger: Optional logger instance
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise PluginSecurityError(
                "Cryptography library not available. "
                "Install with: pip install 'dotmac-plugins[security]'"
            )
        
        self._logger = logger or logging.getLogger(__name__)
        self._private_key = self._load_private_key(private_key)
    
    def _load_private_key(self, key: Union[str, Path]):
        """Load private key from file or string."""
        key_path = Path(key)
        
        if key_path.exists():
            with open(key_path, 'rb') as f:
                key_data = f.read()
        else:
            key_data = str(key).encode('utf-8')
        
        try:
            return serialization.load_pem_private_key(key_data, password=None)
        except Exception as e:
            raise PluginSecurityError(f"Failed to load private key: {e}")
    
    def sign_plugin(self, plugin: IPlugin) -> bytes:
        """
        Sign plugin and return signature.
        
        Args:
            plugin: Plugin to sign
            
        Returns:
            Plugin signature bytes
        """
        # Get plugin data for signing (same method as verifier)
        verifier = PluginSignatureVerifier()
        plugin_data = verifier._get_plugin_data_for_signing(plugin)
        plugin_hash = hashlib.sha256(plugin_data).digest()
        
        # Sign the hash
        try:
            signature = self._private_key.sign(
                plugin_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            self._logger.info(f"Successfully signed plugin {plugin.name}")
            return signature
            
        except Exception as e:
            raise PluginSecurityError(f"Failed to sign plugin {plugin.name}: {e}")
    
    def sign_file(self, file_path: Union[str, Path]) -> bytes:
        """
        Sign file and return signature.
        
        Args:
            file_path: Path to file to sign
            
        Returns:
            File signature bytes
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise PluginSecurityError(f"File not found: {file_path}")
        
        # Calculate file hash
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            file_hash = hasher.digest()
            
            # Sign the hash
            signature = self._private_key.sign(
                file_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            self._logger.info(f"Successfully signed file {file_path}")
            return signature
            
        except Exception as e:
            raise PluginSecurityError(f"Failed to sign file {file_path}: {e}")


def generate_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
    """
    Generate RSA key pair for plugin signing.
    
    Args:
        key_size: RSA key size in bits
        
    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise PluginSecurityError(
            "Cryptography library not available. "
            "Install with: pip install 'dotmac-plugins[security]'"
        )
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem


def create_self_signed_certificate(
    private_key_pem: bytes,
    subject_name: str = "Plugin Signer",
    validity_days: int = 365
) -> bytes:
    """
    Create self-signed certificate for plugin signing.
    
    Args:
        private_key_pem: Private key in PEM format
        subject_name: Certificate subject name
        validity_days: Certificate validity in days
        
    Returns:
        Certificate in PEM format
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise PluginSecurityError(
            "Cryptography library not available. "
            "Install with: pip install 'dotmac-plugins[security]'"
        )
    
    import datetime
    
    # Load private key
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COMMON_NAME, subject_name),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=validity_days)
    ).sign(private_key, hashes.SHA256())
    
    # Serialize certificate
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    
    return cert_pem