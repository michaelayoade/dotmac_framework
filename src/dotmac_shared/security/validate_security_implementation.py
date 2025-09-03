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
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# Add the current directory to sys.path for imports
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)

def test_imports():
    """Test that all security modules can be imported."""
    print("=== Testing Security Module Imports ===")
    
    try:
        from secrets_policy import (
            HardenedSecretsManager, Environment, SecretType, 
            create_secrets_manager, SecretsEnvironmentError
        )
        print("   ✅ Secrets policy module imported successfully")
    except ImportError as e:
        print(f"   ❌ Secrets policy import failed: {e}")
        return False
    
    try:
        from hardened_secret_factory import (
            HardenedSecretFactory, get_hardened_jwt_secret,
            initialize_hardened_secrets
        )
        print("   ✅ Hardened secret factory module imported successfully")
    except ImportError as e:
        print(f"   ❌ Hardened secret factory import failed: {e}")
        return False
    
    try:
        from unified_csrf_strategy import (
            UnifiedCSRFMiddleware, CSRFConfig, CSRFMode,
            create_admin_portal_csrf_config, create_customer_portal_csrf_config
        )
        print("   ✅ Unified CSRF strategy module imported successfully")
    except ImportError as e:
        print(f"   ❌ Unified CSRF strategy import failed: {e}")
        return False
    
    try:
        from environment_security_validator import (
            EnvironmentSecurityValidator, SecuritySeverity,
            validate_portal_security
        )
        print("   ✅ Environment security validator module imported successfully")
    except ImportError as e:
        print(f"   ❌ Environment security validator import failed: {e}")
        return False
    
    print("   ✅ All security modules imported successfully\n")
    return True


def test_secrets_policy():
    """Test secrets policy implementation."""
    print("=== Testing Secrets Policy Implementation ===")
    
    try:
        from secrets_policy import (
            HardenedSecretsManager, Environment, SecretType
        )
        
        # Test environment detection
        dev_manager = HardenedSecretsManager(Environment.DEVELOPMENT)
        assert dev_manager.environment == Environment.DEVELOPMENT
        print("   ✅ Environment detection works")
        
        # Test policy definitions
        policies = dev_manager.DEFAULT_POLICIES
        required_types = [
            SecretType.JWT_SECRET,
            SecretType.DATABASE_CREDENTIAL,
            SecretType.API_KEY,
            SecretType.ENCRYPTION_KEY
        ]
        
        for secret_type in required_types:
            assert secret_type in policies
            policy = policies[secret_type]
            assert hasattr(policy, 'secret_type')
            assert hasattr(policy, 'min_length')
        
        print("   ✅ Secret type policies defined correctly")
        
        # Test production enforcement
        try:
            prod_manager = HardenedSecretsManager(Environment.PRODUCTION, vault_client=None)
            print("   ❌ Production should require vault client")
            return False
        except Exception:
            print("   ✅ Production correctly requires vault client")
        
        print("   ✅ Secrets policy implementation validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Secrets policy test failed: {e}\n")
        return False


async def test_secrets_manager():
    """Test secrets manager functionality."""
    print("=== Testing Secrets Manager Functionality ===")
    
    try:
        from secrets_policy import create_secrets_manager, Environment
        
        # Test development manager creation
        manager = create_secrets_manager(environment="development")
        assert manager.environment == Environment.DEVELOPMENT
        print("   ✅ Development secrets manager created")
        
        # Test compliance validation
        compliance = await manager.validate_environment_compliance()
        assert isinstance(compliance, dict)
        assert "environment" in compliance
        assert "compliant" in compliance
        print("   ✅ Environment compliance validation works")
        
        print("   ✅ Secrets manager functionality validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Secrets manager test failed: {e}\n")
        return False


def test_csrf_strategy():
    """Test CSRF strategy implementation."""
    print("=== Testing CSRF Strategy Implementation ===")
    
    try:
        from unified_csrf_strategy import (
            CSRFConfig, CSRFMode, CSRFTokenDelivery, CSRFToken,
            create_admin_portal_csrf_config, create_customer_portal_csrf_config,
            create_management_portal_csrf_config, create_reseller_portal_csrf_config,
            create_technician_portal_csrf_config
        )
        
        # Test configuration creation for all portals
        portal_configs = [
            ("admin", create_admin_portal_csrf_config()),
            ("customer", create_customer_portal_csrf_config()),
            ("management", create_management_portal_csrf_config()),
            ("reseller", create_reseller_portal_csrf_config()),
            ("technician", create_technician_portal_csrf_config())
        ]
        
        for portal_name, config in portal_configs:
            assert config.portal_name == portal_name
            assert isinstance(config.mode, CSRFMode)
            assert isinstance(config.token_delivery, CSRFTokenDelivery)
            assert config.token_lifetime > 0
        
        print("   ✅ Portal-specific CSRF configurations created")
        
        # Test token generation and validation
        token_generator = CSRFToken("test_secret_key", lifetime=3600)
        
        # Generate token
        token = token_generator.generate()
        assert isinstance(token, str)
        assert len(token.split(":")) == 3
        print("   ✅ CSRF token generation works")
        
        # Validate token
        is_valid = token_generator.validate(token)
        assert is_valid is True
        print("   ✅ CSRF token validation works")
        
        # Test invalid token
        is_valid = token_generator.validate("invalid:token:format")
        assert is_valid is False
        print("   ✅ Invalid CSRF token rejection works")
        
        # Test token binding
        session_token = token_generator.generate(session_id="session123", user_id="user456")
        is_valid = token_generator.validate(
            session_token, 
            session_id="session123", 
            user_id="user456"
        )
        assert is_valid is True
        print("   ✅ CSRF token binding works")
        
        print("   ✅ CSRF strategy implementation validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ CSRF strategy test failed: {e}\n")
        return False


async def test_environment_validation():
    """Test environment-specific validation."""
    print("=== Testing Environment Security Validation ===")
    
    try:
        from environment_security_validator import (
            EnvironmentSecurityValidator, Environment, SecuritySeverity
        )
        
        # Test validator creation for different environments
        environments = [Environment.PRODUCTION, Environment.STAGING, Environment.DEVELOPMENT]
        
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
        
        print("   ✅ Environment-specific requirements configured correctly")
        
        # Test validation execution
        dev_validator = EnvironmentSecurityValidator(Environment.DEVELOPMENT)
        result = await dev_validator.validate_comprehensive_security()
        
        assert hasattr(result, 'environment')
        assert hasattr(result, 'compliant')
        assert hasattr(result, 'violations')
        assert hasattr(result, 'security_score')
        assert isinstance(result.security_score, float)
        print("   ✅ Security validation execution works")
        
        # Test violation severity classification
        assert hasattr(SecuritySeverity, 'CRITICAL')
        assert hasattr(SecuritySeverity, 'HIGH')
        assert hasattr(SecuritySeverity, 'MEDIUM')
        print("   ✅ Security severity classification defined")
        
        print("   ✅ Environment security validation validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Environment validation test failed: {e}\n")
        return False


def test_hardened_secret_factory():
    """Test hardened secret factory implementation."""
    print("=== Testing Hardened Secret Factory ===")
    
    try:
        from hardened_secret_factory import HardenedSecretFactory
        
        # Test factory creation (singleton pattern)
        factory1 = HardenedSecretFactory()
        factory2 = HardenedSecretFactory()
        assert factory1 is factory2
        print("   ✅ Singleton pattern works")
        
        # Test factory has required methods
        assert hasattr(factory1, 'get_jwt_secret')
        assert hasattr(factory1, 'get_database_credentials')
        assert hasattr(factory1, 'get_service_api_key')
        assert hasattr(factory1, 'get_encryption_key')
        assert hasattr(factory1, 'validate_security_compliance')
        print("   ✅ Factory has required methods")
        
        print("   ✅ Hardened secret factory validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Hardened secret factory test failed: {e}\n")
        return False


async def test_portal_integration():
    """Test portal-specific security integration."""
    print("=== Testing Portal Security Integration ===")
    
    try:
        from environment_security_validator import validate_portal_security
        from secrets_policy import Environment
        
        # Test all portal types
        portal_types = ["admin", "customer", "management", "reseller", "technician"]
        
        for portal_type in portal_types:
            result = await validate_portal_security(
                portal_type=portal_type,
                environment=Environment.DEVELOPMENT
            )
            
            assert result.environment == Environment.DEVELOPMENT
            assert isinstance(result.security_score, float)
            assert result.security_score >= 0.0
        
        print("   ✅ All portal types can be validated")
        print("   ✅ Portal security integration validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Portal integration test failed: {e}\n")
        return False


def test_configuration_consistency():
    """Test configuration consistency across components."""
    print("=== Testing Configuration Consistency ===")
    
    try:
        from unified_csrf_strategy import (
            create_admin_portal_csrf_config,
            create_customer_portal_csrf_config
        )
        from secrets_policy import SecretType, HardenedSecretsManager, Environment
        
        # Test CSRF configurations are reasonable
        csrf_configs = [
            create_admin_portal_csrf_config(),
            create_customer_portal_csrf_config()
        ]
        
        for config in csrf_configs:
            # Token lifetime should be between 30 minutes and 4 hours
            assert 1800 <= config.token_lifetime <= 14400
            # Should have reasonable path configurations
            assert len(config.excluded_paths) > 0
            assert len(config.api_paths) > 0
        
        print("   ✅ CSRF configurations are consistent")
        
        # Test secret policies are reasonable
        manager = HardenedSecretsManager(Environment.DEVELOPMENT)
        policies = manager.DEFAULT_POLICIES
        
        for secret_type, policy in policies.items():
            # All policies should have minimum length requirements
            assert policy.min_length >= 16
            # Rotation periods should be reasonable (between 1 day and 1 year)
            assert 1 <= policy.rotation_days <= 365
        
        print("   ✅ Secret policies are consistent")
        print("   ✅ Configuration consistency validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration consistency test failed: {e}\n")
        return False


def test_error_handling():
    """Test error handling across security components."""
    print("=== Testing Error Handling ===")
    
    try:
        from secrets_policy import SecretsEnvironmentError, HardenedSecretsManager, Environment
        from unified_csrf_strategy import CSRFToken
        
        # Test secrets policy error handling
        try:
            HardenedSecretsManager(Environment.PRODUCTION, vault_client=None)
            print("   ❌ Should raise SecretsEnvironmentError")
            return False
        except SecretsEnvironmentError:
            print("   ✅ SecretsEnvironmentError raised correctly")
        
        # Test CSRF token validation error handling
        token_generator = CSRFToken("test_key")
        
        # Invalid token formats should return False, not raise exceptions
        invalid_tokens = [
            "",
            "short",
            "only:two:parts",  # Wrong number of parts
            "invalid:format:signature"  # Wrong signature
        ]
        
        for invalid_token in invalid_tokens:
            is_valid = token_generator.validate(invalid_token)
            assert is_valid is False
        
        print("   ✅ CSRF token validation handles errors gracefully")
        print("   ✅ Error handling validated\n")
        return True
        
    except Exception as e:
        print(f"   ❌ Error handling test failed: {e}\n")
        return False


async def main():
    """Run all security validation tests."""
    print("DotMac Security Implementation Validation")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print()
    
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
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ {test_name} test failed with exception: {e}\n")
            results.append((test_name, False))
    
    # Summary
    print("=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        if result:
            print(f"✅ {test_name}")
            passed += 1
        else:
            print(f"❌ {test_name}")
            failed += 1
    
    print()
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL SECURITY VALIDATION TESTS PASSED!")
        print("\nThe security implementation includes:")
        print("• OpenBao/Vault secrets policy with environment checks")
        print("• Hardened secret factory with production enforcement")
        print("• Unified CSRF strategy supporting SSR and API scenarios")
        print("• Environment-specific security validation")
        print("• Portal-specific security configurations")
        print("• Comprehensive error handling and compliance checking")
        print("\nThe security framework provides production-grade protection")
        print("while maintaining development flexibility.")
    else:
        print(f"\n⚠️  {failed} security validation tests failed.")
        print("Please review the failed tests and fix any issues.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())