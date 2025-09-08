"""
Security Implementation Validation Script

Comprehensive validation script to test all security components:
- OpenBao secrets policy with environment checks
- Hardened secret factory integration
- Unified CSRF strategy across portals
- Environment-specific security validation

This script can be run standalone to validate the security implementation.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)


def test_imports():
    """Test that all security modules can be imported."""
    logger.info("=== Testing Security Module Imports ===")

    try:
        from .secrets_policy import (
            Environment,
            HardenedSecretsManager,
            SecretsEnvironmentError,
            SecretType,
            create_secrets_manager,
        )

        _ = (
            Environment,
            HardenedSecretsManager,
            SecretsEnvironmentError,
            SecretType,
            create_secrets_manager,
        )

        logger.info("   ✅ Secrets policy module imported successfully")
    except ImportError as e:
        logger.info(f"   ❌ Secrets policy import failed: {e}")
        return False

    try:
        from .hardened_secret_factory import (
            HardenedSecretFactory,
            get_hardened_jwt_secret,
            initialize_hardened_secrets,
        )

        _ = (
            HardenedSecretFactory,
            get_hardened_jwt_secret,
            initialize_hardened_secrets,
        )

        logger.info("   ✅ Hardened secret factory module imported successfully")
    except ImportError as e:
        logger.info(f"   ❌ Hardened secret factory import failed: {e}")
        return False

    try:
        from .unified_csrf_strategy import (
            CSRFConfig,
            CSRFMode,
            UnifiedCSRFMiddleware,
            create_admin_portal_csrf_config,
            create_customer_portal_csrf_config,
        )

        _ = (
            CSRFConfig,
            CSRFMode,
            UnifiedCSRFMiddleware,
            create_admin_portal_csrf_config,
            create_customer_portal_csrf_config,
        )

        logger.info("   ✅ Unified CSRF strategy module imported successfully")
    except ImportError as e:
        logger.info(f"   ❌ Unified CSRF strategy import failed: {e}")
        return False

    try:
        from .environment_security_validator import (
            EnvironmentSecurityValidator,
            SecuritySeverity,
            validate_portal_security,
        )

        _ = (
            EnvironmentSecurityValidator,
            SecuritySeverity,
            validate_portal_security,
        )

        logger.info("   ✅ Environment security validator module imported successfully")
    except ImportError as e:
        logger.info(f"   ❌ Environment security validator import failed: {e}")
        return False

    logger.info("   ✅ All security modules imported successfully\n")
    return True


def test_secrets_policy():
    """Test secrets policy implementation."""
    logger.info("=== Testing Secrets Policy Implementation ===")

    try:
        from .secrets_policy import Environment, HardenedSecretsManager, SecretType

        # Test environment detection
        dev_manager = HardenedSecretsManager(Environment.DEVELOPMENT)
        assert dev_manager.environment == Environment.DEVELOPMENT
        logger.info("   ✅ Environment detection works")

        # Test policy definitions
        policies = dev_manager.DEFAULT_POLICIES
        required_types = [
            SecretType.JWT_SECRET,
            SecretType.DATABASE_CREDENTIAL,
            SecretType.API_KEY,
            SecretType.ENCRYPTION_KEY,
        ]

        for secret_type in required_types:
            assert secret_type in policies
            policy = policies[secret_type]
            assert hasattr(policy, "secret_type")
            assert hasattr(policy, "min_length")

        logger.info("   ✅ Secret type policies defined correctly")

        # Test production enforcement
        try:
            HardenedSecretsManager(Environment.PRODUCTION, vault_client=None)
            logger.info("   ❌ Production should require vault client")
            return False
        except Exception:
            logger.info("   ✅ Production correctly requires vault client")

        logger.info("   ✅ Secrets policy implementation validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Secrets policy test failed: {e}\n")
        return False


async def test_secrets_manager():
    """Test secrets manager functionality."""
    logger.info("=== Testing Secrets Manager Functionality ===")

    try:
        from .secrets_policy import Environment, create_secrets_manager

        # Test development manager creation
        manager = create_secrets_manager(environment="development")
        assert manager.environment == Environment.DEVELOPMENT
        logger.info("   ✅ Development secrets manager created")

        # Test compliance validation
        compliance = await manager.validate_environment_compliance()
        assert isinstance(compliance, dict)
        assert "environment" in compliance
        assert "compliant" in compliance
        logger.info("   ✅ Environment compliance validation works")

        logger.info("   ✅ Secrets manager functionality validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Secrets manager test failed: {e}\n")
        return False


def test_csrf_strategy():
    """Test CSRF strategy implementation."""
    logger.info("=== Testing CSRF Strategy Implementation ===")

    try:
        from .unified_csrf_strategy import (
            CSRFMode,
            CSRFToken,
            CSRFTokenDelivery,
            create_admin_portal_csrf_config,
            create_customer_portal_csrf_config,
            create_management_portal_csrf_config,
            create_reseller_portal_csrf_config,
            create_technician_portal_csrf_config,
        )

        # Test configuration creation for all portals
        portal_configs = [
            ("admin", create_admin_portal_csrf_config()),
            ("customer", create_customer_portal_csrf_config()),
            ("management", create_management_portal_csrf_config()),
            ("reseller", create_reseller_portal_csrf_config()),
            ("technician", create_technician_portal_csrf_config()),
        ]

        for portal_name, config in portal_configs:
            assert config.portal_name == portal_name
            assert isinstance(config.mode, CSRFMode)
            assert isinstance(config.token_delivery, CSRFTokenDelivery)
            assert config.token_lifetime > 0

        logger.info("   ✅ Portal-specific CSRF configurations created")

        # Test token generation and validation
        token_generator = CSRFToken("test_secret_key", lifetime=3600)

        # Generate token
        token = token_generator.generate()
        assert isinstance(token, str)
        assert len(token.split(":")) == 3
        logger.info("   ✅ CSRF token generation works")

        # Validate token
        is_valid = token_generator.validate(token)
        assert is_valid is True
        logger.info("   ✅ CSRF token validation works")

        # Test invalid token
        is_valid = token_generator.validate("invalid:token:format")
        assert is_valid is False
        logger.info("   ✅ Invalid CSRF token rejection works")

        # Test token binding
        session_token = token_generator.generate(session_id="session123", user_id="user456")
        is_valid = token_generator.validate(session_token, session_id="session123", user_id="user456")
        assert is_valid is True
        logger.info("   ✅ CSRF token binding works")

        logger.info("   ✅ CSRF strategy implementation validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ CSRF strategy test failed: {e}\n")
        return False


async def test_environment_validation():
    """Test environment-specific validation."""
    logger.info("=== Testing Environment Security Validation ===")

    try:
        from .environment_security_validator import (
            Environment,
            EnvironmentSecurityValidator,
            SecuritySeverity,
        )

        # Test validator creation for different environments
        environments = [
            Environment.PRODUCTION,
            Environment.STAGING,
            Environment.DEVELOPMENT,
        ]

        for env in environments:
            validator = EnvironmentSecurityValidator(env, portal_name="test")
            assert validator.environment == env

            # Check requirements are environment-appropriate
            reqs = validator.requirements
            if env == Environment.PRODUCTION:
                assert reqs["secrets_management"]["vault_required"] is True
                assert reqs["csrf_protection"]["required"] is True
            elif env == Environment.DEVELOPMENT:
                assert reqs["secrets_management"]["vault_required"] is False
                assert reqs["csrf_protection"]["required"] is False

        logger.info("   ✅ Environment-specific requirements configured correctly")

        # Test validation execution
        dev_validator = EnvironmentSecurityValidator(Environment.DEVELOPMENT)
        result = await dev_validator.validate_comprehensive_security()

        assert hasattr(result, "environment")
        assert hasattr(result, "compliant")
        assert hasattr(result, "violations")
        assert hasattr(result, "security_score")
        assert isinstance(result.security_score, float)
        logger.info("   ✅ Security validation execution works")

        # Test violation severity classification
        assert hasattr(SecuritySeverity, "CRITICAL")
        assert hasattr(SecuritySeverity, "HIGH")
        assert hasattr(SecuritySeverity, "MEDIUM")
        logger.info("   ✅ Security severity classification defined")

        logger.info("   ✅ Environment security validation validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Environment validation test failed: {e}\n")
        return False


def test_hardened_secret_factory():
    """Test hardened secret factory implementation."""
    logger.info("=== Testing Hardened Secret Factory ===")

    try:
        from .hardened_secret_factory import HardenedSecretFactory

        # Test factory creation (singleton pattern)
        factory1 = HardenedSecretFactory()
        factory2 = HardenedSecretFactory()
        assert factory1 is factory2
        logger.info("   ✅ Singleton pattern works")

        # Test factory has required methods
        assert hasattr(factory1, "get_jwt_secret")
        assert hasattr(factory1, "get_database_credentials")
        assert hasattr(factory1, "get_service_api_key")
        assert hasattr(factory1, "get_encryption_key")
        assert hasattr(factory1, "validate_security_compliance")
        logger.info("   ✅ Factory has required methods")

        logger.info("   ✅ Hardened secret factory validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Hardened secret factory test failed: {e}\n")
        return False


async def test_portal_integration():
    """Test portal-specific security integration."""
    logger.info("=== Testing Portal Security Integration ===")

    try:
        from .environment_security_validator import validate_portal_security
        from .secrets_policy import Environment

        # Test all portal types
        portal_types = ["admin", "customer", "management", "reseller", "technician"]

        for portal_type in portal_types:
            result = await validate_portal_security(portal_type=portal_type, environment=Environment.DEVELOPMENT)

            assert result.environment == Environment.DEVELOPMENT
            assert isinstance(result.security_score, float)
            assert result.security_score >= 0.0

        logger.info("   ✅ All portal types can be validated")
        logger.info("   ✅ Portal security integration validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Portal integration test failed: {e}\n")
        return False


def test_configuration_consistency():
    """Test configuration consistency across components."""
    logger.info("=== Testing Configuration Consistency ===")

    try:
        from .secrets_policy import Environment, HardenedSecretsManager
        from .unified_csrf_strategy import (
            create_admin_portal_csrf_config,
            create_customer_portal_csrf_config,
        )

        # Test CSRF configurations are reasonable
        csrf_configs = [
            create_admin_portal_csrf_config(),
            create_customer_portal_csrf_config(),
        ]

        for config in csrf_configs:
            # Token lifetime should be between 30 minutes and 4 hours
            assert 1800 <= config.token_lifetime <= 14400
            # Should have reasonable path configurations
            assert len(config.excluded_paths) > 0
            assert len(config.api_paths) > 0

        logger.info("   ✅ CSRF configurations are consistent")

        # Test secret policies are reasonable
        manager = HardenedSecretsManager(Environment.DEVELOPMENT)
        policies = manager.DEFAULT_POLICIES

        for _secret_type, policy in policies.items():
            # All policies should have minimum length requirements
            assert policy.min_length >= 16
            # Rotation periods should be reasonable (between 1 day and 1 year)
            assert 1 <= policy.rotation_days <= 365

        logger.info("   ✅ Secret policies are consistent")
        logger.info("   ✅ Configuration consistency validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Configuration consistency test failed: {e}\n")
        return False


def test_error_handling():
    """Test error handling across security components."""
    logger.info("=== Testing Error Handling ===")

    try:
        from .secrets_policy import (
            Environment,
            HardenedSecretsManager,
            SecretsEnvironmentError,
        )
        from .unified_csrf_strategy import CSRFToken

        # Test secrets policy error handling
        try:
            HardenedSecretsManager(Environment.PRODUCTION, vault_client=None)
            logger.info("   ❌ Should raise SecretsEnvironmentError")
            return False
        except SecretsEnvironmentError:
            logger.info("   ✅ SecretsEnvironmentError raised correctly")

        # Test CSRF token validation error handling
        token_generator = CSRFToken("test_key")

        # Invalid token formats should return False, not raise exceptions
        invalid_tokens = [
            "",
            "short",
            "only:two:parts",  # Wrong number of parts
            "invalid:format:signature",  # Wrong signature
        ]

        for invalid_token in invalid_tokens:
            is_valid = token_generator.validate(invalid_token)
            assert is_valid is False

        logger.info("   ✅ CSRF token validation handles errors gracefully")
        logger.info("   ✅ Error handling validated\n")
        return True

    except Exception as e:
        logger.info(f"   ❌ Error handling test failed: {e}\n")
        return False


async def main():
    """Run all security validation tests."""
    logger.info("DotMac Security Implementation Validation")
    logger.info("=" * 50)
    logger.info(f"Started at: {datetime.now()}")
    logger.info("")
    # Run all tests
    tests = [
        ("Module Imports", test_imports),
        ("Secrets Policy", test_secrets_policy),
        ("Secrets Manager", test_secrets_manager),
        ("CSRF Strategy", test_csrf_strategy),
        ("Environment Validation", test_environment_validation),
        ("Secret Factory", test_hardened_secret_factory),
        ("Portal Integration", test_portal_integration),
        ("Configuration Consistency", test_configuration_consistency),
        ("Error Handling", test_error_handling),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.info(f"   ❌ {test_name} test failed with exception: {e}\n")
            results.append((test_name, False))

    # Summary
    logger.info("=" * 50)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result:
            logger.info(f"✅ {test_name}")
            passed += 1
        else:
            logger.info(f"❌ {test_name}")
            failed += 1

    logger.info("")
    logger.info(f"Total Tests: {len(results)}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success Rate: {(passed/len(results)*100):.1f}%")

    if failed == 0:
        logger.info("\n🎉 ALL SECURITY VALIDATION TESTS PASSED!")
        logger.info("\nThe security implementation includes:")
        logger.info("• OpenBao/Vault secrets policy with environment checks")
        logger.info("• Hardened secret factory with production enforcement")
        logger.info("• Unified CSRF strategy supporting SSR and API scenarios")
        logger.info("• Environment-specific security validation")
        logger.info("• Portal-specific security configurations")
        logger.info("• Comprehensive error handling and compliance checking")
        logger.info("\nThe security framework provides production-grade protection")
        logger.info("while maintaining development flexibility.")
    else:
        logger.info(f"\n⚠️  {failed} security validation tests failed.")
        logger.info("Please review the failed tests and fix any issues.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
logger = logging.getLogger(__name__)
