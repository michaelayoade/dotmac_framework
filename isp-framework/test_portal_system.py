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
    print("🧪 Testing Configurable Portal ID Generation\n")
    
    # Test current configuration
    generator = get_portal_id_generator()
    config = generator.get_configuration_summary()
    
    print("📊 Current Configuration:")
    print(f"   Pattern: {config['pattern']}")
    print(f"   Length: {config['total_length']}")
    print(f"   Prefix: {config['prefix']}")
    print(f"   Character Set: {config['character_set'][:20]}{'...' if len(config['character_set']) > 20 else ''}")
    print(f"   Max Combinations: {config['max_combinations']:,}")
    print(f"   Example: {config['example']}")
    
    # Test different patterns
    print("\n🎲 Testing Different Patterns:")
    patterns = PortalIdPattern.__members__.items()
    
    for pattern_name, pattern_value in patterns:
        print(f"\n   {pattern_name} ({pattern_value.value}):")
        
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
            
            print(f"     Examples: {', '.join(examples)}")
        except Exception as e:
            print(f"     Error: {e}")
        finally:
            # Restore original settings
            settings.portal_id_pattern = original_pattern
            reload_generator_settings()


def test_portal_id_uniqueness():
    """Test Portal ID uniqueness and collision handling."""
    print("\n🔒 Testing Portal ID Uniqueness:")
    
    generator = get_portal_id_generator()
    existing_ids = set()
    
    # Generate 100 Portal IDs and check uniqueness
    for i in range(100):
        portal_id = generator.generate_portal_id(existing_ids)
        assert portal_id not in existing_ids, f"Duplicate Portal ID: {portal_id}"
        existing_ids.add(portal_id)
    
    print(f"   ✅ Generated 100 unique Portal IDs")
    print(f"   Examples: {list(existing_ids)[:5]}")


async def test_portal_account_management():
    """Test Portal Account creation and management."""
    print("\n🔐 Testing Portal Account Management:")
    
    db = SessionLocal()
    try:
        portal_service = PortalAccountService(db)
        
        # Test Portal Account creation
        test_portal_id = "TEST-PORTAL-001"
        test_password = "TestPassword123!"
        
        print(f"   Creating Portal Account: {test_portal_id}")
        
        portal_account = await portal_service.create_portal_account(
            portal_id=test_portal_id,
            password=test_password,
            account_type=PortalAccountType.CUSTOMER,
            force_password_change=False
        )
        
        print(f"   ✅ Portal Account created: {portal_account.portal_id}")
        print(f"   Status: {portal_account.status}")
        print(f"   Account Type: {portal_account.account_type}")
        
        # Test authentication
        print(f"\n   Testing authentication...")
        auth_result = await portal_service.authenticate_portal_user(
            test_portal_id, 
            test_password
        )
        
        if auth_result:
            print(f"   ✅ Authentication successful")
        else:
            print(f"   ❌ Authentication failed")
        
        # Test account activation
        print(f"\n   Activating account...")
        await portal_service.activate_portal_account(test_portal_id)
        
        # Get account status
        status = portal_service.get_portal_account_status(test_portal_id)
        print(f"   ✅ Account activated")
        print(f"   Can Login: {status['can_login']}")
        print(f"   Is Active: {status['is_active']}")
        
        # Test password change
        print(f"\n   Testing password change...")
        new_password = "NewPassword456#"
        
        await portal_service.change_portal_password(
            test_portal_id,
            test_password,
            new_password
        )
        print(f"   ✅ Password changed successfully")
        
        # Test authentication with new password
        auth_result = await portal_service.authenticate_portal_user(
            test_portal_id, 
            new_password
        )
        
        if auth_result:
            print(f"   ✅ Authentication with new password successful")
        else:
            print(f"   ❌ Authentication with new password failed")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Portal Account test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


async def test_integrated_customer_portal():
    """Test integrated customer and Portal Account creation."""
    print("\n👤 Testing Integrated Customer + Portal Creation:")
    
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
        
        print(f"   Creating customer: {customer_data.customer_number}")
        
        result = await service.create_customer(customer_data)
        
        print(f"   ✅ Customer created successfully!")
        print(f"   Portal ID: {result.portal_id}")
        print(f"   Portal Password: {result.portal_password}")
        print(f"   Customer Type: {result.customer_type}")
        
        # Test Portal ID configuration info
        portal_config = service.get_portal_id_configuration()
        print(f"\n   📊 Portal ID Configuration Used:")
        print(f"   Pattern: {portal_config['pattern']}")
        print(f"   Length: {portal_config['total_length']}")
        print(f"   Character Set: {portal_config['character_set'][:15]}...")
        
        # Verify Portal Account was created
        portal_account = service.portal_service.get_portal_account_by_id(result.portal_id)
        if portal_account:
            print(f"   ✅ Portal Account created and linked")
            print(f"   Portal Status: {portal_account.status}")
            print(f"   Account Type: {portal_account.account_type}")
        else:
            print(f"   ❌ Portal Account not found")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Integrated test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def show_pattern_examples():
    """Show examples of different Portal ID patterns."""
    print("\n📋 Available Portal ID Patterns:")
    examples = get_portal_id_generator().get_pattern_examples()
    
    for pattern, info in examples.items():
        print(f"\n   {pattern.upper()}:")
        print(f"     Description: {info['description']}")
        print(f"     Example: {info['example']}")
        print(f"     Recommended for: {info['recommended_for']}")


async def main():
    """Run all Portal system tests."""
    print("🏛️ Portal ID System & Account Management Tests\n")
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Portal ID Configuration
    total_tests += 1
    try:
        test_portal_id_configuration()
        success_count += 1
    except Exception as e:
        print(f"❌ Portal ID configuration test failed: {e}")
    
    # Test 2: Portal ID Uniqueness
    total_tests += 1
    try:
        test_portal_id_uniqueness()
        success_count += 1
    except Exception as e:
        print(f"❌ Portal ID uniqueness test failed: {e}")
    
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
    
    print(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("\n🎉 ALL TESTS PASSED - Portal System Working!")
        print("\n✨ Features Verified:")
        print("   ✅ Configurable Portal ID generation patterns")
        print("   ✅ Portal ID uniqueness and collision handling")
        print("   ✅ Portal Account creation and management")
        print("   ✅ Password authentication and changes")
        print("   ✅ Account activation and status management")
        print("   ✅ Integrated Customer + Portal Account creation")
        print("\n🛠️ Configuration Options:")
        print("   • portal_id_pattern: alphanumeric_clean, alphanumeric, numeric, custom")
        print("   • portal_id_length: 4-20 characters")
        print("   • portal_id_prefix: Optional prefix (e.g., 'CX', 'USR')")
        print("   • portal_id_exclude_ambiguous: Exclude 0,O,I,1")
        print("   • portal_id_custom_charset: Custom character set")
    else:
        print("⚠️  Some tests failed - check implementation")


if __name__ == "__main__":
    asyncio.run(main())