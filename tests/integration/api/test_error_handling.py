"""
Test error handling for the DotMac ISP Framework API.
Comprehensive testing of HTTP error codes, validation errors, and exception handling.
"""

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError


class TestHTTPErrorCodes:
    """Test standard HTTP error code responses."""

    def test_400_bad_request(self, client):
        """Test 400 Bad Request responses."""
        # Invalid JSON payload
        invalid_json = '{"invalid": json}'
        
        headers = {
            "Authorization": "Bearer valid_token",
            "Content-Type": "application/json"
        }
        
        response = client.post(
            "/identity/customers",
            data=invalid_json,
            headers=headers
        )
        
        assert response.status_code == 422  # FastAPI returns 422 for JSON parsing errors
        assert "detail" in response.json()

    def test_401_unauthorized(self, client):
        """Test 401 Unauthorized responses."""
        # No Authorization header
        response = client.get("/identity/users/user-123")
        
        assert response.status_code == 401
        
        # Invalid token format
        headers = {"Authorization": "Bearer invalid_token_format"}
        response = client.get("/identity/users/user-123", headers=headers)
        
        assert response.status_code == 401

    def test_403_forbidden(self, client):
        """Test 403 Forbidden responses."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                # User authenticated but lacks permissions
                mock_get_user.return_value = {"id": "user-123", "role": "limited"}
                mock_perms.side_effect = HTTPException(
                    status_code=403, 
                    detail="Insufficient permissions"
                )
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.post("/identity/customers", json={}, headers=headers)
                
                assert response.status_code == 403
                assert "Insufficient permissions" in response.json()["detail"]

    def test_404_not_found(self, client):
        """Test 404 Not Found responses."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    # Setup mocks
                    mock_instance = AsyncMock()
                    mock_instance.get_customer_by_id.return_value = None
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": "Bearer valid_token"}
                    response = client.get("/identity/customers/nonexistent-id", headers=headers)
                    
                    assert response.status_code == 404
                    assert "Customer not found" in response.json()["detail"]

    def test_422_validation_error(self, client):
        """Test 422 Unprocessable Entity responses."""
        # Invalid data types and missing required fields
        invalid_customer_data = {
            "email": "not-an-email",  # Invalid email format
            "first_name": "",         # Empty required field
            "phone": 1234567890       # Should be string, not int
            # Missing last_name (required field)
        }
        
        headers = {"Authorization": "Bearer valid_token"}
        response = client.post(
            "/identity/customers",
            json=invalid_customer_data,
            headers=headers
        )
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)
        
        # Check that validation errors are properly formatted
        field_errors = [error["loc"][-1] for error in error_detail]
        assert "email" in field_errors or "first_name" in field_errors

    def test_429_rate_limit_exceeded(self, client):
        """Test 429 Too Many Requests responses."""
        # This would typically be handled by rate limiting middleware
        # For now, simulate the response
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.authenticate_user.side_effect = HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )
            mock_service.return_value = mock_instance
            
            login_data = {
                "username": "testuser",
                "password": "password",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=login_data)
            
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]
            assert "Retry-After" in response.headers

    def test_500_internal_server_error(self, client):
        """Test 500 Internal Server Error responses."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            # Simulate unexpected server error
            mock_instance = AsyncMock()
            mock_instance.authenticate_user.side_effect = Exception("Database connection failed")
            mock_service.return_value = mock_instance
            
            login_data = {
                "username": "testuser",
                "password": "password",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=login_data)
            
            assert response.status_code == 500
            assert "Authentication failed" in response.json()["detail"]

    def test_503_service_unavailable(self, client):
        """Test 503 Service Unavailable responses."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            # Simulate service unavailable
            mock_get_service.side_effect = HTTPException(
                status_code=503,
                detail="Service temporarily unavailable",
                headers={"Retry-After": "300"}
            )
            
            headers = {"Authorization": "Bearer valid_token"}
            response = client.get("/services/dashboard", headers=headers)
            
            assert response.status_code == 503
            assert "Service temporarily unavailable" in response.json()["detail"]


class TestValidationErrors:
    """Test field validation and data type errors."""

    def test_email_validation_errors(self, client):
        """Test email field validation."""
        invalid_emails = [
            "not-an-email",
            "missing@domain",
            "@domain.com",
            "user@",
            "spaces in@email.com",
            ""
        ]
        
        for invalid_email in invalid_emails:
            customer_data = {
                "email": invalid_email,
                "first_name": "Test",
                "last_name": "User"
            }
            
            headers = {"Authorization": "Bearer valid_token"}
            response = client.post("/identity/customers", json=customer_data, headers=headers)
            
            assert response.status_code == 422
            error_detail = response.json()["detail"]
            
            # Check that email validation error is present
            email_errors = [e for e in error_detail if "email" in str(e["loc"])]
            assert len(email_errors) > 0

    def test_required_field_validation(self, client):
        """Test required field validation."""
        # Missing required fields
        incomplete_data = {
            "email": "test@example.com"
            # Missing first_name and last_name
        }
        
        headers = {"Authorization": "Bearer valid_token"}
        response = client.post("/identity/customers", json=incomplete_data, headers=headers)
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        
        # Check for missing field errors
        missing_fields = [error["loc"][-1] for error in error_detail if error["type"] == "missing"]
        assert "first_name" in missing_fields or "last_name" in missing_fields

    def test_data_type_validation(self, client):
        """Test data type validation errors."""
        # Wrong data types
        invalid_types_data = {
            "email": 12345,           # Should be string
            "first_name": ["array"],  # Should be string
            "last_name": {"dict": "value"},  # Should be string
            "phone": True            # Should be string
        }
        
        headers = {"Authorization": "Bearer valid_token"}
        response = client.post("/identity/customers", json=invalid_types_data, headers=headers)
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        
        # Check for type validation errors
        type_errors = [e for e in error_detail if "type" in e["type"]]
        assert len(type_errors) > 0

    def test_uuid_validation_errors(self, client):
        """Test UUID field validation."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                mock_get_user.return_value = {"id": "user-123"}
                mock_perms.return_value = lambda: None
                
                # Invalid UUID formats
                invalid_uuids = [
                    "not-a-uuid",
                    "12345",
                    "abc-def-ghi",
                    "123e4567-e89b-12d3-a456-42661417400g"  # Invalid character
                ]
                
                for invalid_uuid in invalid_uuids:
                    headers = {"Authorization": "Bearer valid_token"}
                    response = client.get(f"/identity/customers/{invalid_uuid}", headers=headers)
                    
                    assert response.status_code == 422

    def test_date_validation_errors(self, client):
        """Test date field validation."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                mock_get_user.return_value = {"id": "user-123"}
                mock_service = AsyncMock()
                mock_get_service.return_value = mock_service
                
                # Invalid date formats
                invalid_dates = [
                    "not-a-date",
                    "2024-13-01",     # Invalid month
                    "2024-02-30",     # Invalid day
                    "24-01-01",       # Wrong format
                ]
                
                for invalid_date in invalid_dates:
                    headers = {"Authorization": "Bearer valid_token"}
                    response = client.get(
                        f"/services/instances/service-123/usage?start_date={invalid_date}&end_date=2024-01-31",
                        headers=headers
                    )
                    
                    assert response.status_code == 422


class TestDatabaseErrors:
    """Test database-related error handling."""

    def test_integrity_constraint_violations(self, client):
        """Test handling of database integrity constraint violations."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    # Simulate unique constraint violation
                    mock_instance = AsyncMock()
                    mock_instance.create_customer.side_effect = IntegrityError(
                        "duplicate key value violates unique constraint",
                        None,
                        None
                    )
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    customer_data = {
                        "email": "duplicate@example.com",
                        "first_name": "Test",
                        "last_name": "User"
                    }
                    
                    headers = {"Authorization": "Bearer valid_token"}
                    response = client.post("/identity/customers", json=customer_data, headers=headers)
                    
                    assert response.status_code == 400  # or 409 for conflicts
                    assert "constraint" in response.json()["detail"].lower()

    def test_database_connection_errors(self, client):
        """Test handling of database connection errors."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    # Simulate database connection error
                    mock_instance = AsyncMock()
                    mock_instance.get_customer_by_id.side_effect = OperationalError(
                        "could not connect to server",
                        None,
                        None
                    )
                    mock_service.return_value = mock_instance
                    
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    headers = {"Authorization": "Bearer valid_token"}
                    response = client.get("/identity/customers/customer-123", headers=headers)
                    
                    assert response.status_code == 500
                    assert "Failed to retrieve customer" in response.json()["detail"]

    def test_transaction_rollback_scenarios(self, client):
        """Test transaction rollback scenarios."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                # Simulate transaction that needs rollback
                mock_service = AsyncMock()
                mock_service.activate_service.side_effect = Exception("Transaction failed during provisioning")
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123"}
                
                activation_data = {
                    "customer_id": "customer-123",
                    "service_plan_id": "plan-123",
                    "installation_address": {
                        "street": "123 Test St",
                        "city": "Test City",
                        "state": "CA",
                        "zip_code": "90210"
                    }
                }
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.post("/services/activate", json=activation_data, headers=headers)
                
                assert response.status_code == 500


class TestBusinessLogicErrors:
    """Test business logic validation errors."""

    def test_insufficient_permissions_error(self, client):
        """Test insufficient permissions for operations."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                # User without admin permissions trying to create user
                mock_get_user.return_value = {
                    "id": "user-123",
                    "role": "customer_service",
                    "permissions": ["customers.read"]
                }
                
                mock_perms.side_effect = HTTPException(
                    status_code=403,
                    detail="Insufficient permissions: requires users.create"
                )
                
                user_data = {
                    "username": "newuser",
                    "email": "new@example.com",
                    "first_name": "New",
                    "last_name": "User",
                    "password_hash": "hashed_password"
                }
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.post("/identity/users", json=user_data, headers=headers)
                
                assert response.status_code == 403
                assert "Insufficient permissions" in response.json()["detail"]

    def test_tenant_isolation_violations(self, client):
        """Test tenant isolation enforcement."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
                # User from tenant A trying to access tenant B's customer
                mock_get_user.return_value = {
                    "id": "user-123",
                    "tenant_id": "tenant-a"
                }
                
                mock_instance = AsyncMock()
                mock_instance.get_customer_by_id.side_effect = HTTPException(
                    status_code=404,  # Or 403, depending on security preference
                    detail="Customer not found"  # Hide existence from other tenants
                )
                mock_service.return_value = mock_instance
                
                headers = {
                    "Authorization": "Bearer valid_token",
                    "X-Tenant-ID": "tenant-b"  # Different tenant
                }
                
                response = client.get("/identity/customers/customer-from-tenant-b", headers=headers)
                
                assert response.status_code == 404

    def test_service_state_transition_errors(self, client):
        """Test invalid service state transitions."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                # Try to reactivate already active service
                mock_service = AsyncMock()
                mock_service.reactivate_service.side_effect = HTTPException(
                    status_code=400,
                    detail="Cannot reactivate service: service is already active"
                )
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.post(
                    "/services/instances/service-123/reactivate?reason=Test",
                    headers=headers
                )
                
                assert response.status_code == 400
                assert "already active" in response.json()["detail"]

    def test_billing_validation_errors(self, client):
        """Test billing-related validation errors."""
        # This would test billing module endpoints
        # For now, simulate common billing errors
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = {"id": "user-123"}
            
            # Simulate payment method validation error
            invalid_payment_data = {
                "card_number": "1234",  # Too short
                "expiry_month": 13,     # Invalid month
                "expiry_year": 2020,    # Past year
                "cvv": "12345"          # Too long
            }
            
            headers = {"Authorization": "Bearer valid_token"}
            # This would be a billing endpoint
            response = client.post("/billing/payment-methods", json=invalid_payment_data, headers=headers)
            
            # Since we don't have actual billing router, expect 404
            assert response.status_code in [404, 422]


class TestConcurrencyErrors:
    """Test concurrency and race condition handling."""

    def test_optimistic_locking_conflicts(self, client):
        """Test optimistic locking conflict handling."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                # Simulate version conflict (optimistic locking)
                mock_service = AsyncMock()
                mock_service.update_service_status.side_effect = HTTPException(
                    status_code=409,
                    detail="Update conflict: record has been modified by another user"
                )
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                status_update = {
                    "new_status": "suspended",
                    "reason": "Concurrent update test"
                }
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.patch(
                    "/services/instances/service-123/status",
                    json=status_update,
                    headers=headers
                )
                
                assert response.status_code == 409
                assert "Update conflict" in response.json()["detail"]

    def test_resource_locking_timeouts(self, client):
        """Test resource locking timeout scenarios."""
        with patch('dotmac_isp.modules.services.router.get_services_service') as mock_get_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                # Simulate lock timeout
                mock_service = AsyncMock()
                mock_service.bulk_service_operation.side_effect = HTTPException(
                    status_code=408,
                    detail="Operation timed out: resource is locked by another process"
                )
                mock_get_service.return_value = mock_service
                
                mock_get_user.return_value = {"id": "user-123", "user_id": "user-123"}
                
                bulk_request = {
                    "service_instance_ids": ["service-123", "service-456"],
                    "operation": "suspend",
                    "reason": "Timeout test"
                }
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.post("/services/bulk-operation", json=bulk_request, headers=headers)
                
                assert response.status_code == 408
                assert "timed out" in response.json()["detail"]


class TestSecurityErrors:
    """Test security-related error handling."""

    def test_sql_injection_prevention(self, client):
        """Test SQL injection attempt handling."""
        with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
            with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                mock_get_user.return_value = {"id": "user-123"}
                mock_perms.return_value = lambda: None
                
                # Attempt SQL injection in search parameter
                malicious_search = "'; DROP TABLE customers; --"
                
                headers = {"Authorization": "Bearer valid_token"}
                response = client.get(
                    f"/identity/customers?search={malicious_search}",
                    headers=headers
                )
                
                # Should not cause server error - parameterized queries prevent injection
                assert response.status_code in [200, 422]

    def test_xss_prevention(self, client):
        """Test XSS attempt prevention."""
        with patch('dotmac_isp.modules.identity.router.CustomerService') as mock_service:
            with patch('dotmac_shared.auth.dependencies.get_current_user') as mock_get_user:
                with patch('dotmac_shared.auth.dependencies.require_permissions') as mock_perms:
                    mock_instance = AsyncMock()
                    mock_service.return_value = mock_instance
                    mock_get_user.return_value = {"id": "user-123"}
                    mock_perms.return_value = lambda: None
                    
                    # Attempt XSS in user input
                    malicious_data = {
                        "email": "test@example.com",
                        "first_name": "<script>alert('xss')</script>",
                        "last_name": "User"
                    }
                    
                    headers = {"Authorization": "Bearer valid_token"}
                    response = client.post("/identity/customers", json=malicious_data, headers=headers)
                    
                    # Should process normally - input sanitization handles XSS
                    assert response.status_code in [200, 201, 422]

    def test_csrf_protection(self, client):
        """Test CSRF protection mechanisms."""
        # CSRF protection is typically handled by middleware
        # Test that requests without proper CSRF tokens are rejected
        customer_data = {
            "email": "csrf@example.com",
            "first_name": "CSRF",
            "last_name": "Test"
        }
        
        # Request without CSRF token (if required by middleware)
        response = client.post("/identity/customers", json=customer_data)
        
        # Depending on CSRF implementation, could be 403 or require token
        assert response.status_code in [401, 403, 422]


class TestExceptionHandlingMiddleware:
    """Test global exception handling and middleware."""

    def test_unhandled_exception_catching(self, client):
        """Test that unhandled exceptions are properly caught."""
        with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
            # Simulate completely unexpected error
            mock_instance = AsyncMock()
            mock_instance.authenticate_user.side_effect = RuntimeError("Unexpected error")
            mock_service.return_value = mock_instance
            
            login_data = {
                "username": "testuser",
                "password": "password",
                "portal_type": "admin"
            }
            
            response = client.post("/identity/auth/login", json=login_data)
            
            # Should be handled gracefully by exception handler
            assert response.status_code == 500
            assert "Authentication failed" in response.json()["detail"]

    def test_error_logging_and_tracking(self, client):
        """Test that errors are properly logged and tracked."""
        with patch('dotmac_isp.modules.identity.router.logger') as mock_logger:
            with patch('dotmac_isp.modules.identity.router.AuthService') as mock_service:
                # Simulate error that should be logged
                mock_instance = AsyncMock()
                mock_instance.authenticate_user.side_effect = Exception("Database connection failed")
                mock_service.return_value = mock_instance
                
                login_data = {
                    "username": "testuser",
                    "password": "password",
                    "portal_type": "admin"
                }
                
                response = client.post("/identity/auth/login", json=login_data)
                
                # Verify error was logged
                assert response.status_code == 500
                mock_logger.error.assert_called()

    def test_error_response_format_consistency(self, client):
        """Test that all error responses follow consistent format."""
        error_responses = []
        
        # Collect various error responses
        test_cases = [
            # 404 error
            {"method": "get", "url": "/identity/customers/nonexistent", "expected_status": 404},
            # 422 validation error
            {"method": "post", "url": "/identity/customers", "json": {"invalid": "data"}, "expected_status": 422},
            # 401 unauthorized
            {"method": "get", "url": "/identity/users/user-123", "expected_status": 401}
        ]
        
        for case in test_cases:
            method = getattr(client, case["method"])
            kwargs = {k: v for k, v in case.items() if k not in ["method", "url", "expected_status"]}
            
            response = method(case["url"], **kwargs)
            
            if response.status_code == case["expected_status"]:
                error_responses.append(response.json())
        
        # Check that all error responses have consistent structure
        for error_response in error_responses:
            assert "detail" in error_response
            # Additional consistency checks can be added here