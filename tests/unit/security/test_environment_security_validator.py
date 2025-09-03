"""
Comprehensive unit tests for the Environment Security Validator.

Tests cover:
- Security validation across different environments
- Compliance scoring and violation detection
- Security policy enforcement
- Audit logging and reporting
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from dotmac_shared.security.environment_security_validator import (
    Environment,
    SecurityLevel,
    ViolationSeverity,
    SecurityViolation,
    SecurityValidationResult,
    SecurityAuditLog,
    EnvironmentSecurityValidator,
    ComplianceReport,
    SecurityMetrics,
)


class TestEnvironment:
    """Test Environment enum from security validator."""
    
    def test_environment_values(self):
        """Test environment values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"


class TestSecurityLevel:
    """Test SecurityLevel enum."""
    
    def test_security_levels(self):
        """Test security level values."""
        assert SecurityLevel.MINIMAL == "minimal"
        assert SecurityLevel.STANDARD == "standard"
        assert SecurityLevel.ENHANCED == "enhanced"
        assert SecurityLevel.MAXIMUM == "maximum"


class TestViolationSeverity:
    """Test ViolationSeverity enum."""
    
    def test_violation_severities(self):
        """Test violation severity values."""
        assert ViolationSeverity.LOW == "low"
        assert ViolationSeverity.MEDIUM == "medium"
        assert ViolationSeverity.HIGH == "high"
        assert ViolationSeverity.CRITICAL == "critical"


class TestSecurityViolation:
    """Test SecurityViolation model."""
    
    def test_violation_creation(self):
        """Test security violation creation."""
        violation = SecurityViolation(
            violation_type="weak_password",
            severity=ViolationSeverity.HIGH,
            description="Password does not meet strength requirements",
            component="authentication",
            recommendation="Use complex password with minimum 12 characters"
        )
        
        assert violation.violation_type == "weak_password"
        assert violation.severity == ViolationSeverity.HIGH
        assert "strength requirements" in violation.description
        assert violation.component == "authentication"
        assert "complex password" in violation.recommendation
    
    def test_violation_with_metadata(self):
        """Test security violation with metadata."""
        metadata = {"password_length": 6, "has_special_chars": False}
        
        violation = SecurityViolation(
            violation_type="password_policy",
            severity=ViolationSeverity.MEDIUM,
            description="Password policy violation",
            component="user_management",
            recommendation="Enforce password complexity",
            metadata=metadata
        )
        
        assert violation.metadata == metadata
        assert violation.metadata["password_length"] == 6


class TestSecurityValidationResult:
    """Test SecurityValidationResult model."""
    
    def test_validation_result_success(self):
        """Test successful validation result."""
        result = SecurityValidationResult(
            environment=Environment.PRODUCTION,
            security_level=SecurityLevel.ENHANCED,
            compliance_score=95,
            violations=[],
            passed_checks=25,
            total_checks=25,
            validation_timestamp=datetime.now()
        )
        
        assert result.environment == Environment.PRODUCTION
        assert result.security_level == SecurityLevel.ENHANCED
        assert result.compliance_score == 95
        assert len(result.violations) == 0
        assert result.is_compliant is True  # No violations = compliant
    
    def test_validation_result_with_violations(self):
        """Test validation result with violations."""
        violations = [
            SecurityViolation(
                violation_type="missing_https",
                severity=ViolationSeverity.HIGH,
                description="HTTPS not enforced",
                component="network",
                recommendation="Enable HTTPS enforcement"
            )
        ]
        
        result = SecurityValidationResult(
            environment=Environment.PRODUCTION,
            security_level=SecurityLevel.STANDARD,
            compliance_score=78,
            violations=violations,
            passed_checks=18,
            total_checks=25,
            validation_timestamp=datetime.now()
        )
        
        assert result.compliance_score == 78
        assert len(result.violations) == 1
        assert result.violations[0].severity == ViolationSeverity.HIGH
        assert result.is_compliant is False  # Has violations


class TestSecurityAuditLog:
    """Test SecurityAuditLog model."""
    
    def test_audit_log_creation(self):
        """Test audit log creation."""
        audit_log = SecurityAuditLog(
            environment=Environment.PRODUCTION,
            action="security_validation",
            component="environment_validator",
            user_id=str(uuid4()),
            details={"validation_type": "comprehensive", "checks_run": 25},
            timestamp=datetime.now()
        )
        
        assert audit_log.environment == Environment.PRODUCTION
        assert audit_log.action == "security_validation"
        assert audit_log.component == "environment_validator"
        assert "validation_type" in audit_log.details
    
    def test_audit_log_with_violation(self):
        """Test audit log with security violation."""
        violation_details = {
            "violation_type": "insecure_config",
            "severity": "high",
            "component": "database"
        }
        
        audit_log = SecurityAuditLog(
            environment=Environment.STAGING,
            action="violation_detected",
            component="config_validator",
            details=violation_details,
            timestamp=datetime.now()
        )
        
        assert audit_log.action == "violation_detected"
        assert audit_log.details["severity"] == "high"


class TestEnvironmentSecurityValidator:
    """Test EnvironmentSecurityValidator class."""
    
    @pytest.fixture
    def validator(self):
        return EnvironmentSecurityValidator(
            environment=Environment.PRODUCTION,
            security_level=SecurityLevel.ENHANCED
        )
    
    @pytest.fixture
    def dev_validator(self):
        return EnvironmentSecurityValidator(
            environment=Environment.DEVELOPMENT,
            security_level=SecurityLevel.MINIMAL
        )
    
    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.environment == Environment.PRODUCTION
        assert validator.security_level == SecurityLevel.ENHANCED
        assert validator.required_compliance_score == 90  # High for production
        assert len(validator.security_policies) > 0
    
    def test_dev_validator_initialization(self, dev_validator):
        """Test development validator initialization."""
        assert dev_validator.environment == Environment.DEVELOPMENT
        assert dev_validator.security_level == SecurityLevel.MINIMAL
        assert dev_validator.required_compliance_score == 60  # Lower for dev
    
    @pytest.mark.asyncio
    async def test_validate_secrets_management_production(self, validator):
        """Test secrets management validation in production."""
        # Mock OpenBao client availability
        with patch('dotmac_shared.security.secrets_policy.OpenBaoClient') as mock_client:
            mock_client.return_value.health_check = AsyncMock(return_value=True)
            
            result = await validator.validate_secrets_management()
            
            assert result.passed is True
            assert "OpenBao available" in result.details
    
    @pytest.mark.asyncio
    async def test_validate_secrets_management_missing_vault(self, validator):
        """Test secrets management validation with missing vault."""
        with patch('dotmac_shared.security.secrets_policy.OpenBaoClient') as mock_client:
            mock_client.return_value.health_check = AsyncMock(return_value=False)
            
            result = await validator.validate_secrets_management()
            
            assert result.passed is False
            assert any(v.violation_type == "vault_unavailable" for v in result.violations)
    
    @pytest.mark.asyncio
    async def test_validate_csrf_protection(self, validator):
        """Test CSRF protection validation."""
        result = await validator.validate_csrf_protection()
        
        # Should pass basic CSRF validation
        assert result.passed is True
        assert "CSRF configuration" in result.details
    
    @pytest.mark.asyncio
    async def test_validate_https_enforcement_production(self, validator):
        """Test HTTPS enforcement validation in production."""
        # Mock config that requires HTTPS
        with patch.dict('os.environ', {'REQUIRE_HTTPS': 'true'}):
            result = await validator.validate_https_enforcement()
            
            assert result.passed is True
            assert "HTTPS enforced" in result.details
    
    @pytest.mark.asyncio
    async def test_validate_https_enforcement_missing(self, validator):
        """Test HTTPS enforcement validation when missing."""
        with patch.dict('os.environ', {'REQUIRE_HTTPS': 'false'}):
            result = await validator.validate_https_enforcement()
            
            assert result.passed is False
            assert any(v.violation_type == "https_not_enforced" for v in result.violations)
            assert any(v.severity == ViolationSeverity.HIGH for v in result.violations)
    
    @pytest.mark.asyncio
    async def test_validate_authentication_security(self, validator):
        """Test authentication security validation."""
        result = await validator.validate_authentication_security()
        
        # Basic validation should include JWT, session, and password policies
        assert result.passed is not None
        assert "Authentication security" in result.details
    
    @pytest.mark.asyncio
    async def test_validate_database_security(self, validator):
        """Test database security validation."""
        # Mock database connection with security features
        with patch('dotmac_shared.database.get_db_security_status') as mock_db:
            mock_db.return_value = {
                'ssl_enabled': True,
                'encryption_at_rest': True,
                'connection_pooling': True,
                'query_logging': True
            }
            
            result = await validator.validate_database_security()
            
            assert result.passed is True
            assert "Database security validated" in result.details
    
    @pytest.mark.asyncio
    async def test_validate_api_security(self, validator):
        """Test API security validation."""
        result = await validator.validate_api_security()
        
        # Should validate rate limiting, input validation, etc.
        assert result.passed is not None
        assert "API security" in result.details
    
    @pytest.mark.asyncio
    async def test_validate_logging_monitoring(self, validator):
        """Test logging and monitoring validation."""
        result = await validator.validate_logging_monitoring()
        
        # Should check for proper logging configuration
        assert result.passed is not None
        assert "Logging and monitoring" in result.details
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_validation(self, validator):
        """Test comprehensive security validation."""
        with patch.object(validator, 'validate_secrets_management') as mock_secrets:
            with patch.object(validator, 'validate_csrf_protection') as mock_csrf:
                with patch.object(validator, 'validate_https_enforcement') as mock_https:
                    # Mock all validations as passing
                    mock_secrets.return_value = Mock(passed=True, violations=[], score=100)
                    mock_csrf.return_value = Mock(passed=True, violations=[], score=100)
                    mock_https.return_value = Mock(passed=True, violations=[], score=100)
                    
                    result = await validator.validate_comprehensive_security()
                    
                    assert isinstance(result, SecurityValidationResult)
                    assert result.environment == Environment.PRODUCTION
                    assert result.security_level == SecurityLevel.ENHANCED
                    assert result.compliance_score >= 90  # Should meet production requirements
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation_with_failures(self, validator):
        """Test comprehensive validation with some failures."""
        violation = SecurityViolation(
            violation_type="test_failure",
            severity=ViolationSeverity.MEDIUM,
            description="Test failure",
            component="test",
            recommendation="Fix test issue"
        )
        
        with patch.object(validator, 'validate_secrets_management') as mock_secrets:
            with patch.object(validator, 'validate_csrf_protection') as mock_csrf:
                # Mock one failure and one success
                mock_secrets.return_value = Mock(passed=False, violations=[violation], score=60)
                mock_csrf.return_value = Mock(passed=True, violations=[], score=100)
                
                result = await validator.validate_comprehensive_security()
                
                assert result.compliance_score < 90  # Should not meet production requirements
                assert len(result.violations) > 0
                assert result.is_compliant is False
    
    def test_calculate_compliance_score(self, validator):
        """Test compliance score calculation."""
        violations = [
            SecurityViolation("test1", ViolationSeverity.LOW, "Low severity", "test", "fix"),
            SecurityViolation("test2", ViolationSeverity.HIGH, "High severity", "test", "fix"),
            SecurityViolation("test3", ViolationSeverity.MEDIUM, "Medium severity", "test", "fix"),
        ]
        
        score = validator.calculate_compliance_score(violations, total_checks=10)
        
        # Score should be reduced based on violation severities
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert score < 100  # Should be reduced due to violations
    
    def test_calculate_compliance_score_no_violations(self, validator):
        """Test compliance score with no violations."""
        score = validator.calculate_compliance_score([], total_checks=10)
        assert score == 100
    
    def test_get_required_compliance_score(self):
        """Test required compliance score for different environments."""
        prod_validator = EnvironmentSecurityValidator(
            Environment.PRODUCTION, SecurityLevel.ENHANCED
        )
        assert prod_validator.required_compliance_score == 90
        
        dev_validator = EnvironmentSecurityValidator(
            Environment.DEVELOPMENT, SecurityLevel.MINIMAL
        )
        assert dev_validator.required_compliance_score == 60
        
        staging_validator = EnvironmentSecurityValidator(
            Environment.STAGING, SecurityLevel.STANDARD
        )
        assert staging_validator.required_compliance_score == 80
    
    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, validator):
        """Test compliance report generation."""
        # Mock a validation result
        violations = [
            SecurityViolation(
                "https_missing",
                ViolationSeverity.HIGH,
                "HTTPS not enforced",
                "network",
                "Enable HTTPS"
            )
        ]
        
        validation_result = SecurityValidationResult(
            environment=Environment.PRODUCTION,
            security_level=SecurityLevel.ENHANCED,
            compliance_score=85,
            violations=violations,
            passed_checks=20,
            total_checks=25,
            validation_timestamp=datetime.now()
        )
        
        report = await validator.generate_compliance_report(validation_result)
        
        assert isinstance(report, ComplianceReport)
        assert report.environment == Environment.PRODUCTION
        assert report.compliance_score == 85
        assert len(report.violations_by_severity) > 0
        assert ViolationSeverity.HIGH in report.violations_by_severity
        assert report.recommendations is not None
    
    @pytest.mark.asyncio
    async def test_audit_security_event(self, validator):
        """Test security event auditing."""
        event_details = {
            "event_type": "validation_completed",
            "compliance_score": 95,
            "violations_found": 2
        }
        
        await validator.audit_security_event("security_validation", event_details)
        
        # Should create audit log (test that no exception is raised)
        assert True  # If we reach here, audit logging didn't fail
    
    def test_is_compliant(self, validator):
        """Test compliance determination logic."""
        # Test with score above threshold
        assert validator.is_compliant(95) is True
        
        # Test with score below threshold
        assert validator.is_compliant(85) is False
        
        # Test with score exactly at threshold
        assert validator.is_compliant(90) is True


class TestComplianceReport:
    """Test ComplianceReport model."""
    
    def test_compliance_report_creation(self):
        """Test compliance report creation."""
        violations_by_severity = {
            ViolationSeverity.HIGH: 2,
            ViolationSeverity.MEDIUM: 1,
            ViolationSeverity.LOW: 0
        }
        
        report = ComplianceReport(
            environment=Environment.PRODUCTION,
            security_level=SecurityLevel.ENHANCED,
            compliance_score=88,
            is_compliant=False,
            violations_by_severity=violations_by_severity,
            total_checks=25,
            passed_checks=22,
            validation_timestamp=datetime.now(),
            recommendations=["Enable HTTPS", "Fix password policy"],
            next_validation_due=datetime.now() + timedelta(days=30)
        )
        
        assert report.environment == Environment.PRODUCTION
        assert report.compliance_score == 88
        assert report.is_compliant is False
        assert report.violations_by_severity[ViolationSeverity.HIGH] == 2
        assert len(report.recommendations) == 2


class TestSecurityMetrics:
    """Test SecurityMetrics model."""
    
    def test_security_metrics_creation(self):
        """Test security metrics creation."""
        metrics = SecurityMetrics(
            environment=Environment.PRODUCTION,
            total_validations=100,
            passed_validations=95,
            average_compliance_score=92.5,
            critical_violations=2,
            high_violations=8,
            medium_violations=15,
            low_violations=25,
            last_validation=datetime.now(),
            trend_direction="improving"
        )
        
        assert metrics.environment == Environment.PRODUCTION
        assert metrics.total_validations == 100
        assert metrics.passed_validations == 95
        assert metrics.average_compliance_score == 92.5
        assert metrics.success_rate == 95.0  # 95/100 * 100
        assert metrics.trend_direction == "improving"


class TestSecurityValidationIntegration:
    """Test security validation integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_multi_environment_validation(self):
        """Test validation across multiple environments."""
        environments = [
            (Environment.DEVELOPMENT, SecurityLevel.MINIMAL),
            (Environment.STAGING, SecurityLevel.STANDARD),
            (Environment.PRODUCTION, SecurityLevel.ENHANCED)
        ]
        
        results = []
        for env, level in environments:
            validator = EnvironmentSecurityValidator(env, level)
            
            # Mock basic validations
            with patch.object(validator, 'validate_secrets_management') as mock_secrets:
                mock_secrets.return_value = Mock(passed=True, violations=[], score=100)
                
                result = await validator.validate_comprehensive_security()
                results.append(result)
        
        # Production should have highest requirements
        prod_result = results[2]  # Production result
        assert prod_result.security_level == SecurityLevel.ENHANCED
        
        # All environments should have some validation results
        for result in results:
            assert isinstance(result, SecurityValidationResult)
            assert result.environment in [env for env, _ in environments]
    
    @pytest.mark.asyncio
    async def test_security_policy_enforcement(self):
        """Test security policy enforcement across different scenarios."""
        validator = EnvironmentSecurityValidator(
            Environment.PRODUCTION,
            SecurityLevel.MAXIMUM
        )
        
        # Test with various mock conditions
        test_scenarios = [
            {"vault_available": True, "https_enabled": True, "expected_pass": True},
            {"vault_available": False, "https_enabled": True, "expected_pass": False},
            {"vault_available": True, "https_enabled": False, "expected_pass": False},
            {"vault_available": False, "https_enabled": False, "expected_pass": False},
        ]
        
        for scenario in test_scenarios:
            with patch('dotmac_shared.security.secrets_policy.OpenBaoClient') as mock_vault:
                with patch.dict('os.environ', {'REQUIRE_HTTPS': str(scenario["https_enabled"]).lower()}):
                    mock_vault.return_value.health_check = AsyncMock(return_value=scenario["vault_available"])
                    
                    secrets_result = await validator.validate_secrets_management()
                    https_result = await validator.validate_https_enforcement()
                    
                    overall_pass = secrets_result.passed and https_result.passed
                    assert overall_pass == scenario["expected_pass"]


@pytest.mark.asyncio
async def test_security_validator_comprehensive_workflow():
    """Test a comprehensive security validation workflow."""
    # Initialize validator for production environment
    validator = EnvironmentSecurityValidator(
        environment=Environment.PRODUCTION,
        security_level=SecurityLevel.ENHANCED
    )
    
    # Mock all validation methods to return realistic results
    with patch.object(validator, 'validate_secrets_management') as mock_secrets:
        with patch.object(validator, 'validate_csrf_protection') as mock_csrf:
            with patch.object(validator, 'validate_https_enforcement') as mock_https:
                with patch.object(validator, 'validate_authentication_security') as mock_auth:
                    # Setup mock responses
                    mock_secrets.return_value = Mock(passed=True, violations=[], score=100)
                    mock_csrf.return_value = Mock(passed=True, violations=[], score=100)
                    mock_https.return_value = Mock(passed=True, violations=[], score=100)
                    mock_auth.return_value = Mock(passed=True, violations=[], score=90)
                    
                    # Run comprehensive validation
                    result = await validator.validate_comprehensive_security()
                    
                    # Verify results
                    assert isinstance(result, SecurityValidationResult)
                    assert result.environment == Environment.PRODUCTION
                    assert result.compliance_score >= validator.required_compliance_score
                    assert result.is_compliant is True
                    
                    # Generate compliance report
                    report = await validator.generate_compliance_report(result)
                    assert isinstance(report, ComplianceReport)
                    assert report.is_compliant is True
                    
                    # Test audit logging
                    await validator.audit_security_event(
                        "comprehensive_validation_completed",
                        {"score": result.compliance_score, "violations": len(result.violations)}
                    )