"""Automated SSL certificate management for DotMac ISP Framework."""

import asyncio
import logging
import os
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
from dataclasses import dataclass

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CertificateInfo:
    """Certificate information container."""

    domain: str
    cert_path: str
    key_path: str
    issued_date: datetime
    expiry_date: datetime
    days_until_expiry: int

    @property
    def is_expiring(self) -> bool:
        """Check if certificate expires within 30 days."""
        return self.days_until_expiry <= 30

    @property
    def is_expired(self) -> bool:
        """Check if certificate has expired."""
        return self.days_until_expiry <= 0


class SSLCertificateManager:
    """Automated SSL certificate manager with Let's Encrypt integration."""

    def __init__(self):
        """Initialize SSL certificate manager."""
        self.settings = get_settings()
        self.cert_dir = Path("/etc/ssl/dotmac")
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        # ACME client configuration
        self.acme_staging = self.settings.environment != "production"
        self.acme_server = (
            "https://acme-staging-v02.api.letsencrypt.org/directory"
            if self.acme_staging
            else "https://acme-v02.api.letsencrypt.org/directory"
        )

        self.email = getattr(self.settings, "ssl_email", None)
        self.domains = getattr(self.settings, "ssl_domains", "").split(",")
        self.domains = [d.strip() for d in self.domains if d.strip()]

        logger.info(f"SSL Manager initialized for domains: {self.domains}")
        if self.acme_staging:
            logger.warning("Using Let's Encrypt staging environment")

    async def get_certificate_info(self, domain: str) -> Optional[CertificateInfo]:
        """Get information about existing certificate."""
        cert_path = self.cert_dir / f"{domain}.crt"
        key_path = self.cert_dir / f"{domain}.key"

        if not cert_path.exists():
            return None

        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            cert = x509.load_pem_x509_certificate(cert_data)

            issued_date = cert.not_valid_before
            expiry_date = cert.not_valid_after
            days_until_expiry = (expiry_date - datetime.utcnow()).days

            return CertificateInfo(
                domain=domain,
                cert_path=str(cert_path),
                key_path=str(key_path),
                issued_date=issued_date,
                expiry_date=expiry_date,
                days_until_expiry=days_until_expiry,
            )

        except Exception as e:
            logger.error(f"Failed to read certificate for {domain}: {e}")
            return None

    async def generate_self_signed_certificate(self, domain: str) -> bool:
        """Generate self-signed certificate for development."""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Create certificate subject
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                    x509.NameAttribute(
                        NameOID.ORGANIZATION_NAME, "DotMac ISP Framework"
                    ),
                    x509.NameAttribute(NameOID.COMMON_NAME, domain),
                ]
            )

            # Create certificate
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=365))
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName(domain),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # Write certificate
            cert_path = self.cert_dir / f"{domain}.crt"
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            # Write private key
            key_path = self.cert_dir / f"{domain}.key"
            with open(key_path, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            # Set proper permissions
            os.chmod(cert_path, 0o644)
            os.chmod(key_path, 0o600)

            logger.info(f"✅ Generated self-signed certificate for {domain}")
            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to generate self-signed certificate for {domain}: {e}"
            )
            return False

    async def obtain_letsencrypt_certificate(self, domain: str) -> bool:
        """Obtain certificate from Let's Encrypt using certbot."""
        if not self.email:
            logger.error("SSL email not configured for Let's Encrypt")
            return False

        try:
            # Check if certbot is available
            result = await asyncio.create_subprocess_exec(
                "which",
                "certbot",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            if result.returncode != 0:
                logger.error(
                    "certbot not found. Please install certbot for Let's Encrypt certificates"
                )
                return await self.generate_self_signed_certificate(domain)

            # Obtain certificate using certbot
            cmd = [
                "certbot",
                "certonly",
                "--standalone",
                "--non-interactive",
                "--agree-tos",
                f"--email={self.email}",
                f"--server={self.acme_server}",
                "--cert-name",
                domain,
                "--cert-path",
                str(self.cert_dir / f"{domain}.crt"),
                "--key-path",
                str(self.cert_dir / f"{domain}.key"),
                "-d",
                domain,
            ]

            if self.acme_staging:
                cmd.append("--staging")

            result = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                logger.info(f"✅ Obtained Let's Encrypt certificate for {domain}")
                return True
            else:
                logger.error(f"❌ certbot failed for {domain}: {stderr.decode()}")
                logger.info(f"Falling back to self-signed certificate for {domain}")
                return await self.generate_self_signed_certificate(domain)

        except Exception as e:
            logger.error(
                f"❌ Failed to obtain Let's Encrypt certificate for {domain}: {e}"
            )
            logger.info(f"Falling back to self-signed certificate for {domain}")
            return await self.generate_self_signed_certificate(domain)

    async def renew_certificate(self, domain: str) -> bool:
        """Renew certificate for domain."""
        logger.info(f"Renewing certificate for {domain}")

        if self.settings.environment == "production" and self.email:
            return await self.obtain_letsencrypt_certificate(domain)
        else:
            return await self.generate_self_signed_certificate(domain)

    async def ensure_certificates(self) -> Dict[str, bool]:
        """Ensure certificates exist for all configured domains."""
        results = {}

        for domain in self.domains:
            if not domain:
                continue

            cert_info = await self.get_certificate_info(domain)

            if not cert_info:
                logger.info(f"No certificate found for {domain}, obtaining new one")
                success = await self.renew_certificate(domain)
                results[domain] = success
            elif cert_info.is_expiring:
                logger.info(
                    f"Certificate for {domain} expires in {cert_info.days_until_expiry} days, renewing"
                )
                success = await self.renew_certificate(domain)
                results[domain] = success
            else:
                logger.info(
                    f"Certificate for {domain} is valid for {cert_info.days_until_expiry} more days"
                )
                results[domain] = True

        return results

    async def get_ssl_context(self, domain: str) -> Optional[ssl.SSLContext]:
        """Get SSL context for domain."""
        cert_info = await self.get_certificate_info(domain)
        if not cert_info:
            return None

        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(cert_info.cert_path, cert_info.key_path)
            return context
        except Exception as e:
            logger.error(f"Failed to create SSL context for {domain}: {e}")
            return None

    async def get_certificate_status(self) -> List[CertificateInfo]:
        """Get status of all configured certificates."""
        certificates = []

        for domain in self.domains:
            if not domain:
                continue

            cert_info = await self.get_certificate_info(domain)
            if cert_info:
                certificates.append(cert_info)

        return certificates

    async def setup_certificate_renewal_cron(self) -> bool:
        """Setup automatic certificate renewal via cron."""
        try:
            # Create renewal script
            script_path = self.cert_dir / "renew_certificates.py"
            script_content = f'''#!/usr/bin/env python3
"""Automatic certificate renewal script for DotMac ISP Framework."""

import asyncio
import sys
import os

# Add the source directory to Python path
sys.path.insert(0, "/home/dotmac_framework/dotmac_isp_framework/src")

from dotmac_isp.core.ssl_manager import get_ssl_manager

async def main():
    """Main renewal function."""
    ssl_manager = get_ssl_manager()
    results = await ssl_manager.ensure_certificates()
    
    for domain, success in results.items():
        if success:
            print(f"✅ Certificate for {{domain}} is up to date")
        else:
            print(f"❌ Failed to renew certificate for {{domain}}")
    
    # Restart application if any certificates were renewed
    if any(results.values()):
        print("Certificates were renewed, consider restarting the application")

if __name__ == "__main__":
    asyncio.run(main())
'''

            with open(script_path, "w") as f:
                f.write(script_content)

            os.chmod(script_path, 0o755)

            logger.info(f"✅ Created certificate renewal script at {script_path}")
            logger.info("To enable automatic renewal, add this to crontab:")
            logger.info(f"0 2 * * * /usr/bin/python3 {script_path}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to setup certificate renewal: {e}")
            return False


# Global SSL manager instance
_ssl_manager = None


def get_ssl_manager() -> SSLCertificateManager:
    """Get the global SSL manager instance."""
    global _ssl_manager
    if _ssl_manager is None:
        _ssl_manager = SSLCertificateManager()
    return _ssl_manager


async def initialize_ssl() -> bool:
    """Initialize SSL certificates on application startup."""
    ssl_manager = get_ssl_manager()

    # Ensure certificates exist
    results = await ssl_manager.ensure_certificates()

    # Setup renewal script
    await ssl_manager.setup_certificate_renewal_cron()

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    if success_count == total_count:
        logger.info(
            f"✅ SSL initialization complete: {success_count}/{total_count} certificates ready"
        )
        return True
    else:
        logger.warning(
            f"⚠️  SSL initialization partial: {success_count}/{total_count} certificates ready"
        )
        return False
