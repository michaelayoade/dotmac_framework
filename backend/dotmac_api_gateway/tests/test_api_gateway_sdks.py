"""
Comprehensive tests for DotMac API Gateway SDKs.

Tests gateway management, authentication proxy, rate limiting, API versioning,
and gateway analytics functionality.
"""

from datetime import datetime, timedelta
from dotmac_api_gateway.core.datetime_utils import utc_now_iso, utc_now, expires_in_days, expires_in_hours, time_ago_minutes, time_ago_hours

import pytest

# Import core exceptions
from dotmac_api_gateway.sdks.api_documentation import APIDocumentationSDK
from dotmac_api_gateway.sdks.api_versioning import APIVersioningSDK
from dotmac_api_gateway.sdks.authentication_proxy import AuthenticationProxySDK

# Import API Gateway SDKs
from dotmac_api_gateway.sdks.gateway import GatewaySDK
from dotmac_api_gateway.sdks.gateway_analytics import GatewayAnalyticsSDK
from dotmac_api_gateway.sdks.rate_limiting import RateLimitingSDK


class TestGatewaySDK:
    """Test core gateway management functionality."""

    @pytest.fixture
    def gateway_sdk(self):
        """Create gateway SDK instance."""
        return GatewaySDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_gateway(self, gateway_sdk):
        """Test gateway creation."""
        gateway = await gateway_sdk.create_gateway(
            name="Test API Gateway",
            description="Gateway for testing APIs",
            domains=["api.example.com", "test-api.example.com"],
            load_balancer_algorithm="round_robin",
            ssl_enabled=True,
            health_check_enabled=True,
            health_check_path="/health"
        )

        assert gateway["name"] == "Test API Gateway"
        assert gateway["description"] == "Gateway for testing APIs"
        assert "api.example.com" in gateway["domains"]
        assert gateway["load_balancer_algorithm"] == "round_robin"
        assert gateway["ssl_enabled"] is True
        assert gateway["health_check_enabled"] is True
        assert gateway["status"] == "active"
        assert "gateway_id" in gateway

    @pytest.mark.asyncio
    async def test_create_and_manage_routes(self, gateway_sdk):
        """Test route creation and management."""
        # Create gateway first
        gateway = await gateway_sdk.create_gateway(
            name="Route Test Gateway",
            description="Gateway for route testing"
        )
        gateway_id = gateway["gateway_id"]

        # Create route
        route = await gateway_sdk.create_route(
            gateway_id=gateway_id,
            path="/api/v1/users",
            upstream_service="user-service",
            upstream_url="http://user-service:8080",
            methods=["GET", "POST"],
            timeout=30,
            retries=3,
            cache_enabled=True,
            cache_ttl=300
        )

        assert route["gateway_id"] == gateway_id
        assert route["path"] == "/api/v1/users"
        assert route["upstream_service"] == "user-service"
        assert route["upstream_url"] == "http://user-service:8080"
        assert "GET" in route["methods"]
        assert "POST" in route["methods"]
        assert route["timeout"] == 30
        assert route["cache_enabled"] is True

        # List routes
        routes = await gateway_sdk.list_routes(gateway_id)
        assert len(routes) == 1
        assert routes[0]["route_id"] == route["route_id"]

        # Update route
        updated_route = await gateway_sdk.update_route(
            route["route_id"],
            timeout=60,
            cache_ttl=600
        )

        assert updated_route["timeout"] == 60
        assert updated_route["cache_ttl"] == 600

        # Delete route
        delete_result = await gateway_sdk.delete_route(route["route_id"])
        assert delete_result is True

        # Verify route is deleted
        remaining_routes = await gateway_sdk.list_routes(gateway_id)
        assert len(remaining_routes) == 0

    @pytest.mark.asyncio
    async def test_load_balancer_configuration(self, gateway_sdk):
        """Test load balancer configuration."""
        # Create gateway
        gateway = await gateway_sdk.create_gateway(
            name="Load Balancer Test Gateway"
        )
        gateway_id = gateway["gateway_id"]

        # Configure load balancer
        lb_config = await gateway_sdk.configure_load_balancer(
            gateway_id=gateway_id,
            algorithm="weighted_round_robin",
            health_check_path="/health",
            health_check_interval=20,
            health_check_timeout=5,
            connection_timeout=5000,
            max_connections_per_upstream=200,
            sticky_sessions=True,
            session_cookie_name="GATEWAY_SESSION"
        )

        assert lb_config["gateway_id"] == gateway_id
        assert lb_config["algorithm"] == "weighted_round_robin"
        assert lb_config["health_check_interval"] == 20
        assert lb_config["sticky_sessions"] is True
        assert lb_config["session_cookie_name"] == "GATEWAY_SESSION"

        # Verify gateway was updated
        updated_gateway = await gateway_sdk.get_gateway(gateway_id)
        assert updated_gateway["load_balancer_algorithm"] == "weighted_round_robin"

    @pytest.mark.asyncio
    async def test_cors_configuration(self, gateway_sdk):
        """Test CORS configuration."""
        # Create gateway
        gateway = await gateway_sdk.create_gateway(
            name="CORS Test Gateway"
        )
        gateway_id = gateway["gateway_id"]

        # Configure CORS
        cors_result = await gateway_sdk.configure_cors(
            gateway_id=gateway_id,
            allowed_origins=["https://app.example.com", "https://admin.example.com"],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            allowed_headers=["Content-Type", "Authorization", "X-API-Key"],
            max_age=86400
        )

        assert cors_result is True

        # Verify CORS configuration
        updated_gateway = await gateway_sdk.get_gateway(gateway_id)
        assert updated_gateway["cors_enabled"] is True
        assert "https://app.example.com" in updated_gateway["cors_origins"]
        assert "PUT" in updated_gateway["cors_methods"]
        assert updated_gateway["cors_max_age"] == 86400

    @pytest.mark.asyncio
    async def test_request_response_transformations(self, gateway_sdk):
        """Test request and response transformations."""
        # Create gateway and route
        gateway = await gateway_sdk.create_gateway(name="Transform Test Gateway")
        gateway_id = gateway["gateway_id"]

        route = await gateway_sdk.create_route(
            gateway_id=gateway_id,
            path="/api/v1/transform",
            upstream_service="transform-service",
            upstream_url="http://transform-service:8080"
        )
        route_id = route["route_id"]

        # Add request transformation
        req_transform_result = await gateway_sdk.add_request_transformation(
            route_id=route_id,
            transformation_type="header_manipulation",
            config={
                "add_headers": {
                    "X-Gateway-Timestamp": "{{timestamp}}",
                    "X-Request-ID": "{{request_id}}"
                },
                "remove_headers": ["X-Internal-Token"]
            }
        )

        assert req_transform_result is True

        # Add response transformation
        resp_transform_result = await gateway_sdk.add_response_transformation(
            route_id=route_id,
            transformation_type="json_manipulation",
            config={
                "remove_fields": ["internal_id", "debug_info"],
                "add_fields": {
                    "api_version": "v1",
                    "response_time": "{{response_time}}"
                }
            }
        )

        assert resp_transform_result is True

    @pytest.mark.asyncio
    async def test_upstream_service_registration(self, gateway_sdk):
        """Test upstream service registration."""
        # Register upstream service
        service = await gateway_sdk.register_upstream_service(
            name="User Management Service",
            url="http://user-service:8080",
            weight=100,
            max_connections=50,
            health_check_url="http://user-service:8080/health"
        )

        assert service["name"] == "User Management Service"
        assert service["url"] == "http://user-service:8080"
        assert service["weight"] == 100
        assert service["max_connections"] == 50
        assert service["status"] == "healthy"
        assert "service_id" in service


class TestAuthenticationProxySDK:
    """Test authentication and authorization functionality."""

    @pytest.fixture
    def auth_sdk(self):
        """Create authentication proxy SDK instance."""
        return AuthenticationProxySDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_jwt_auth_policy(self, auth_sdk):
        """Test JWT authentication policy creation."""
        policy = await auth_sdk.create_auth_policy(
            name="JWT Auth Policy",
            auth_type="jwt",
            jwt_secret_key="test-secret-key-123",
            jwt_algorithm="HS256",
            jwt_issuer="dotmac-gateway",
            jwt_audience=["api", "admin"],
            required_scopes=["read", "write"],
            required_roles=["user"],
            token_ttl=3600
        )

        assert policy["name"] == "JWT Auth Policy"
        assert policy["auth_type"] == "jwt"
        assert policy["jwt_secret_key"] == "test-secret-key-123"
        assert policy["jwt_algorithm"] == "HS256"
        assert policy["jwt_issuer"] == "dotmac-gateway"
        assert "read" in policy["required_scopes"]
        assert "user" in policy["required_roles"]
        assert policy["token_ttl"] == 3600

    @pytest.mark.asyncio
    async def test_create_api_key_auth_policy(self, auth_sdk):
        """Test API key authentication policy creation."""
        policy = await auth_sdk.create_auth_policy(
            name="API Key Auth Policy",
            auth_type="api_key",
            api_key_header="X-API-Key",
            enable_bearer_token=True,
            enable_query_param=False,
            required_scopes=["api_access"]
        )

        assert policy["name"] == "API Key Auth Policy"
        assert policy["auth_type"] == "api_key"
        assert policy["api_key_header"] == "X-API-Key"
        assert policy["enable_bearer_token"] is True
        assert policy["enable_query_param"] is False
        assert "api_access" in policy["required_scopes"]

    @pytest.mark.asyncio
    async def test_jwt_provider_and_token_management(self, auth_sdk):
        """Test JWT provider creation and token management."""
        # Create JWT provider
        provider = await auth_sdk.create_jwt_auth_provider(
            name="Main JWT Provider",
            secret_key="jwt-secret-123",
            algorithm="HS256",
            issuer="dotmac-api-gateway",
            audience=["api"],
            expiration_seconds=3600
        )

        assert provider["name"] == "Main JWT Provider"
        assert provider["type"] == "jwt"
        assert provider["secret_key"] == "jwt-secret-123"
        assert provider["algorithm"] == "HS256"
        assert provider["expiration_seconds"] == 3600

        # Generate JWT token
        token_data = await auth_sdk.generate_jwt_token(
            user_id="user123",
            scopes=["read", "write"],
            roles=["user", "admin"],
            secret_key="jwt-secret-123",
            expires_in=3600
        )

        assert token_data["payload"]["sub"] == "user123"
        assert "read" in token_data["payload"]["scopes"]
        assert "admin" in token_data["payload"]["roles"]
        assert "token" in token_data

        # Validate JWT token
        validated_payload = await auth_sdk.validate_jwt_token(
            token_data["token"],
            "jwt-secret-123",
            "HS256"
        )

        assert validated_payload["sub"] == "user123"
        assert "read" in validated_payload["scopes"]

    @pytest.mark.asyncio
    async def test_api_key_management(self, auth_sdk):
        """Test API key generation and management."""
        # Create API key provider
        provider = await auth_sdk.create_api_key_auth_provider(
            name="API Key Provider",
            header_name="X-API-Key",
            allow_query_param=True,
            query_param_name="apikey"
        )

        assert provider["name"] == "API Key Provider"
        assert provider["type"] == "api_key"
        assert provider["header_name"] == "X-API-Key"
        assert provider["allow_query_param"] is True

        # Generate API key
        api_key_data = await auth_sdk.generate_api_key(
            name="Test API Key",
            user_id="user123",
            scopes=["read", "write"],
            roles=["api_user"],
            expires_at=(utc_now() + timedelta(days=30)).isoformat()
        )

        assert api_key_data["name"] == "Test API Key"
        assert api_key_data["user_id"] == "user123"
        assert "read" in api_key_data["scopes"]
        assert "api_user" in api_key_data["roles"]
        assert api_key_data["status"] == "active"
        assert api_key_data["api_key"].startswith("ak_")

        # Validate API key
        validated_key = await auth_sdk.validate_api_key(api_key_data["api_key"])

        assert validated_key is not None
        assert validated_key["user_id"] == "user123"
        assert validated_key["usage_count"] == 1

        # Revoke API key
        revoke_result = await auth_sdk.revoke_api_key(api_key_data["api_key"])
        assert revoke_result is True

        # Verify key is revoked
        revoked_key = await auth_sdk.validate_api_key(api_key_data["api_key"])
        assert revoked_key is None

    @pytest.mark.asyncio
    async def test_oauth2_provider_creation(self, auth_sdk):
        """Test OAuth2 provider creation."""
        provider = await auth_sdk.create_oauth2_auth_provider(
            name="Google OAuth2",
            client_id="google_client_id",
            client_secret="google_client_secret",
            authorization_url="https://accounts.google.com/oauth/authorize",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scope="openid email profile",
            redirect_uri="https://api.example.com/auth/callback"
        )

        assert provider["name"] == "Google OAuth2"
        assert provider["type"] == "oauth2"
        assert provider["client_id"] == "google_client_id"
        assert provider["authorization_url"] == "https://accounts.google.com/oauth/authorize"
        assert provider["scope"] == "openid email profile"

    @pytest.mark.asyncio
    async def test_request_authentication(self, auth_sdk):
        """Test request authentication with different methods."""
        # Create JWT policy
        jwt_policy = await auth_sdk.create_auth_policy(
            name="JWT Test Policy",
            auth_type="jwt",
            jwt_secret_key="test-secret",
            required_scopes=["api_access"]
        )

        # Generate JWT token
        token_data = await auth_sdk.generate_jwt_token(
            user_id="testuser",
            scopes=["api_access", "read"],
            secret_key="test-secret"
        )

        # Test JWT authentication
        jwt_headers = {"Authorization": f"Bearer {token_data['token']}"}
        jwt_auth_result = await auth_sdk.authenticate_request(
            headers=jwt_headers,
            query_params={},
            policy_id=jwt_policy["policy_id"]
        )

        assert jwt_auth_result["auth_type"] == "jwt"
        assert jwt_auth_result["user_id"] == "testuser"
        assert "api_access" in jwt_auth_result["scopes"]

        # Create API key policy
        api_key_policy = await auth_sdk.create_auth_policy(
            name="API Key Test Policy",
            auth_type="api_key",
            api_key_header="X-API-Key",
            required_scopes=["api_access"]
        )

        # Generate API key
        api_key_data = await auth_sdk.generate_api_key(
            name="Test Key",
            scopes=["api_access", "read"]
        )

        # Test API key authentication
        api_key_headers = {"X-API-Key": api_key_data["api_key"]}
        api_key_auth_result = await auth_sdk.authenticate_request(
            headers=api_key_headers,
            query_params={},
            policy_id=api_key_policy["policy_id"]
        )

        assert api_key_auth_result["auth_type"] == "api_key"
        assert "api_access" in api_key_auth_result["scopes"]


class TestRateLimitingSDK:
    """Test rate limiting functionality."""

    @pytest.fixture
    def rate_limit_sdk(self):
        """Create rate limiting SDK instance."""
        return RateLimitingSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_rate_limit_policy(self, rate_limit_sdk):
        """Test rate limit policy creation."""
        policy = await rate_limit_sdk.create_rate_limit_policy(
            name="API Rate Limit",
            limit=100,
            window_seconds=60,
            scope="api_key",
            burst_limit=120,
            quota_period="daily",
            quota_limit=10000
        )

        assert policy["name"] == "API Rate Limit"
        assert policy["limit"] == 100
        assert policy["window_seconds"] == 60
        assert policy["scope"] == "api_key"
        assert policy["burst_limit"] == 120
        assert policy["quota_period"] == "daily"
        assert policy["quota_limit"] == 10000

    @pytest.mark.asyncio
    async def test_tiered_rate_limiting(self, rate_limit_sdk):
        """Test tiered rate limiting based on user tiers."""
        # Create tiered rate limit policy
        policy = await rate_limit_sdk.create_tiered_rate_limit_policy(
            name="Tiered API Limits",
            tiers={
                "free": {"limit": 100, "window_seconds": 3600},
                "premium": {"limit": 1000, "window_seconds": 3600},
                "enterprise": {"limit": 10000, "window_seconds": 3600}
            },
            default_tier="free"
        )

        assert policy["name"] == "Tiered API Limits"
        assert policy["tiers"]["free"]["limit"] == 100
        assert policy["tiers"]["premium"]["limit"] == 1000
        assert policy["tiers"]["enterprise"]["limit"] == 10000
        assert policy["default_tier"] == "free"

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, rate_limit_sdk):
        """Test rate limit enforcement."""
        # Create rate limit policy
        policy = await rate_limit_sdk.create_rate_limit_policy(
            name="Test Rate Limit",
            limit=5,
            window_seconds=60,
            scope="ip"
        )
        policy_id = policy["policy_id"]

        client_ip = "192.168.1.100"

        # Test within limit
        for i in range(5):
            result = await rate_limit_sdk.check_rate_limit(
                policy_id=policy_id,
                identifier=client_ip,
                cost=1
            )

            assert result["allowed"] is True
            assert result["remaining"] == 4 - i
            assert result["limit"] == 5

        # Test exceeding limit
        exceeded_result = await rate_limit_sdk.check_rate_limit(
            policy_id=policy_id,
            identifier=client_ip,
            cost=1
        )

        assert exceeded_result["allowed"] is False
        assert exceeded_result["remaining"] == 0
        assert "retry_after" in exceeded_result

    @pytest.mark.asyncio
    async def test_distributed_rate_limiting(self, rate_limit_sdk):
        """Test distributed rate limiting across multiple instances."""
        # Create distributed rate limit policy
        policy = await rate_limit_sdk.create_distributed_rate_limit_policy(
            name="Distributed Rate Limit",
            limit=1000,
            window_seconds=3600,
            scope="user_id",
            redis_config={
                "host": "redis-cluster",
                "port": 6379,
                "db": 0
            },
            sync_interval=5
        )

        assert policy["name"] == "Distributed Rate Limit"
        assert policy["distributed"] is True
        assert policy["redis_config"]["host"] == "redis-cluster"
        assert policy["sync_interval"] == 5

    @pytest.mark.asyncio
    async def test_rate_limit_bypass_rules(self, rate_limit_sdk):
        """Test rate limit bypass rules."""
        # Create rate limit policy with bypass rules
        policy = await rate_limit_sdk.create_rate_limit_policy(
            name="Rate Limit with Bypass",
            limit=100,
            window_seconds=3600,
            scope="api_key",
            bypass_rules=[
                {
                    "type": "ip_whitelist",
                    "values": ["10.0.0.0/8", "192.168.1.100"]
                },
                {
                    "type": "api_key_whitelist",
                    "values": ["admin-key-123", "monitoring-key-456"]
                }
            ]
        )

        assert len(policy["bypass_rules"]) == 2
        assert policy["bypass_rules"][0]["type"] == "ip_whitelist"
        assert "10.0.0.0/8" in policy["bypass_rules"][0]["values"]

        # Test bypass for whitelisted IP
        bypass_result = await rate_limit_sdk.check_rate_limit_with_bypass(
            policy_id=policy["policy_id"],
            identifier="test-key",
            client_ip="192.168.1.100"
        )

        assert bypass_result["allowed"] is True
        assert bypass_result["bypassed"] is True
        assert bypass_result["bypass_reason"] == "ip_whitelist"


class TestAPIVersioningSDK:
    """Test API versioning functionality."""

    @pytest.fixture
    def versioning_sdk(self):
        """Create API versioning SDK instance."""
        return APIVersioningSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_create_api_version(self, versioning_sdk):
        """Test API version creation."""
        version = await versioning_sdk.create_api_version(
            api_name="User Management API",
            version="v2.1.0",
            description="Enhanced user management with new features",
            status="stable",
            upstream_url="http://user-service-v2:8080",
            deprecation_date=None,
            sunset_date=None
        )

        assert version["api_name"] == "User Management API"
        assert version["version"] == "v2.1.0"
        assert version["status"] == "stable"
        assert version["upstream_url"] == "http://user-service-v2:8080"
        assert "version_id" in version

    @pytest.mark.asyncio
    async def test_version_routing_strategies(self, versioning_sdk):
        """Test different version routing strategies."""
        api_name = "Test API"

        # Create multiple versions
        v1 = await versioning_sdk.create_api_version(
            api_name=api_name,
            version="v1.0.0",
            upstream_url="http://api-v1:8080"
        )

        v2 = await versioning_sdk.create_api_version(
            api_name=api_name,
            version="v2.0.0",
            upstream_url="http://api-v2:8080"
        )

        # Test header-based routing
        header_routing = await versioning_sdk.configure_version_routing(
            api_name=api_name,
            strategy="header",
            config={
                "header_name": "API-Version",
                "default_version": "v2.0.0"
            }
        )

        assert header_routing["strategy"] == "header"
        assert header_routing["config"]["header_name"] == "API-Version"
        assert header_routing["config"]["default_version"] == "v2.0.0"

        # Test path-based routing
        path_routing = await versioning_sdk.configure_version_routing(
            api_name=api_name,
            strategy="path",
            config={
                "path_prefix": "/v{version}",
                "version_pattern": r"v(\d+)\.(\d+)\.(\d+)"
            }
        )

        assert path_routing["strategy"] == "path"
        assert path_routing["config"]["path_prefix"] == "/v{version}"

        # Test query parameter routing
        query_routing = await versioning_sdk.configure_version_routing(
            api_name=api_name,
            strategy="query_param",
            config={
                "param_name": "version",
                "default_version": "v1.0.0"
            }
        )

        assert query_routing["strategy"] == "query_param"
        assert query_routing["config"]["param_name"] == "version"

    @pytest.mark.asyncio
    async def test_api_deprecation_and_sunset(self, versioning_sdk):
        """Test API version deprecation and sunset."""
        # Create API version
        version = await versioning_sdk.create_api_version(
            api_name="Legacy API",
            version="v1.0.0",
            upstream_url="http://legacy-api:8080"
        )
        version_id = version["version_id"]

        # Deprecate version
        deprecation_result = await versioning_sdk.deprecate_version(
            version_id=version_id,
            deprecation_date=(utc_now() + timedelta(days=30)).isoformat(),
            sunset_date=(utc_now() + timedelta(days=90)).isoformat(),
            migration_guide_url="https://docs.example.com/migration-v2",
            replacement_version="v2.0.0"
        )

        assert deprecation_result["status"] == "deprecated"
        assert deprecation_result["replacement_version"] == "v2.0.0"
        assert deprecation_result["migration_guide_url"] == "https://docs.example.com/migration-v2"

        # Get version status
        version_status = await versioning_sdk.get_version_status(version_id)

        assert version_status["status"] == "deprecated"
        assert "sunset_date" in version_status
        assert "days_until_sunset" in version_status

    @pytest.mark.asyncio
    async def test_version_compatibility_matrix(self, versioning_sdk):
        """Test API version compatibility matrix."""
        api_name = "Compatibility Test API"

        # Create multiple versions
        versions = []
        for version in ["v1.0.0", "v1.1.0", "v2.0.0", "v2.1.0"]:
            v = await versioning_sdk.create_api_version(
                api_name=api_name,
                version=version,
                upstream_url=f"http://api-{version.replace('.', '-')}:8080"
            )
            versions.append(v)

        # Define compatibility matrix
        compatibility_matrix = await versioning_sdk.define_compatibility_matrix(
            api_name=api_name,
            compatibility_rules=[
                {
                    "from_version": "v1.0.0",
                    "to_versions": ["v1.1.0"],
                    "compatibility_level": "backward_compatible"
                },
                {
                    "from_version": "v1.1.0",
                    "to_versions": ["v2.0.0"],
                    "compatibility_level": "breaking_changes"
                },
                {
                    "from_version": "v2.0.0",
                    "to_versions": ["v2.1.0"],
                    "compatibility_level": "backward_compatible"
                }
            ]
        )

        assert len(compatibility_matrix["compatibility_rules"]) == 3
        assert compatibility_matrix["compatibility_rules"][0]["compatibility_level"] == "backward_compatible"
        assert compatibility_matrix["compatibility_rules"][1]["compatibility_level"] == "breaking_changes"


class TestGatewayAnalyticsSDK:
    """Test gateway analytics and monitoring functionality."""

    @pytest.fixture
    def analytics_sdk(self):
        """Create gateway analytics SDK instance."""
        return GatewayAnalyticsSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_record_api_metrics(self, analytics_sdk):
        """Test API metrics recording."""
        # Record API request metrics
        metrics = await analytics_sdk.record_api_request(
            gateway_id="gw-123",
            route_id="route-456",
            method="GET",
            path="/api/v1/users",
            status_code=200,
            response_time_ms=150,
            request_size_bytes=1024,
            response_size_bytes=4096,
            user_id="user123",
            api_key_id="key456",
            client_ip="192.168.1.100",
            user_agent="Mozilla/5.0 (Test)",
            timestamp=utc_now()
        )

        assert metrics["gateway_id"] == "gw-123"
        assert metrics["route_id"] == "route-456"
        assert metrics["method"] == "GET"
        assert metrics["status_code"] == 200
        assert metrics["response_time_ms"] == 150
        assert "request_id" in metrics

    @pytest.mark.asyncio
    async def test_generate_analytics_report(self, analytics_sdk):
        """Test analytics report generation."""
        gateway_id = "gw-test-123"

        # Generate sample metrics data
        for i in range(100):
            await analytics_sdk.record_api_request(
                gateway_id=gateway_id,
                route_id=f"route-{i % 5}",
                method="GET",
                path=f"/api/v1/endpoint{i % 3}",
                status_code=200 if i % 10 != 0 else 500,
                response_time_ms=100 + (i % 50),
                user_id=f"user{i % 10}",
                timestamp=utc_now() - timedelta(minutes=i)
            )

        # Generate analytics report
        report = await analytics_sdk.generate_analytics_report(
            gateway_id=gateway_id,
            start_time=utc_now() - timedelta(hours=2),
            end_time=utc_now(),
            metrics=["request_count", "error_rate", "avg_response_time", "top_endpoints"]
        )

        assert report["gateway_id"] == gateway_id
        assert "request_count" in report["metrics"]
        assert "error_rate" in report["metrics"]
        assert "avg_response_time" in report["metrics"]
        assert "top_endpoints" in report["metrics"]
        assert report["metrics"]["request_count"] >= 100
        assert 0 <= report["metrics"]["error_rate"] <= 1

    @pytest.mark.asyncio
    async def test_real_time_monitoring(self, analytics_sdk):
        """Test real-time monitoring capabilities."""
        gateway_id = "gw-monitor-123"

        # Start real-time monitoring
        monitoring_session = await analytics_sdk.start_real_time_monitoring(
            gateway_id=gateway_id,
            metrics=["request_rate", "error_rate", "avg_response_time"],
            aggregation_window_seconds=10,
            alert_thresholds={
                "error_rate": 0.05,  # 5% error rate
                "avg_response_time": 1000  # 1 second
            }
        )

        assert monitoring_session["gateway_id"] == gateway_id
        assert monitoring_session["status"] == "active"
        assert "request_rate" in monitoring_session["metrics"]
        assert monitoring_session["aggregation_window_seconds"] == 10

        # Simulate real-time data
        current_metrics = await analytics_sdk.get_current_metrics(
            gateway_id=gateway_id,
            window_seconds=60
        )

        assert current_metrics["gateway_id"] == gateway_id
        assert "timestamp" in current_metrics
        assert "metrics" in current_metrics

    @pytest.mark.asyncio
    async def test_traffic_analysis(self, analytics_sdk):
        """Test traffic pattern analysis."""
        gateway_id = "gw-traffic-123"

        # Analyze traffic patterns
        traffic_analysis = await analytics_sdk.analyze_traffic_patterns(
            gateway_id=gateway_id,
            analysis_period_hours=24,
            pattern_types=["peak_hours", "endpoint_popularity", "user_behavior", "geographic_distribution"]
        )

        assert traffic_analysis["gateway_id"] == gateway_id
        assert "peak_hours" in traffic_analysis["patterns"]
        assert "endpoint_popularity" in traffic_analysis["patterns"]
        assert "user_behavior" in traffic_analysis["patterns"]

        # Get traffic anomalies
        anomalies = await analytics_sdk.detect_traffic_anomalies(
            gateway_id=gateway_id,
            detection_window_hours=1,
            anomaly_types=["request_spike", "error_burst", "slow_responses"]
        )

        assert anomalies["gateway_id"] == gateway_id
        assert "anomalies" in anomalies
        assert "detection_timestamp" in anomalies


class TestAPIDocumentationSDK:
    """Test API documentation functionality."""

    @pytest.fixture
    def docs_sdk(self):
        """Create API documentation SDK instance."""
        return APIDocumentationSDK(tenant_id="test-tenant-123")

    @pytest.mark.asyncio
    async def test_generate_openapi_spec(self, docs_sdk):
        """Test OpenAPI specification generation."""
        # Define API specification
        api_spec = await docs_sdk.generate_openapi_spec(
            api_name="User Management API",
            version="v1.0.0",
            base_url="https://api.example.com",
            description="API for managing user accounts and profiles",
            contact={
                "name": "API Support",
                "email": "support@example.com",
                "url": "https://support.example.com"
            },
            license={
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        )

        assert api_spec["openapi"] == "3.0.3"
        assert api_spec["info"]["title"] == "User Management API"
        assert api_spec["info"]["version"] == "v1.0.0"
        assert api_spec["servers"][0]["url"] == "https://api.example.com"
        assert api_spec["info"]["contact"]["email"] == "support@example.com"

    @pytest.mark.asyncio
    async def test_add_api_endpoints_documentation(self, docs_sdk):
        """Test adding endpoint documentation."""
        api_id = "api-123"

        # Add endpoint documentation
        endpoint_doc = await docs_sdk.add_endpoint_documentation(
            api_id=api_id,
            path="/api/v1/users/{userId}",
            method="GET",
            summary="Get user by ID",
            description="Retrieve detailed information about a specific user",
            parameters=[
                {
                    "name": "userId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                    "description": "Unique identifier for the user"
                }
            ],
            responses={
                "200": {
                    "description": "User details retrieved successfully",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "email": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "404": {
                    "description": "User not found"
                }
            },
            tags=["Users"],
            security=[{"ApiKeyAuth": []}]
        )

        assert endpoint_doc["path"] == "/api/v1/users/{userId}"
        assert endpoint_doc["method"] == "GET"
        assert endpoint_doc["summary"] == "Get user by ID"
        assert len(endpoint_doc["parameters"]) == 1
        assert "200" in endpoint_doc["responses"]
        assert "Users" in endpoint_doc["tags"]

    @pytest.mark.asyncio
    async def test_generate_api_documentation_portal(self, docs_sdk):
        """Test API documentation portal generation."""
        # Generate documentation portal
        portal = await docs_sdk.generate_documentation_portal(
            api_specs=["api-123", "api-456"],
            portal_config={
                "title": "DotMac API Documentation",
                "description": "Comprehensive API documentation for DotMac services",
                "theme": "modern",
                "enable_try_it_out": True,
                "enable_code_samples": True,
                "supported_languages": ["curl", "javascript", "python", "go"],
                "custom_css": "/assets/custom.css",
                "logo_url": "/assets/logo.png"
            }
        )

        assert portal["title"] == "DotMac API Documentation"
        assert portal["config"]["enable_try_it_out"] is True
        assert "javascript" in portal["config"]["supported_languages"]
        assert portal["status"] == "generated"
        assert "portal_url" in portal


# Integration tests
class TestAPIGatewayIntegration:
    """Test integration between API Gateway SDKs."""

    @pytest.mark.asyncio
    async def test_gateway_with_authentication_integration(self):
        """Test gateway routing with authentication."""
        gateway_sdk = GatewaySDK(tenant_id="test-tenant")
        auth_sdk = AuthenticationProxySDK(tenant_id="test-tenant")

        # Create gateway
        gateway = await gateway_sdk.create_gateway(
            name="Authenticated API Gateway",
            description="Gateway with authentication"
        )
        gateway_id = gateway["gateway_id"]

        # Create authentication policy
        auth_policy = await auth_sdk.create_auth_policy(
            name="JWT Auth Policy",
            auth_type="jwt",
            jwt_secret_key="integration-test-secret",
            required_scopes=["api_access"]
        )

        # Create route with authentication
        route = await gateway_sdk.create_route(
            gateway_id=gateway_id,
            path="/api/v1/protected",
            upstream_service="protected-service",
            upstream_url="http://protected-service:8080",
            auth_policy_id=auth_policy["policy_id"]
        )

        assert route["auth_policy_id"] == auth_policy["policy_id"]

        # Apply authentication policy to route
        policy_applied = await gateway_sdk.apply_auth_policy(
            route["route_id"],
            auth_policy["policy_id"]
        )

        assert policy_applied is True

    @pytest.mark.asyncio
    async def test_gateway_with_rate_limiting_integration(self):
        """Test gateway routing with rate limiting."""
        gateway_sdk = GatewaySDK(tenant_id="test-tenant")
        rate_limit_sdk = RateLimitingSDK(tenant_id="test-tenant")

        # Create gateway and route
        gateway = await gateway_sdk.create_gateway(name="Rate Limited Gateway")
        route = await gateway_sdk.create_route(
            gateway_id=gateway["gateway_id"],
            path="/api/v1/limited",
            upstream_service="limited-service",
            upstream_url="http://limited-service:8080"
        )

        # Create rate limit policy
        rate_policy = await rate_limit_sdk.create_rate_limit_policy(
            name="API Rate Limit",
            limit=100,
            window_seconds=60,
            scope="api_key"
        )

        # Apply rate limiting to route
        rate_limit_applied = await gateway_sdk.apply_rate_limit_policy(
            route["route_id"],
            rate_policy["policy_id"]
        )

        assert rate_limit_applied is True

    @pytest.mark.asyncio
    async def test_versioned_api_with_analytics(self):
        """Test versioned APIs with analytics tracking."""
        versioning_sdk = APIVersioningSDK(tenant_id="test-tenant")
        analytics_sdk = GatewayAnalyticsSDK(tenant_id="test-tenant")

        api_name = "Analytics Test API"

        # Create API versions
        v1 = await versioning_sdk.create_api_version(
            api_name=api_name,
            version="v1.0.0",
            upstream_url="http://api-v1:8080"
        )

        v2 = await versioning_sdk.create_api_version(
            api_name=api_name,
            version="v2.0.0",
            upstream_url="http://api-v2:8080"
        )

        # Configure version routing
        routing_config = await versioning_sdk.configure_version_routing(
            api_name=api_name,
            strategy="header",
            config={"header_name": "API-Version", "default_version": "v2.0.0"}
        )

        # Record analytics for different versions
        v1_metrics = await analytics_sdk.record_api_request(
            gateway_id="gw-versioned",
            route_id=v1["version_id"],
            method="GET",
            path="/api/v1/test",
            status_code=200,
            response_time_ms=100,
            api_version="v1.0.0"
        )

        v2_metrics = await analytics_sdk.record_api_request(
            gateway_id="gw-versioned",
            route_id=v2["version_id"],
            method="GET",
            path="/api/v2/test",
            status_code=200,
            response_time_ms=80,
            api_version="v2.0.0"
        )

        assert v1_metrics["api_version"] == "v1.0.0"
        assert v2_metrics["api_version"] == "v2.0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
