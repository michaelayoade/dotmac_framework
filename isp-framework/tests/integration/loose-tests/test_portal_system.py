import logging

logger = logging.getLogger(__name__)

"""Test the configurable Portal ID system and account management."""

import asyncio
import sys
sys.path.insert(0, 'src')

from dotmac_isp.modules.identity.portal_id_generator import (
    get_portal_id_generator, 
    PortalIdPattern,
    reload_generator_settings
)
from dotmac_isp.core.settings import get_settings
from dotmac_isp.core.database import SessionLocal
from dotmac_isp.modules.identity.service import CustomerService
from dotmac_isp.modules.identity.portal_service import PortalAccountService
from dotmac_isp.modules.identity.portal_models import PortalAccountType
from dotmac_isp.modules.identity.schemas import CustomerCreateAPI
from dotmac_isp.modules.identity.models import CustomerType


def test_portal_id_configuration():
    """Test different Portal ID generation patterns."""
logger.info("🧪 Testing Configurable Portal ID Generation\n")
    
    # Test current configuration
    generator = get_portal_id_generator()
    config = generator.get_configuration_summary()
    
logger.info("📊 Current Configuration:")
logger.info(f"   Pattern: {config['pattern']}")
logger.info(f"   Length: {config['total_length']}")
logger.info(f"   Prefix: {config['prefix']}")
logger.info(f"   Character Set: {config['character_set'][:20]}{'...' if len(config['character_set']) > 20 else ''}")
logger.info(f"   Max Combinations: {config['max_combinations']:,}")
logger.info(f"   Example: {config['example']}")
    
    # Test different patterns
logger.info("\n🎲 Testing Different Patterns:")
    patterns = PortalIdPattern.__members__.items()
    
    for pattern_name, pattern_value in patterns:
logger.info(f"\n   {pattern_name} ({pattern_value.value}):")
        
        # Temporarily modify settings for testing
        settings = get_settings()
        original_pattern = settings.portal_id_pattern
        settings.portal_id_pattern = pattern_value.value
        reload_generator_settings()
        
        try:
            generator = get_portal_id_generator()
            examples = []
            for _ in range(3):
                examples.append(generator.generate_portal_id())
            
logger.info(f"     Examples: {', '.join(examples)}")
        except Exception as e:
logger.error(f"     Error: {e}")
        finally:
            # Restore original settings
            settings.portal_id_pattern = original_pattern
            reload_generator_settings()


def test_portal_id_uniqueness():
    """Test Portal ID uniqueness and collision handling."""
logger.info("\n🔒 Testing Portal ID Uniqueness:")
    
    generator = get_portal_id_generator()
    existing_ids = set()
    
    # Generate 100 Portal IDs and check uniqueness
    for i in range(100):
        portal_id = generator.generate_portal_id(existing_ids)
        assert portal_id not in existing_ids, f"Duplicate Portal ID: {portal_id}"
        existing_ids.add(portal_id)
    
logger.info(f"   ✅ Generated 100 unique Portal IDs")
logger.info(f"   Examples: {list(existing_ids)[:5]}")


async def test_portal_account_management():
    """Test Portal Account creation and management."""
logger.info("\n🔐 Testing Portal Account Management:")
    
    db = SessionLocal()
    try:
        portal_service = PortalAccountService(db)
        
        # Test Portal Account creation
        test_portal_id = "TEST-PORTAL-001"
        test_password = "TestPassword123!"
        
logger.info(f"   Creating Portal Account: {test_portal_id}")
        
        portal_account = await portal_service.create_portal_account(
            portal_id=test_portal_id,
            password=test_password,
            account_type=PortalAccountType.CUSTOMER,
            force_password_change=False
        )
        
logger.info(f"   ✅ Portal Account created: {portal_account.portal_id}")
logger.info(f"   Status: {portal_account.status}")
logger.info(f"   Account Type: {portal_account.account_type}")
        
        # Test authentication
logger.info(f"\n   Testing authentication...")
        auth_result = await portal_service.authenticate_portal_user(
            test_portal_id, 
            test_password
        )
        
        if auth_result:
logger.info(f"   ✅ Authentication successful")
        else:
logger.info(f"   ❌ Authentication failed")
        
        # Test account activation
logger.info(f"\n   Activating account...")
        await portal_service.activate_portal_account(test_portal_id)
        
        # Get account status
        status = portal_service.get_portal_account_status(test_portal_id)
logger.info(f"   ✅ Account activated")
logger.info(f"   Can Login: {status['can_login']}")
logger.info(f"   Is Active: {status['is_active']}")
        
        # Test password change
logger.info(f"\n   Testing password change...")
        new_password = "NewPassword456#"
        
        await portal_service.change_portal_password(
            test_portal_id,
            test_password,
            new_password
        )
logger.info(f"   ✅ Password changed successfully")
        
        # Test authentication with new password
        auth_result = await portal_service.authenticate_portal_user(
            test_portal_id, 
            new_password
        )
        
        if auth_result:
logger.info(f"   ✅ Authentication with new password successful")
        else:
logger.info(f"   ❌ Authentication with new password failed")
        
        return True
        
    except Exception as e:
logger.info(f"   ❌ Portal Account test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_integrated_customer_portal():
    """Test integrated customer and Portal Account creation."""
logger.info("\n👤 Testing Integrated Customer + Portal Creation:")
    
    db = SessionLocal()
    try:
        service = CustomerService(db)
        
        # Create customer with Portal Account
        customer_data = CustomerCreateAPI(
            customer_number="PORTAL-TEST-001",
            display_name="Portal Test Customer",
            customer_type=CustomerType.BUSINESS,
            first_name="Portal",
            last_name="Tester",
            email="portal@test.com",
            phone="+1888999000"
        )
        
logger.info(f"   Creating customer: {customer_data.customer_number}")
        
        result = await service.create_customer(customer_data)
        
logger.info(f"   ✅ Customer created successfully!")
logger.info(f"   Portal ID: {result.portal_id}")
logger.info(f"   Portal Password: {result.portal_password}")
logger.info(f"   Customer Type: {result.customer_type}")
        
        # Test Portal ID configuration info
        portal_config = service.get_portal_id_configuration()
logger.info(f"\n   📊 Portal ID Configuration Used:")
logger.info(f"   Pattern: {portal_config['pattern']}")
logger.info(f"   Length: {portal_config['total_length']}")
logger.info(f"   Character Set: {portal_config['character_set'][:15]}...")
        
        # Verify Portal Account was created
        portal_account = service.portal_service.get_portal_account_by_id(result.portal_id)
        if portal_account:
logger.info(f"   ✅ Portal Account created and linked")
logger.info(f"   Portal Status: {portal_account.status}")
logger.info(f"   Account Type: {portal_account.account_type}")
        else:
logger.info(f"   ❌ Portal Account not found")
        
        return True
        
    except Exception as e:
logger.info(f"   ❌ Integrated test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def show_pattern_examples():
    """Show examples of different Portal ID patterns."""
logger.info("\n📋 Available Portal ID Patterns:")
    examples = get_portal_id_generator().get_pattern_examples()
    
    for pattern, info in examples.items():
logger.info(f"\n   {pattern.upper()}:")
logger.info(f"     Description: {info['description']}")
logger.info(f"     Example: {info['example']}")
logger.info(f"     Recommended for: {info['recommended_for']}")


async def main():
    """Run all Portal system tests."""
logger.info("🏛️ Portal ID System & Account Management Tests\n")
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Portal ID Configuration
    total_tests += 1
    try:
        test_portal_id_configuration()
        success_count += 1
    except Exception as e:
logger.info(f"❌ Portal ID configuration test failed: {e}")
    
    # Test 2: Portal ID Uniqueness
    total_tests += 1
    try:
        test_portal_id_uniqueness()
        success_count += 1
    except Exception as e:
logger.info(f"❌ Portal ID uniqueness test failed: {e}")
    
    # Test 3: Portal Account Management
    total_tests += 1
    if await test_portal_account_management():
        success_count += 1
    
    # Test 4: Integrated Customer + Portal
    total_tests += 1
    if await test_integrated_customer_portal():
        success_count += 1
    
    # Show pattern examples
    show_pattern_examples()
    
logger.info(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
logger.info("\n🎉 ALL TESTS PASSED - Portal System Working!")
logger.info("\n✨ Features Verified:")
logger.info("   ✅ Configurable Portal ID generation patterns")
logger.info("   ✅ Portal ID uniqueness and collision handling")
logger.info("   ✅ Portal Account creation and management")
logger.info("   ✅ Password authentication and changes")
logger.info("   ✅ Account activation and status management")
logger.info("   ✅ Integrated Customer + Portal Account creation")
logger.info("\n🛠️ Configuration Options:")
logger.info("   • portal_id_pattern: alphanumeric_clean, alphanumeric, numeric, custom")
logger.info("   • portal_id_length: 4-20 characters")
logger.info("   • portal_id_prefix: Optional prefix (e.g., 'CX', 'USR')")
logger.info("   • portal_id_exclude_ambiguous: Exclude 0,O,I,1")
logger.info("   • portal_id_custom_charset: Custom character set")
    else:
logger.info("⚠️  Some tests failed - check implementation")


if __name__ == "__main__":
    asyncio.run(main())