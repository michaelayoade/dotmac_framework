"""
Network Security Management

TLS/SSL certificate management, network encryption, and secure communications.
"""

import secrets
import ssl
from dataclasses import dataclass
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
from typing import Any

import structlog
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = structlog.get_logger(__name__)


class CertificateType(Enum):
    """Types of certificates"""

    SERVER = "server"
    CLIENT = "client"
    CA = "ca"
    INTERMEDIATE = "intermediate"


class CertificateStatus(Enum):
    """Certificate status"""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


@dataclass
class CertificateInfo:
    """Certificate information"""

    certificate_id: str
    certificate_type: CertificateType
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    status: CertificateStatus
    fingerprint: str
    key_size: int
    signature_algorithm: str
    san_dns: list[str]
    san_ip: list[str]

    def is_expired(self) -> bool:
        """Check if certificate has expired"""
        return utcnow() > self.not_after

    def expires_soon(self, days: int = 30) -> bool:
        """Check if certificate expires within specified days"""
        return utcnow() > (self.not_after - timedelta(days=days)


class CertificateManager:
    """SSL/TLS certificate management"""

    def __init__(self):
        """  Init   operation."""
        self.certificates: dict[str, CertificateInfo] = {}
        self.private_keys: dict[str, bytes] = {}
        self.certificate_chains: dict[str, list[bytes]] = {}
        self.ca_certificates: dict[str, bytes] = {}

        # Generate root CA
        self._generate_root_ca()

    def _generate_root_ca(self) -> None:
        """Generate root CA certificate"""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=4096, backend=default_backend()
        )

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DotMac Platform"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security"),
                x509.NameAttribute(NameOID.COMMON_NAME, "DotMac Root CA"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key()
            .serial_number(x509.random_serial_number()
            .not_valid_before(utcnow()
            .not_valid_after(utcnow() + timedelta(days=3650)  # 10 years
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key(),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    private_key.public_key()
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    key_agreement=False,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    digital_signature=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256(), default_backend()
        )

        # Store CA certificate and key
        cert_id = "root_ca"
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        self.ca_certificates[cert_id] = cert_pem
        self.private_keys[cert_id] = key_pem

        # Create certificate info
        cert_info = CertificateInfo(
            certificate_id=cert_id,
            certificate_type=CertificateType.CA,
            subject=cert.subject.rfc4514_string(),
            issuer=cert.issuer.rfc4514_string(),
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            status=CertificateStatus.ACTIVE,
            fingerprint=cert.fingerprint(hashes.SHA256().hex(),
            key_size=4096,
            signature_algorithm=cert.signature_algorithm_oid._name,
            san_dns=[],
            san_ip=[],
        )

        self.certificates[cert_id] = cert_info

        logger.info("Root CA certificate generated", cert_id=cert_id)

    def generate_server_certificate(
        self,
        common_name: str,
        san_dns: list[str] = None,
        san_ip: list[str] = None,
        validity_days: int = 365,
    ) -> str:
        """Generate server certificate"""

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        # Load CA certificate and key
        ca_cert_pem = self.ca_certificates["root_ca"]
        ca_key_pem = self.private_keys["root_ca"]

        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem, default_backend()
        ca_private_key = serialization.load_pem_private_key(
            ca_key_pem, password=None, backend=default_backend()
        )

        # Create certificate subject
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DotMac Platform"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Services"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )

        # Build certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(private_key.public_key()
            .serial_number(x509.random_serial_number()
            .not_valid_before(utcnow()
            .not_valid_after(utcnow() + timedelta(days=validity_days)
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key(),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    ca_private_key.public_key()
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    key_agreement=False,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    digital_signature=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    ]
                ),
                critical=True,
            )
        )

        # Add Subject Alternative Names
        san_list = []
        if san_dns:
            san_list.extend([x509.DNSName(name) for name in san_dns])
        if san_ip:
            import ipaddress

            san_list.extend([x509.IPAddress(ipaddress.ip_address(ip) for ip in san_ip])

        if san_list:
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )

        # Sign certificate
        cert = cert_builder.sign(ca_private_key, hashes.SHA256(), default_backend()

        # Generate certificate ID
        cert_id = f"server_{secrets.token_hex(8)}"

        # Store certificate and key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        self.certificates[cert_id] = CertificateInfo(
            certificate_id=cert_id,
            certificate_type=CertificateType.SERVER,
            subject=cert.subject.rfc4514_string(),
            issuer=cert.issuer.rfc4514_string(),
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            status=CertificateStatus.ACTIVE,
            fingerprint=cert.fingerprint(hashes.SHA256().hex(),
            key_size=2048,
            signature_algorithm=cert.signature_algorithm_oid._name,
            san_dns=san_dns or [],
            san_ip=san_ip or [],
        )

        self.private_keys[cert_id] = key_pem
        self.certificate_chains[cert_id] = [cert_pem, ca_cert_pem]

        logger.info(
            "Server certificate generated", cert_id=cert_id, common_name=common_name
        )

        return cert_id

    def get_certificate_info(self, cert_id: str) -> CertificateInfo | None:
        """Get certificate information"""
        return self.certificates.get(cert_id)

    def get_certificate_pem(self, cert_id: str) -> bytes | None:
        """Get certificate in PEM format"""
        if cert_id in self.certificate_chains:
            return self.certificate_chains[cert_id][0]
        elif cert_id in self.ca_certificates:
            return self.ca_certificates[cert_id]
        return None

    def get_private_key_pem(self, cert_id: str) -> bytes | None:
        """Get private key in PEM format"""
        return self.private_keys.get(cert_id)

    def get_certificate_chain(self, cert_id: str) -> list[bytes] | None:
        """Get full certificate chain"""
        return self.certificate_chains.get(cert_id)

    def revoke_certificate(self, cert_id: str) -> bool:
        """Revoke a certificate"""
        if cert_id in self.certificates:
            self.certificates[cert_id].status = CertificateStatus.REVOKED
            logger.info("Certificate revoked", cert_id=cert_id)
            return True
        return False

    def check_expiring_certificates(self, days: int = 30) -> list[CertificateInfo]:
        """Check for certificates expiring within specified days"""
        expiring = []

        for cert_info in self.certificates.values():
            if cert_info.status == CertificateStatus.ACTIVE and cert_info.expires_soon(
                days
            ):
                expiring.append(cert_info)

        return expiring

    def auto_renew_certificates(self) -> list[str]:
        """Automatically renew expiring certificates"""
        renewed = []
        expiring = self.check_expiring_certificates(30)

        for cert_info in expiring:
            if cert_info.certificate_type == CertificateType.SERVER:
                try:
                    # Extract common name from subject
                    subject_parts = dict(
                        part.split("=") for part in cert_info.subject.split(",")
                    )
                    common_name = subject_parts.get("CN", "localhost")

                    # Generate new certificate
                    new_cert_id = self.generate_server_certificate(
                        common_name=common_name,
                        san_dns=cert_info.san_dns,
                        san_ip=cert_info.san_ip,
                    )

                    # Revoke old certificate
                    self.revoke_certificate(cert_info.certificate_id)

                    renewed.append(new_cert_id)

                    logger.info(
                        "Certificate auto-renewed",
                        old_cert_id=cert_info.certificate_id,
                        new_cert_id=new_cert_id,
                    )

                except Exception as e:
                    logger.error(
                        "Certificate auto-renewal failed",
                        cert_id=cert_info.certificate_id,
                        error=str(e),
                    )

        return renewed


class TLSManager:
    """TLS configuration and context management"""

    def __init__(self, certificate_manager: CertificateManager):
        """  Init   operation."""
        self.certificate_manager = certificate_manager
        self.tls_contexts: dict[str, ssl.SSLContext] = {}

    def create_server_context(self, cert_id: str) -> ssl.SSLContext | None:
        """Create SSL context for server"""
        cert_pem = self.certificate_manager.get_certificate_pem(cert_id)
        key_pem = self.certificate_manager.get_private_key_pem(cert_id)

        if not cert_pem or not key_pem:
            logger.error("Certificate or key not found", cert_id=cert_id)
            return None

        try:
            # Create SSL context
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

            # Load certificate chain from memory using temporary files
            import os
            import tempfile

            with tempfile.NamedTemporaryFile(mode="wb", delete=False) as cert_file:
                cert_file.write(cert_pem)
                cert_file_path = cert_file.name

            with tempfile.NamedTemporaryFile(mode="wb", delete=False) as key_file:
                key_file.write(key_pem)
                key_file_path = key_file.name

            try:
                context.load_cert_chain(cert_file_path, key_file_path)
            finally:
                os.unlink(cert_file_path)
                os.unlink(key_file_path)

            # Configure security settings
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.set_ciphers(
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
            )
            context.set_alpn_protocols(["h2", "http/1.1"])

            # Store context
            self.tls_contexts[cert_id] = context

            logger.info("TLS server context created", cert_id=cert_id)
            return context

        except Exception as e:
            logger.error("Failed to create TLS context", cert_id=cert_id, error=str(e)
            return None

    def create_client_context(
        self, verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED
    ) -> ssl.SSLContext:
        """Create SSL context for client connections"""
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = verify_mode
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        return context

    def get_context(self, cert_id: str) -> ssl.SSLContext | None:
        """Get cached SSL context"""
        return self.tls_contexts.get(cert_id)


class NetworkSecurityManager:
    """Network security manager"""

    def __init__(self):
        """  Init   operation."""
        self.certificate_manager = CertificateManager()
        self.tls_manager = TLSManager(self.certificate_manager)
        self.trusted_networks: list[str] = []
        self.blocked_ips: set = set()
        self.rate_limits: dict[str, dict[str, Any]] = {}

    def add_trusted_network(self, network: str) -> None:
        """Add trusted network CIDR"""
        self.trusted_networks.append(network)
        logger.info("Trusted network added", network=network)

    def block_ip(self, ip_address: str) -> None:
        """Block IP address"""
        self.blocked_ips.add(ip_address)
        logger.warning("IP address blocked", ip_address=ip_address)

    def unblock_ip(self, ip_address: str) -> None:
        """Unblock IP address"""
        self.blocked_ips.discard(ip_address)
        logger.info("IP address unblocked", ip_address=ip_address)

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips

    def is_trusted_network(self, ip_address: str) -> bool:
        """Check if IP is in trusted network"""
        import ipaddress

        try:
            ip = ipaddress.ip_address(ip_address)
            for network in self.trusted_networks:
                if ip in ipaddress.ip_network(network):
                    return True
        except ValueError:
            pass

        return False

    def setup_secure_server(
        self, host: str, port: int, cert_id: str | None = None
    ) -> tuple[str, ssl.SSLContext]:
        """Setup secure server with TLS"""

        # Generate certificate if not provided
        if not cert_id:
            cert_id = self.certificate_manager.generate_server_certificate(
                common_name=host,
                san_dns=[host] if not self._is_ip_address(host) else [],
                san_ip=[host] if self._is_ip_address(host) else [],
            )

        # Create TLS context
        tls_context = self.tls_manager.create_server_context(cert_id)
        if not tls_context:
            raise RuntimeError(f"Failed to create TLS context for {cert_id}")

        logger.info("Secure server configured", host=host, port=port, cert_id=cert_id)

        return cert_id, tls_context

    def _is_ip_address(self, addr: str) -> bool:
        """Check if string is an IP address"""
        try:
            import ipaddress

            ipaddress.ip_address(addr)
            return True
        except ValueError:
            return False

    async def validate_connection(
        self, client_ip: str, user_agent: str | None = None
    ) -> bool:
        """Validate incoming connection"""

        # Check if IP is blocked
        if self.is_ip_blocked(client_ip):
            logger.warning("Blocked IP attempted connection", ip=client_ip)
            return False

        # Check rate limiting
        current_time = utcnow()
        rate_limit_key = f"ip:{client_ip}"

        if rate_limit_key in self.rate_limits:
            limit_info = self.rate_limits[rate_limit_key]
            if current_time < limit_info["reset_time"]:
                if limit_info["count"] >= limit_info["limit"]:
                    logger.warning("Rate limit exceeded", ip=client_ip)
                    return False
                limit_info["count"] += 1
            else:
                # Reset rate limit
                self.rate_limits[rate_limit_key] = {
                    "count": 1,
                    "limit": 100,  # 100 requests per minute
                    "reset_time": current_time + timedelta(minutes=1),
                }
        else:
            # Initialize rate limit
            self.rate_limits[rate_limit_key] = {
                "count": 1,
                "limit": 100,
                "reset_time": current_time + timedelta(minutes=1),
            }

        return True

    def get_security_headers(self) -> dict[str, str]:
        """Get security headers for HTTP responses"""
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
