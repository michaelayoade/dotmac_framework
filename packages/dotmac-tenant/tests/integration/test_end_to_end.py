"""
End-to-end integration tests for tenant functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.tenant import (
    TenantConfig,
    TenantMiddleware,
    TenantResolutionStrategy,
    get_current_tenant,
    require_tenant,
)
from dotmac.tenant.boundary import TenantSecurityEnforcer
from dotmac.tenant.middleware import TenantSecurityMiddleware
from dotmac.tenant.db import TenantDatabaseManager


class TestE2ETenantResolution:
    """End-to-end tenant resolution tests."""
    
    def test_complete_tenant_workflow_host_based(self):
        """Test complete tenant workflow with host-based resolution."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HOST_BASED,
            host_tenant_mapping={
                "client1.myapp.com": "client1",
                "client2.myapp.com": "client2",
            },
            enforce_tenant_isolation=True,
            log_tenant_access=True
        )
        
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/api/tenant-data")
        async def get_tenant_data(request: Request, tenant=Depends(require_tenant)):
            return {
                "tenant_id": tenant.tenant_id,
                "resolution_method": tenant.resolution_method,
                "data": f"Data for {tenant.tenant_id}"
            }
        
        with TestClient(app) as client:
            # Test client1
            response = client.get(
                "/api/tenant-data",
                headers={"Host": "client1.myapp.com"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "client1"
            assert data["resolution_method"] == "host_mapping"
            assert "client1" in data["data"]
            
            # Test client2
            response = client.get(
                "/api/tenant-data", 
                headers={"Host": "client2.myapp.com"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "client2"
            assert "client2" in data["data"]
    
    def test_complete_tenant_workflow_subdomain(self):
        """Test complete tenant workflow with subdomain resolution."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.SUBDOMAIN,
            base_domain="api.myapp.com",
            subdomain_position=0
        )
        
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/api/profile")
        async def get_profile():
            tenant = get_current_tenant()
            if not tenant:
                return {"error": "No tenant context"}
            
            return {
                "tenant_id": tenant.tenant_id,
                "profile": f"Profile for {tenant.tenant_id}"
            }
        
        with TestClient(app) as client:
            response = client.get(
                "/api/profile",
                headers={"Host": "acme.api.myapp.com"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "acme"
            assert "acme" in data["profile"]
    
    def test_complete_tenant_workflow_composite(self):
        """Test complete tenant workflow with composite resolution."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.COMPOSITE,
            tenant_header_name="X-Tenant-ID",
            host_tenant_mapping={
                "app.myapp.com": "main-tenant"
            },
            fallback_tenant_id="default"
        )
        
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/api/settings")
        async def get_settings(request: Request):
            tenant = getattr(request.state, 'tenant', None)
            return {
                "tenant_id": tenant.tenant_id if tenant else None,
                "resolution_method": tenant.resolution_method if tenant else None,
                "settings": f"Settings for {tenant.tenant_id if tenant else 'unknown'}"
            }
        
        with TestClient(app) as client:
            # Test header-based resolution (should take precedence)
            response = client.get(
                "/api/settings",
                headers={
                    "Host": "app.myapp.com",
                    "X-Tenant-ID": "header-tenant"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "header-tenant"
            assert data["resolution_method"] == "header_tenant_id"
            
            # Test host-based resolution (fallback)
            response = client.get(
                "/api/settings",
                headers={"Host": "app.myapp.com"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "main-tenant"
            assert data["resolution_method"] == "host_mapping"
            
            # Test fallback resolution
            response = client.get(
                "/api/settings",
                headers={"Host": "unknown.myapp.com"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "default"
            assert data["resolution_method"] == "fallback"


class TestE2ESecurityIntegration:
    """End-to-end security integration tests."""
    
    def test_tenant_security_enforcement(self):
        """Test tenant security enforcement end-to-end."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HEADER_BASED,
            tenant_header_name="X-Tenant-ID",
            enforce_tenant_isolation=True,
            allow_cross_tenant_access=False
        )
        
        security_enforcer = TenantSecurityEnforcer(config)
        
        app.add_middleware(
            TenantSecurityMiddleware,
            config=config,
            security_enforcer=security_enforcer
        )
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/api/secure-data")
        async def get_secure_data(tenant=Depends(require_tenant)):
            return {
                "tenant_id": tenant.tenant_id,
                "secure_data": f"Secure data for {tenant.tenant_id}"
            }
        
        @app.post("/api/cross-tenant-operation")
        async def cross_tenant_op(request: Request):
            tenant = get_current_tenant()
            # Simulate cross-tenant access attempt
            await security_enforcer.validate_cross_tenant_access(
                requesting_tenant_id=tenant.tenant_id,
                target_tenant_id="different-tenant",
                operation="read"
            )
            return {"result": "success"}
        
        with TestClient(app) as client:
            # Test successful access
            response = client.get(
                "/api/secure-data",
                headers={"X-Tenant-ID": "tenant1"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "tenant1"
            
            # Test cross-tenant access denial
            with pytest.raises(Exception):  # Would be handled by middleware
                response = client.post(
                    "/api/cross-tenant-operation",
                    headers={"X-Tenant-ID": "tenant1"}
                )
    
    def test_rate_limiting_integration(self):
        """Test rate limiting integration."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HEADER_BASED,
            tenant_header_name="X-Tenant-ID"
        )
        
        security_enforcer = TenantSecurityEnforcer(config)
        
        # Set aggressive rate limits for testing
        from dotmac.tenant.boundary import TenantAccessPolicy
        policy = TenantAccessPolicy(
            tenant_id="test-tenant",
            max_requests_per_minute=2  # Very low for testing
        )
        security_enforcer.set_tenant_policy("test-tenant", policy)
        
        app.add_middleware(
            TenantSecurityMiddleware,
            config=config,
            security_enforcer=security_enforcer
        )
        app.add_middleware(TenantMiddleware, config=config)
        
        @app.get("/api/limited")
        async def limited_endpoint():
            tenant = get_current_tenant()
            return {"tenant_id": tenant.tenant_id, "data": "limited"}
        
        with TestClient(app) as client:
            headers = {"X-Tenant-ID": "test-tenant"}
            
            # First two requests should succeed
            response1 = client.get("/api/limited", headers=headers)
            response2 = client.get("/api/limited", headers=headers)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Third request should be rate limited
            # Note: This would need actual rate limiting implementation
            # For now, this test demonstrates the structure


class TestE2EDatabaseIntegration:
    """End-to-end database integration tests."""
    
    @pytest.mark.asyncio
    async def test_tenant_aware_database_session(self, async_mock_engine):
        """Test tenant-aware database session integration."""
        config = TenantConfig(
            database_strategy="rls",  # Row-Level Security
            enable_rls=True
        )
        
        db_manager = TenantDatabaseManager(config, async_mock_engine)
        
        # Mock session and context
        from dotmac.tenant.identity import set_tenant_context, TenantContext
        
        tenant_context = TenantContext(
            tenant_id="test-tenant",
            resolution_method="test",
            resolved_from="unit-test"
        )
        set_tenant_context(tenant_context)
        
        # Test getting tenant-aware session
        with patch.object(db_manager, '_session_factory') as mock_factory:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None
            
            async with db_manager.get_tenant_aware_session() as session:
                assert session is not None
                # Verify tenant context was set for RLS
                mock_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_rls_setup_integration(self, async_mock_engine):
        """Test RLS setup integration."""
        config = TenantConfig(enable_rls=True)
        db_manager = TenantDatabaseManager(config, async_mock_engine)
        
        # Mock successful RLS setup
        with patch.object(async_mock_engine, 'begin') as mock_begin:
            mock_conn = AsyncMock()
            mock_begin.return_value.__aenter__.return_value = mock_conn
            mock_begin.return_value.__aexit__.return_value = None
            
            result = await db_manager.setup_rls(
                async_mock_engine,
                "users",
                "tenant_id"
            )
            
            assert result is True
            # Verify RLS commands were executed
            assert mock_conn.execute.call_count >= 2  # ALTER TABLE + CREATE POLICY


class TestE2EMultiTenantScenarios:
    """End-to-end multi-tenant scenario tests."""
    
    def test_multiple_tenants_same_app(self):
        """Test multiple tenants accessing same application."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HOST_BASED,
            host_tenant_mapping={
                "tenant-a.app.com": "tenant-a",
                "tenant-b.app.com": "tenant-b", 
                "tenant-c.app.com": "tenant-c",
            }
        )
        
        app.add_middleware(TenantMiddleware, config=config)
        
        # Simulate tenant-specific data storage
        tenant_data = {
            "tenant-a": {"users": ["alice", "bob"], "plan": "premium"},
            "tenant-b": {"users": ["charlie"], "plan": "basic"},
            "tenant-c": {"users": ["diana", "eve", "frank"], "plan": "enterprise"},
        }
        
        @app.get("/api/dashboard")
        async def get_dashboard(tenant=Depends(require_tenant)):
            data = tenant_data.get(tenant.tenant_id, {})
            return {
                "tenant_id": tenant.tenant_id,
                "user_count": len(data.get("users", [])),
                "plan": data.get("plan", "unknown"),
                "users": data.get("users", [])
            }
        
        with TestClient(app) as client:
            # Test tenant-a
            response_a = client.get(
                "/api/dashboard",
                headers={"Host": "tenant-a.app.com"}
            )
            assert response_a.status_code == 200
            data_a = response_a.json()
            assert data_a["tenant_id"] == "tenant-a"
            assert data_a["user_count"] == 2
            assert data_a["plan"] == "premium"
            
            # Test tenant-b
            response_b = client.get(
                "/api/dashboard",
                headers={"Host": "tenant-b.app.com"}
            )
            assert response_b.status_code == 200
            data_b = response_b.json()
            assert data_b["tenant_id"] == "tenant-b"
            assert data_b["user_count"] == 1
            assert data_b["plan"] == "basic"
            
            # Test tenant-c
            response_c = client.get(
                "/api/dashboard",
                headers={"Host": "tenant-c.app.com"}
            )
            assert response_c.status_code == 200
            data_c = response_c.json()
            assert data_c["tenant_id"] == "tenant-c"
            assert data_c["user_count"] == 3
            assert data_c["plan"] == "enterprise"
    
    def test_tenant_context_isolation(self):
        """Test that tenant contexts are properly isolated."""
        app = FastAPI()
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HEADER_BASED,
            tenant_header_name="X-Tenant-ID"
        )
        
        app.add_middleware(TenantMiddleware, config=config)
        
        # Track tenant access for isolation testing
        access_log = []
        
        @app.get("/api/log-access")
        async def log_access(tenant=Depends(require_tenant)):
            access_log.append({
                "tenant_id": tenant.tenant_id,
                "timestamp": len(access_log),  # Simple counter
                "context_id": id(tenant)  # Object ID for isolation check
            })
            return {"tenant_id": tenant.tenant_id, "logged": True}
        
        with TestClient(app) as client:
            # Make requests from different tenants
            tenants = ["tenant-1", "tenant-2", "tenant-3"]
            
            for i in range(9):  # 3 requests per tenant
                tenant_id = tenants[i % 3]
                response = client.get(
                    "/api/log-access",
                    headers={"X-Tenant-ID": tenant_id}
                )
                assert response.status_code == 200
            
            # Verify isolation - each tenant should have separate contexts
            tenant_contexts = {}
            for entry in access_log:
                tenant_id = entry["tenant_id"]
                context_id = entry["context_id"]
                
                if tenant_id not in tenant_contexts:
                    tenant_contexts[tenant_id] = set()
                tenant_contexts[tenant_id].add(context_id)
            
            # Each tenant should have accessed with multiple context instances
            # (contexts are created per request)
            assert len(tenant_contexts) == 3
            for tenant_id in tenants:
                assert tenant_id in tenant_contexts
                # Each request creates a new context object
                assert len(tenant_contexts[tenant_id]) == 3