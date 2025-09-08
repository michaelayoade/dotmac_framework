"""
Tests for security validation and dependency guards.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dotmac.ticketing.core.security import (
    TenantIsolationError,
    InputValidationError,
    RateLimitError,
    validate_tenant_id,
    validate_user_id,
    validate_ticket_id,
    validate_email,
    validate_string_field,
    sanitize_search_query,
    SecurityAuditLog,
    SimpleRateLimit,
    audit_tenant_access,
    rate_limit,
)


class TestInputValidation:
    """Test input validation functions."""

    def test_validate_tenant_id_success(self):
        """Test successful tenant ID validation."""
        result = validate_tenant_id("valid-tenant-123")
        assert result == "valid-tenant-123"
    
    def test_validate_tenant_id_empty(self):
        """Test tenant ID validation with empty value."""
        with pytest.raises(TenantIsolationError, match="Tenant ID is required"):
            validate_tenant_id("")
        
        with pytest.raises(TenantIsolationError, match="Tenant ID is required"):
            validate_tenant_id(None)
    
    def test_validate_tenant_id_suspicious_patterns(self):
        """Test tenant ID validation with suspicious patterns."""
        suspicious_values = [
            "tenant/../admin",
            "tenant//admin",
            "tenant<script>alert('xss')</script>",
            'tenant"OR 1=1',
            "tenant'DROP TABLE tickets",
        ]
        
        for value in suspicious_values:
            with pytest.raises(TenantIsolationError, match="suspicious pattern"):
                validate_tenant_id(value)
    
    def test_validate_tenant_id_too_long(self):
        """Test tenant ID validation with value too long."""
        long_tenant = "a" * 256
        with pytest.raises(TenantIsolationError, match="too long"):
            validate_tenant_id(long_tenant)
    
    def test_validate_user_id_success(self):
        """Test successful user ID validation."""
        assert validate_user_id("user-123") == "user-123"
        assert validate_user_id("") is None
        assert validate_user_id(None) is None
    
    def test_validate_user_id_suspicious_patterns(self):
        """Test user ID validation with suspicious patterns."""
        suspicious_values = [
            "user<script>alert('xss')</script>",
            "user<iframe src='evil.com'>",
            "userjavascript:alert('xss')",
        ]
        
        for value in suspicious_values:
            with pytest.raises(InputValidationError, match="suspicious pattern"):
                validate_user_id(value)
    
    def test_validate_ticket_id_success(self):
        """Test successful ticket ID validation."""
        assert validate_ticket_id("ticket-123") == "ticket-123"
        assert validate_ticket_id("TKT_456") == "TKT_456"
    
    def test_validate_ticket_id_invalid(self):
        """Test ticket ID validation with invalid characters."""
        invalid_values = [
            "",
            None,
            "ticket with spaces",
            "ticket@example.com",
            "ticket<script>",
        ]
        
        for value in invalid_values:
            with pytest.raises(InputValidationError):
                validate_ticket_id(value)
    
    def test_validate_email_success(self):
        """Test successful email validation."""
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("User@Example.Com") == "user@example.com"
        assert validate_email("") is None
        assert validate_email(None) is None
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid addresses."""
        invalid_emails = [
            "not-an-email",
            "user@",
            "@example.com", 
            "user@@example.com",
            "user@example",
            "user@example.com@extra",
            "user <script>@example.com",
            "user@example.com\\test",
        ]
        
        for email in invalid_emails:
            with pytest.raises(InputValidationError):
                validate_email(email)
    
    def test_validate_string_field_success(self):
        """Test successful string field validation."""
        assert validate_string_field("Valid string", "test") == "Valid string"
        assert validate_string_field("  padded  ", "test") == "padded"
        assert validate_string_field("", "test", allow_empty=True) is None
    
    def test_validate_string_field_too_long(self):
        """Test string field validation with value too long."""
        long_string = "a" * 1001
        with pytest.raises(InputValidationError, match="too long"):
            validate_string_field(long_string, "test")
    
    def test_validate_string_field_content_fields(self):
        """Test string field validation allows newlines in content fields."""
        content = "Line 1\nLine 2\tTabbed"
        result = validate_string_field(content, "description")
        assert "\n" in result
        assert "\t" in result
    
    def test_sanitize_search_query_success(self):
        """Test successful search query sanitization."""
        assert sanitize_search_query("normal search") == "normal search"
        assert sanitize_search_query("  padded  ") == "padded"
        assert sanitize_search_query("") is None
        assert sanitize_search_query(None) is None
    
    def test_sanitize_search_query_dangerous_patterns(self):
        """Test search query sanitization removes dangerous patterns."""
        dangerous_queries = [
            "search UNION SELECT password FROM users",
            "search; DROP TABLE tickets;",
            "search /* comment */ term",
            "search -- comment",
        ]
        
        for query in dangerous_queries:
            result = sanitize_search_query(query)
            assert "UNION" not in result.upper()
            assert "SELECT" not in result.upper()
            assert "DROP" not in result.upper()
            assert "--" not in result
            assert "/*" not in result


class TestSecurityAuditLog:
    """Test security audit logging."""

    def test_audit_log_tenant_access(self, caplog):
        """Test audit logging for tenant access."""
        import logging
        audit_log = SecurityAuditLog()
        
        with caplog.at_level(logging.INFO):
            audit_log.log_tenant_access(
                "create_ticket", 
                "tenant-123", 
                "user-456", 
                "ticket-789", 
                success=True
            )
        
        assert "TENANT_ACCESS: create_ticket" in caplog.text
        assert "tenant:tenant-123" in caplog.text
        assert "user:user-456" in caplog.text
        assert "ticket:ticket-789" in caplog.text
        assert "success:True" in caplog.text
    
    def test_audit_log_validation_error(self, caplog):
        """Test audit logging for validation errors."""
        import logging
        audit_log = SecurityAuditLog()
        
        with caplog.at_level(logging.WARNING):
            audit_log.log_validation_error(
                "InputValidationError",
                "Invalid email format",
                "tenant-123"
            )
        
        assert "VALIDATION_ERROR: InputValidationError" in caplog.text
        assert "Invalid email format" in caplog.text
        assert "tenant:tenant-123" in caplog.text
    
    def test_audit_log_security_event(self, caplog):
        """Test audit logging for security events."""
        import logging
        audit_log = SecurityAuditLog()
        
        with caplog.at_level(logging.INFO):
            audit_log.log_security_event("rate_limit_exceeded", {
                "tenant_id": "tenant-123",
                "requests": 65,
                "limit": 60
            })
        
        assert "SECURITY_EVENT: rate_limit_exceeded" in caplog.text


class TestRateLimit:
    """Test rate limiting functionality."""

    def test_simple_rate_limit_within_limit(self):
        """Test rate limiter allows requests within limit."""
        rate_limiter = SimpleRateLimit(requests_per_minute=5)
        
        # Should allow first 5 requests
        for i in range(5):
            assert rate_limiter.check_rate_limit("test-user") is True
        
        # Should deny 6th request
        assert rate_limiter.check_rate_limit("test-user") is False
    
    def test_simple_rate_limit_different_users(self):
        """Test rate limiter tracks users separately."""
        rate_limiter = SimpleRateLimit(requests_per_minute=2)
        
        # Each user should have their own limit
        assert rate_limiter.check_rate_limit("user1") is True
        assert rate_limiter.check_rate_limit("user2") is True
        assert rate_limiter.check_rate_limit("user1") is True
        assert rate_limiter.check_rate_limit("user2") is True
        
        # Both users should be at limit
        assert rate_limiter.check_rate_limit("user1") is False
        assert rate_limiter.check_rate_limit("user2") is False


class TestSecurityDecorators:
    """Test security decorator functionality."""

    async def test_audit_tenant_access_decorator_success(self, caplog):
        """Test audit decorator logs successful operations."""
        import logging
        
        @audit_tenant_access("test_operation")
        async def test_function(tenant_id=None, user_id=None):
            return "success"
        
        with caplog.at_level(logging.INFO):
            result = await test_function(tenant_id="tenant-123", user_id="user-456")
        
        assert result == "success"
        assert "TENANT_ACCESS: test_operation" in caplog.text
        assert "success:True" in caplog.text
    
    async def test_audit_tenant_access_decorator_failure(self, caplog):
        """Test audit decorator logs failed operations."""
        import logging
        
        @audit_tenant_access("test_operation")
        async def test_function(tenant_id=None, user_id=None):
            raise ValueError("Test error")
        
        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError):
                await test_function(tenant_id="tenant-123", user_id="user-456")
        
        assert "TENANT_ACCESS: test_operation" in caplog.text
        assert "success:False" in caplog.text
        assert "VALIDATION_ERROR: ValueError" in caplog.text
    
    async def test_rate_limit_decorator_within_limit(self):
        """Test rate limit decorator allows requests within limit."""
        # Create fresh rate limiter for test
        from dotmac.ticketing.core.security import rate_limiter
        rate_limiter.requests = {}  # Reset
        
        @rate_limit("tenant_id")
        async def test_function(tenant_id=None):
            return "success"
        
        # Should succeed multiple times
        result1 = await test_function(tenant_id="test-tenant")
        result2 = await test_function(tenant_id="test-tenant")
        
        assert result1 == "success"
        assert result2 == "success"
    
    async def test_rate_limit_decorator_exceeds_limit(self):
        """Test rate limit decorator blocks requests over limit."""
        from dotmac.ticketing.core.security import SimpleRateLimit
        
        # Create rate limiter with very low limit for testing
        test_limiter = SimpleRateLimit(requests_per_minute=1)
        
        def rate_limit_test(identifier_key: str = 'tenant_id'):
            def decorator(func):
                async def wrapper(*args, **kwargs):
                    identifier = kwargs.get(identifier_key, 'unknown')
                    if not test_limiter.check_rate_limit(str(identifier)):
                        raise RateLimitError(f"Rate limit exceeded for {identifier}")
                    return await func(*args, **kwargs)
                return wrapper
            return decorator
        
        @rate_limit_test("tenant_id")
        async def test_function(tenant_id=None):
            return "success"
        
        # First request should succeed
        result1 = await test_function(tenant_id="test-tenant")
        assert result1 == "success"
        
        # Second request should fail
        with pytest.raises(RateLimitError):
            await test_function(tenant_id="test-tenant")


class TestIntegrationWithTicketManager:
    """Test security integration with ticket manager."""

    async def test_manager_validates_tenant_id(self):
        """Test manager validates tenant ID in methods."""
        from dotmac.ticketing.core.manager import TicketManager
        
        manager = TicketManager()
        mock_db = AsyncMock()
        
        # Should raise error for invalid tenant ID
        with pytest.raises(TenantIsolationError):
            await manager.get_ticket(mock_db, "", "ticket-123")
        
        with pytest.raises(TenantIsolationError):
            await manager.get_ticket(mock_db, None, "ticket-123")
    
    async def test_manager_validates_ticket_id(self):
        """Test manager validates ticket ID in methods."""
        from dotmac.ticketing.core.manager import TicketManager
        
        manager = TicketManager()
        mock_db = AsyncMock()
        
        # Should raise error for invalid ticket ID
        with pytest.raises(InputValidationError):
            await manager.get_ticket(mock_db, "valid-tenant", "")
        
        with pytest.raises(InputValidationError):
            await manager.get_ticket(mock_db, "valid-tenant", None)
    
    async def test_manager_sanitizes_search_queries(self):
        """Test manager sanitizes search queries in list_tickets."""
        from dotmac.ticketing.core.manager import TicketManager
        
        manager = TicketManager()
        mock_db = AsyncMock()
        
        # Mock successful database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Should sanitize dangerous search query
        filters = {"search": "test UNION SELECT password FROM users"}
        
        tickets, count = await manager.list_tickets(
            db=mock_db,
            tenant_id="valid-tenant",
            filters=filters
        )
        
        # Search should be sanitized (SQL keywords removed)
        assert "UNION" not in filters["search"].upper()
        assert "SELECT" not in filters["search"].upper()


class TestAPISecurityIntegration:
    """Test API security integration."""

    def test_ticket_create_request_validation(self):
        """Test TicketCreateRequest validates and sanitizes fields."""
        from dotmac.ticketing.api.routes import TicketCreateRequest
        
        # Test with dangerous content
        request = TicketCreateRequest(
            title="Test <script>alert('xss')</script>",
            description="Description with\nnewlines and\ttabs",
            customer_email="  TEST@EXAMPLE.COM  ",
            customer_name="Customer <script>",
            tags=["tag1", "tag2", "", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11"]
        )
        
        validated = request.validate_fields()
        
        # Should sanitize title (remove script tags)
        assert "<script>" not in validated.title
        assert "alert" not in validated.title
        
        # Should preserve newlines in description
        assert "\n" in validated.description
        assert "\t" in validated.description
        
        # Should normalize email
        assert validated.customer_email == "test@example.com"
        
        # Should sanitize customer name
        assert "<script>" not in validated.customer_name
        
        # Should limit tags to 10
        assert len(validated.tags) == 10
        assert "" not in validated.tags  # Empty tags removed
    
    def test_ticket_create_request_validation_errors(self):
        """Test TicketCreateRequest raises validation errors."""
        from dotmac.ticketing.api.routes import TicketCreateRequest
        
        # Test with invalid email
        request = TicketCreateRequest(
            title="Test",
            description="Test",
            customer_email="invalid-email"
        )
        
        with pytest.raises(InputValidationError):
            request.validate_fields()