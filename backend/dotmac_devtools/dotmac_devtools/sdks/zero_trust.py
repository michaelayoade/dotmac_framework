"""
Zero Trust Security SDK - Service mesh security, mTLS, and policy management.
"""

from datetime import datetime, timedelta
from dotmac_devtools.core.datetime_utils import utc_now, utc_now_iso
from typing import Any
from uuid import uuid4

import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ..core.config import DevToolsConfig
from ..core.exceptions import PolicyError


class ZeroTrustSecurityService:
    """Core service for zero-trust security implementation."""

    def __init__(self, config: DevToolsConfig):
        self.config = config

        # In-memory storage (would be replaced with persistent storage)
        self._service_identities: dict[str, dict[str, Any]] = {}
        self._certificates: dict[str, dict[str, Any]] = {}
        self._policies: dict[str, dict[str, Any]] = {}
        self._service_mesh_config: dict[str, Any] = {}
        self._trust_domains: dict[str, dict[str, Any]] = {}

    async def initialize_zero_trust(self, **kwargs) -> dict[str, Any]:
        """Initialize zero-trust security model."""

        cluster_name = kwargs.get('cluster_name', 'default-cluster')
        trust_domain = kwargs.get('trust_domain', 'dotmac.local')

        # Initialize root CA
        root_ca = await self._create_root_ca(trust_domain)

        # Configure service mesh
        mesh_config = {
            'cluster_name': cluster_name,
            'trust_domain': trust_domain,
            'provider': kwargs.get('provider', self.config.security.service_mesh_provider),
            'enable_mtls': kwargs.get('enable_mtls', self.config.security.enforce_mtls),
            'policy_enforcement': kwargs.get('policy_enforcement', self.config.security.policy_enforcement),
            'root_ca': root_ca,
            'created_at': utc_now().isoformat(),
        }

        self._service_mesh_config[cluster_name] = mesh_config

        # Create default policies
        await self._create_default_policies(cluster_name)

        return mesh_config

    async def create_service_identity(self, **kwargs) -> dict[str, Any]:
        """Create service identity with certificate."""

        service_name = kwargs['service_name']
        namespace = kwargs.get('namespace', 'default')
        cluster_name = kwargs.get('cluster_name', 'default-cluster')

        # Generate service certificate
        cert_data = await self._generate_service_certificate(
            service_name, namespace, cluster_name
        )

        # Create service identity
        identity_id = str(uuid4())

        identity = {
            'identity_id': identity_id,
            'service_name': service_name,
            'namespace': namespace,
            'cluster_name': cluster_name,
            'spiffe_id': f"spiffe://{self._get_trust_domain(cluster_name)}/ns/{namespace}/sa/{service_name}",
            'certificate': cert_data,
            'scopes': kwargs.get('scopes', ['default']),
            'roles': kwargs.get('roles', ['service']),
            'created_at': utc_now().isoformat(),
            'expires_at': cert_data['expires_at'],
            'status': 'active',
        }

        self._service_identities[identity_id] = identity

        return identity

    async def create_security_policy(self, **kwargs) -> dict[str, Any]:
        """Create security policy for service communication."""

        policy_id = str(uuid4())

        policy = {
            'policy_id': policy_id,
            'name': kwargs['name'],
            'cluster_name': kwargs.get('cluster_name', 'default-cluster'),
            'source_service': kwargs.get('source_service'),
            'source_namespace': kwargs.get('source_namespace'),
            'destination_service': kwargs.get('destination_service'),
            'destination_namespace': kwargs.get('destination_namespace'),
            'action': kwargs.get('action', 'allow'),  # allow, deny
            'conditions': kwargs.get('conditions', []),
            'require_mtls': kwargs.get('require_mtls', True),
            'require_jwt': kwargs.get('require_jwt', False),
            'allowed_methods': kwargs.get('allowed_methods', ['GET', 'POST', 'PUT', 'DELETE']),
            'rate_limit': kwargs.get('rate_limit'),
            'priority': kwargs.get('priority', 100),
            'created_at': utc_now().isoformat(),
            'updated_at': utc_now().isoformat(),
            'status': 'active',
        }

        self._policies[policy_id] = policy

        return policy

    async def generate_istio_policy(self, policy_id: str) -> dict[str, Any]:
        """Generate Istio policy manifests."""

        policy = self._policies.get(policy_id)
        if not policy:
            raise PolicyError(f"Policy not found: {policy_id}")

        # Generate AuthorizationPolicy
        auth_policy = {
            'apiVersion': 'security.istio.io/v1beta1',
            'kind': 'AuthorizationPolicy',
            'metadata': {
                'name': f"policy-{policy['name'].lower().replace(' ', '-')}",
                'namespace': policy.get('destination_namespace', 'default')
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': policy['destination_service']
                    }
                },
                'rules': []
            }
        }

        # Add rules based on policy
        if policy['action'] == 'allow':
            rule = {
                'from': [{
                    'source': {
                        'principals': [f"cluster.local/ns/{policy.get('source_namespace', 'default')}/sa/{policy['source_service']}"]
                    }
                }],
                'to': [{
                    'operation': {
                        'methods': policy['allowed_methods']
                    }
                }]
            }
            auth_policy['spec']['rules'].append(rule)

        # Generate PeerAuthentication for mTLS
        peer_auth = None
        if policy['require_mtls']:
            peer_auth = {
                'apiVersion': 'security.istio.io/v1beta1',
                'kind': 'PeerAuthentication',
                'metadata': {
                    'name': f"mtls-{policy['destination_service']}",
                    'namespace': policy.get('destination_namespace', 'default')
                },
                'spec': {
                    'selector': {
                        'matchLabels': {
                            'app': policy['destination_service']
                        }
                    },
                    'mtls': {
                        'mode': 'STRICT'
                    }
                }
            }

        manifests = {
            'authorization_policy': auth_policy,
            'peer_authentication': peer_auth
        }

        return {
            'policy_id': policy_id,
            'manifests': manifests,
            'yaml_content': self._convert_to_yaml(manifests)
        }

    async def audit_security_policies(self, cluster_name: str = 'default-cluster') -> dict[str, Any]:
        """Audit security policies and identify gaps."""

        cluster_policies = [
            policy for policy in self._policies.values()
            if policy['cluster_name'] == cluster_name
        ]

        # Identify potential security gaps
        gaps = []
        warnings = []

        # Check for services without explicit policies
        services_with_policies = set()
        for policy in cluster_policies:
            if policy['destination_service']:
                services_with_policies.add(f"{policy['destination_namespace']}/{policy['destination_service']}")

        # Check for overly permissive policies
        for policy in cluster_policies:
            if policy['action'] == 'allow' and not policy['conditions']:
                warnings.append(f"Policy {policy['name']} allows unrestricted access")

            if not policy['require_mtls']:
                warnings.append(f"Policy {policy['name']} does not require mTLS")

        # Check certificate expiration
        expiring_certs = []
        for identity in self._service_identities.values():
            if identity['cluster_name'] == cluster_name:
                expires_at = datetime.fromisoformat(identity['expires_at'])
                days_until_expiry = (expires_at - utc_now()).days

                if days_until_expiry < 30:
                    expiring_certs.append({
                        'service': identity['service_name'],
                        'namespace': identity['namespace'],
                        'expires_in_days': days_until_expiry
                    })

        return {
            'cluster_name': cluster_name,
            'total_policies': len(cluster_policies),
            'active_policies': len([p for p in cluster_policies if p['status'] == 'active']),
            'security_gaps': gaps,
            'warnings': warnings,
            'expiring_certificates': expiring_certs,
            'audit_timestamp': utc_now().isoformat()
        }

    async def rotate_certificates(self, cluster_name: str = 'default-cluster') -> dict[str, Any]:
        """Rotate certificates for services."""

        rotated = []
        failed = []

        for identity in self._service_identities.values():
            if identity['cluster_name'] != cluster_name:
                continue

            expires_at = datetime.fromisoformat(identity['expires_at'])
            days_until_expiry = (expires_at - utc_now()).days

            # Rotate if expiring within 30 days
            if days_until_expiry < 30:
                try:
                    new_cert = await self._generate_service_certificate(
                        identity['service_name'],
                        identity['namespace'],
                        cluster_name
                    )

                    identity['certificate'] = new_cert
                    identity['expires_at'] = new_cert['expires_at']
                    identity['updated_at'] = utc_now().isoformat()

                    rotated.append({
                        'service': identity['service_name'],
                        'namespace': identity['namespace'],
                        'new_expiry': new_cert['expires_at']
                    })

                except Exception as e:
                    failed.append({
                        'service': identity['service_name'],
                        'namespace': identity['namespace'],
                        'error': str(e)
                    })

        return {
            'cluster_name': cluster_name,
            'rotated_certificates': rotated,
            'failed_rotations': failed,
            'rotation_timestamp': utc_now().isoformat()
        }

    async def _create_root_ca(self, trust_domain: str) -> dict[str, Any]:
        """Create root certificate authority."""

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "DotMac ISP"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"DotMac Root CA - {trust_domain}"),
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
            utc_now()
        ).not_valid_after(
            utc_now() + timedelta(days=3650)  # 10 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        # Serialize certificate and key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        return {
            'certificate': cert_pem.decode('utf-8'),
            'private_key': key_pem.decode('utf-8'),
            'trust_domain': trust_domain,
            'expires_at': cert.not_valid_after.isoformat(),
            'created_at': utc_now().isoformat()
        }

    async def _generate_service_certificate(self, service_name: str, namespace: str, cluster_name: str) -> dict[str, Any]:
        """Generate certificate for a service."""

        trust_domain = self._get_trust_domain(cluster_name)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"{service_name}.{namespace}.svc.cluster.local"),
        ])

        # Get root CA (for demo, we'll use a simple issuer)
        issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"DotMac Root CA - {trust_domain}"),
        ])

        # Generate SPIFFE ID
        spiffe_id = f"spiffe://{trust_domain}/ns/{namespace}/sa/{service_name}"

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            utc_now()
        ).not_valid_after(
            utc_now() + timedelta(days=self.config.security.default_cert_validity)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{service_name}.{namespace}.svc.cluster.local"),
                x509.DNSName(f"{service_name}.{namespace}"),
                x509.DNSName(service_name),
                x509.UniformResourceIdentifier(spiffe_id),
            ]),
            critical=False,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=False,
                crl_sign=False,
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        # Serialize certificate and key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        return {
            'certificate': cert_pem.decode('utf-8'),
            'private_key': key_pem.decode('utf-8'),
            'spiffe_id': spiffe_id,
            'expires_at': cert.not_valid_after.isoformat(),
            'created_at': utc_now().isoformat()
        }

    async def _create_default_policies(self, cluster_name: str):
        """Create default security policies."""

        default_policies = [
            {
                'name': 'Default Deny All',
                'cluster_name': cluster_name,
                'action': 'deny',
                'priority': 1000,
                'conditions': []
            },
            {
                'name': 'Allow Internal Services',
                'cluster_name': cluster_name,
                'action': 'allow',
                'require_mtls': True,
                'priority': 500,
                'conditions': [
                    {'source_namespace': 'default'},
                    {'destination_namespace': 'default'}
                ]
            }
        ]

        for policy_data in default_policies:
            await self.create_security_policy(**policy_data)

    def _get_trust_domain(self, cluster_name: str) -> str:
        """Get trust domain for cluster."""
        mesh_config = self._service_mesh_config.get(cluster_name, {})
        return mesh_config.get('trust_domain', 'dotmac.local')

    def _convert_to_yaml(self, manifests: dict[str, Any]) -> str:
        """Convert manifests to YAML format."""
        yaml_docs = []
        for name, manifest in manifests.items():
            if manifest:
                yaml_docs.append(yaml.dump(manifest, default_flow_style=False))

        return "---\n".join(yaml_docs)


class ZeroTrustSecuritySDK:
    """SDK for zero-trust security implementation."""

    def __init__(self, config: DevToolsConfig | None = None):
        self.config = config or DevToolsConfig()
        self._service = ZeroTrustSecurityService(self.config)

    async def initialize_zero_trust(
        self,
        cluster_name: str = "default-cluster",
        trust_domain: str = "dotmac.local",
        **kwargs
    ) -> dict[str, Any]:
        """Initialize zero-trust security model."""
        return await self._service.initialize_zero_trust(
            cluster_name=cluster_name,
            trust_domain=trust_domain,
            **kwargs
        )

    async def create_service_identity(
        self,
        service_name: str,
        namespace: str = "default",
        **kwargs
    ) -> dict[str, Any]:
        """Create service identity with certificate."""
        return await self._service.create_service_identity(
            service_name=service_name,
            namespace=namespace,
            **kwargs
        )

    async def create_security_policy(
        self,
        name: str,
        source_service: str = None,
        destination_service: str = None,
        **kwargs
    ) -> dict[str, Any]:
        """Create security policy."""
        return await self._service.create_security_policy(
            name=name,
            source_service=source_service,
            destination_service=destination_service,
            **kwargs
        )

    async def generate_istio_policy(self, policy_id: str) -> dict[str, Any]:
        """Generate Istio policy manifests."""
        return await self._service.generate_istio_policy(policy_id)

    async def audit_security_policies(self, cluster_name: str = "default-cluster") -> dict[str, Any]:
        """Audit security policies."""
        return await self._service.audit_security_policies(cluster_name)

    async def rotate_certificates(self, cluster_name: str = "default-cluster") -> dict[str, Any]:
        """Rotate certificates for services."""
        return await self._service.rotate_certificates(cluster_name)
