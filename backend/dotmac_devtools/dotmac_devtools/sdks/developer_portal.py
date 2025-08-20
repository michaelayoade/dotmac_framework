"""
Developer Portal SDK - Self-service API access, documentation, and partner management.
"""

import secrets
from datetime import datetime, timedelta
from dotmac_devtools.core.datetime_utils import utc_now, utc_now_iso
from typing import Any
from uuid import uuid4

from ..core.config import DevToolsConfig
from ..core.exceptions import ValidationError


class DeveloperPortalService:
    """Core service for developer portal management."""

    def __init__(self, config: DevToolsConfig):
        self.config = config

        # In-memory storage (would be replaced with persistent storage)
        self._developers: dict[str, dict[str, Any]] = {}
        self._applications: dict[str, dict[str, Any]] = {}
        self._api_keys: dict[str, dict[str, Any]] = {}
        self._usage_metrics: dict[str, list[dict[str, Any]]] = {}
        self._documentation: dict[str, dict[str, Any]] = {}
        self._portal_config: dict[str, Any] = {}

    async def initialize_portal(self, **kwargs) -> dict[str, Any]:
        """Initialize developer portal."""

        portal_config = {
            'portal_id': str(uuid4()),
            'domain': kwargs.get('domain', self.config.portal.default_domain),
            'title': kwargs.get('title', 'Developer Portal'),
            'description': kwargs.get('description', 'API Developer Portal'),
            'company_name': kwargs.get('company_name', 'DotMac ISP'),
            'support_email': kwargs.get('support_email', 'api-support@dotmac.com'),
            'auth_provider': kwargs.get('auth_provider', self.config.portal.auth_provider),
            'approval_workflow': kwargs.get('approval_workflow', self.config.portal.approval_workflow),
            'enable_analytics': kwargs.get('enable_analytics', True),
            'enable_rate_limiting': kwargs.get('enable_rate_limiting', True),
            'enable_webhooks': kwargs.get('enable_webhooks', True),
            'theme': kwargs.get('theme', 'default'),
            'custom_css': kwargs.get('custom_css'),
            'custom_logo': kwargs.get('custom_logo'),
            'created_at': utc_now().isoformat(),
            'updated_at': utc_now().isoformat(),
        }

        self._portal_config = portal_config

        # Generate initial API documentation
        await self._generate_default_documentation()

        return portal_config

    async def register_developer(self, **kwargs) -> dict[str, Any]:
        """Register a new developer."""

        developer_id = str(uuid4())

        developer = {
            'developer_id': developer_id,
            'email': kwargs['email'],
            'name': kwargs.get('name', ''),
            'company': kwargs.get('company', ''),
            'phone': kwargs.get('phone', ''),
            'use_case': kwargs.get('use_case', ''),
            'expected_volume': kwargs.get('expected_volume', 'low'),
            'status': 'pending' if self._portal_config.get('approval_workflow') == 'manual' else 'approved',
            'tier': kwargs.get('tier', 'starter'),
            'rate_limits': self._get_tier_rate_limits(kwargs.get('tier', 'starter')),
            'registration_date': utc_now().isoformat(),
            'last_login': None,
            'metadata': kwargs.get('metadata', {}),
        }

        self._developers[developer_id] = developer

        # Auto-approve if configured
        if self._portal_config.get('approval_workflow') == 'automatic':
            await self._approve_developer(developer_id)

        return developer

    async def approve_developer(self, developer_id: str) -> dict[str, Any]:
        """Approve a developer registration."""
        return await self._approve_developer(developer_id)

    async def _approve_developer(self, developer_id: str) -> dict[str, Any]:
        """Internal method to approve developer."""

        developer = self._developers.get(developer_id)
        if not developer:
            raise ValidationError(f"Developer not found: {developer_id}")

        developer['status'] = 'approved'
        developer['approved_at'] = utc_now().isoformat()

        # Create default application
        app = await self.create_application(
            developer_id=developer_id,
            name=f"{developer['name']} Default App",
            description="Default application for API access"
        )

        return {
            'developer': developer,
            'default_application': app
        }

    async def create_application(self, **kwargs) -> dict[str, Any]:
        """Create a new application for a developer."""

        developer_id = kwargs['developer_id']
        developer = self._developers.get(developer_id)
        if not developer:
            raise ValidationError(f"Developer not found: {developer_id}")

        if developer['status'] != 'approved':
            raise ValidationError("Developer must be approved to create applications")

        app_id = str(uuid4())

        application = {
            'app_id': app_id,
            'developer_id': developer_id,
            'name': kwargs['name'],
            'description': kwargs.get('description', ''),
            'type': kwargs.get('type', 'web'),
            'callback_urls': kwargs.get('callback_urls', []),
            'scopes': kwargs.get('scopes', ['api:read']),
            'status': 'active',
            'created_at': utc_now().isoformat(),
            'updated_at': utc_now().isoformat(),
        }

        self._applications[app_id] = application

        # Generate API key
        api_key = await self.generate_api_key(app_id)
        application['api_key'] = api_key

        return application

    async def generate_api_key(self, app_id: str) -> dict[str, Any]:
        """Generate API key for an application."""

        application = self._applications.get(app_id)
        if not application:
            raise ValidationError(f"Application not found: {app_id}")

        developer = self._developers.get(application['developer_id'])
        if not developer:
            raise ValidationError("Developer not found")

        key_id = str(uuid4())
        api_key = f"ak_{secrets.token_urlsafe(32)}"

        api_key_data = {
            'key_id': key_id,
            'api_key': api_key,
            'app_id': app_id,
            'developer_id': application['developer_id'],
            'name': f"API Key for {application['name']}",
            'scopes': application['scopes'],
            'rate_limits': developer['rate_limits'],
            'status': 'active',
            'created_at': utc_now().isoformat(),
            'expires_at': (utc_now() + timedelta(days=365)).isoformat(),
            'last_used_at': None,
            'usage_count': 0,
        }

        self._api_keys[api_key] = api_key_data

        return api_key_data

    async def validate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Validate an API key."""

        key_data = self._api_keys.get(api_key)
        if not key_data:
            return None

        if key_data['status'] != 'active':
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(key_data['expires_at'])
        if utc_now() > expires_at:
            return None

        # Update usage statistics
        key_data['last_used_at'] = utc_now().isoformat()
        key_data['usage_count'] += 1

        # Record usage metrics
        await self._record_api_usage(api_key, {
            'timestamp': utc_now().isoformat(),
            'api_key': api_key,
            'app_id': key_data['app_id'],
            'developer_id': key_data['developer_id'],
        })

        return key_data

    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""

        key_data = self._api_keys.get(api_key)
        if not key_data:
            return False

        key_data['status'] = 'revoked'
        key_data['revoked_at'] = utc_now().isoformat()

        return True

    async def get_usage_metrics(self, developer_id: str, **filters) -> dict[str, Any]:
        """Get usage metrics for a developer."""

        time_range = filters.get('time_range', '30d')
        cutoff = self._parse_time_range(time_range)

        usage_data = self._usage_metrics.get(developer_id, [])
        recent_usage = [
            usage for usage in usage_data
            if datetime.fromisoformat(usage['timestamp']) >= cutoff
        ]

        # Calculate metrics
        total_requests = len(recent_usage)
        unique_apps = len(set(usage['app_id'] for usage in recent_usage))

        # Group by day
        daily_usage = {}
        for usage in recent_usage:
            date = usage['timestamp'][:10]  # Extract date part
            daily_usage[date] = daily_usage.get(date, 0) + 1

        return {
            'developer_id': developer_id,
            'time_range': time_range,
            'total_requests': total_requests,
            'unique_applications': unique_apps,
            'daily_usage': daily_usage,
            'usage_details': recent_usage
        }

    async def create_documentation(self, **kwargs) -> dict[str, Any]:
        """Create API documentation."""

        doc_id = str(uuid4())

        documentation = {
            'doc_id': doc_id,
            'title': kwargs['title'],
            'content': kwargs.get('content', ''),
            'api_spec': kwargs.get('api_spec'),
            'category': kwargs.get('category', 'general'),
            'tags': kwargs.get('tags', []),
            'version': kwargs.get('version', '1.0.0'),
            'status': kwargs.get('status', 'published'),
            'author': kwargs.get('author', 'DotMac Team'),
            'created_at': utc_now().isoformat(),
            'updated_at': utc_now().isoformat(),
        }

        self._documentation[doc_id] = documentation

        return documentation

    async def generate_code_samples(self, api_spec: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Generate code samples for API endpoints."""

        languages = kwargs.get('languages', ['python', 'javascript', 'curl'])
        samples = {}

        # Extract endpoints from OpenAPI spec
        paths = api_spec.get('paths', {})

        for path, methods in paths.items():
            for method, spec in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    endpoint_key = f"{method.upper()} {path}"
                    samples[endpoint_key] = {}

                    for language in languages:
                        samples[endpoint_key][language] = self._generate_code_sample(
                            method, path, spec, language
                        )

        return samples

    def _generate_code_sample(self, method: str, path: str, spec: dict[str, Any], language: str) -> str:
        """Generate code sample for specific language."""

        if language == 'curl':
            return f"""curl -X {method.upper()} \\
  https://api.example.com{path} \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json\""""

        elif language == 'python':
            return f"""import requests

response = requests.{method.lower()}(
    "https://api.example.com{path}",
    headers={{"X-API-Key": "YOUR_API_KEY"}}
)
print(response.json())"""

        elif language == 'javascript':
            return f"""fetch('https://api.example.com{path}', {{
  method: '{method.upper()}',
  headers: {{
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  }}
}})
.then(response => response.json())
.then(data => console.log(data));"""

        return f"# {language} sample not available"

    async def _generate_default_documentation(self):
        """Generate default API documentation."""

        default_docs = [
            {
                'title': 'Getting Started',
                'content': 'Welcome to the DotMac API documentation.',
                'category': 'quickstart'
            },
            {
                'title': 'Authentication',
                'content': 'Learn how to authenticate with the API using API keys.',
                'category': 'auth'
            },
            {
                'title': 'Rate Limiting',
                'content': 'Understand API rate limits and how to handle them.',
                'category': 'limits'
            }
        ]

        for doc in default_docs:
            await self.create_documentation(**doc)

    def _get_tier_rate_limits(self, tier: str) -> dict[str, int]:
        """Get rate limits for developer tier."""

        limits = {
            'starter': {
                'requests_per_minute': 100,
                'requests_per_hour': 1000,
                'requests_per_day': 10000
            },
            'pro': {
                'requests_per_minute': 1000,
                'requests_per_hour': 10000,
                'requests_per_day': 100000
            },
            'enterprise': {
                'requests_per_minute': 10000,
                'requests_per_hour': 100000,
                'requests_per_day': 1000000
            }
        }

        return limits.get(tier, limits['starter'])

    async def _record_api_usage(self, api_key: str, usage_data: dict[str, Any]):
        """Record API usage for analytics."""

        developer_id = usage_data['developer_id']

        if developer_id not in self._usage_metrics:
            self._usage_metrics[developer_id] = []

        self._usage_metrics[developer_id].append(usage_data)

    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string to datetime."""

        now = utc_now()

        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            return now - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            return now - timedelta(days=days)
        elif time_range.endswith('w'):
            weeks = int(time_range[:-1])
            return now - timedelta(weeks=weeks)
        else:
            return now - timedelta(days=30)  # Default to 30 days


class DeveloperPortalSDK:
    """SDK for developer portal management."""

    def __init__(self, config: DevToolsConfig | None = None):
        self.config = config or DevToolsConfig()
        self._service = DeveloperPortalService(self.config)

    async def initialize_portal(
        self,
        domain: str,
        title: str = "Developer Portal",
        **kwargs
    ) -> dict[str, Any]:
        """Initialize developer portal."""
        return await self._service.initialize_portal(
            domain=domain,
            title=title,
            **kwargs
        )

    async def register_developer(
        self,
        email: str,
        name: str = "",
        **kwargs
    ) -> dict[str, Any]:
        """Register a new developer."""
        return await self._service.register_developer(
            email=email,
            name=name,
            **kwargs
        )

    async def approve_developer(self, developer_id: str) -> dict[str, Any]:
        """Approve a developer registration."""
        return await self._service.approve_developer(developer_id)

    async def create_application(
        self,
        developer_id: str,
        name: str,
        **kwargs
    ) -> dict[str, Any]:
        """Create a new application."""
        return await self._service.create_application(
            developer_id=developer_id,
            name=name,
            **kwargs
        )

    async def generate_api_key(self, app_id: str) -> dict[str, Any]:
        """Generate API key for an application."""
        return await self._service.generate_api_key(app_id)

    async def validate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Validate an API key."""
        return await self._service.validate_api_key(api_key)

    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        return await self._service.revoke_api_key(api_key)

    async def get_usage_metrics(
        self,
        developer_id: str,
        time_range: str = "30d"
    ) -> dict[str, Any]:
        """Get usage metrics for a developer."""
        return await self._service.get_usage_metrics(
            developer_id,
            time_range=time_range
        )

    async def create_documentation(
        self,
        title: str,
        content: str = "",
        **kwargs
    ) -> dict[str, Any]:
        """Create API documentation."""
        return await self._service.create_documentation(
            title=title,
            content=content,
            **kwargs
        )

    async def generate_code_samples(
        self,
        api_spec: dict[str, Any],
        languages: list[str] = None
    ) -> dict[str, Any]:
        """Generate code samples for API endpoints."""
        return await self._service.generate_code_samples(
            api_spec,
            languages=languages or ['python', 'javascript', 'curl']
        )
