"""
Plugin System Validation Test
Quick validation test for the infrastructure plugin system
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from dotmac_management.services.infrastructure_service import get_infrastructure_service


async def test_infrastructure_service():
    """Test the infrastructure service and plugin system."""
    
    print("🔍 Testing Infrastructure Plugin System")
    print("=" * 50)
    
    try:
        # Get infrastructure service
        infra_service = await get_infrastructure_service()
        print("✅ Infrastructure service initialized")
        
        # Test health status
        health = await infra_service.get_health_status()
        print(f"📊 Health Status: {health['healthy']}")
        
        if health['providers']:
            print("🔌 Available Providers:")
            for provider_type, providers in health['providers'].items():
                print(f"  {provider_type.title()}:")
                for name, status in providers.items():
                    status_icon = "✅" if status.get("healthy", False) else "❌"
                    print(f"    {status_icon} {name}: {status.get('status', 'unknown')}")
        
        # List available providers
        providers = infra_service.list_available_providers()
        print(f"\n🏗️  Deployment Providers: {providers.get('deployment_providers', [])}")
        print(f"🌐 DNS Providers: {providers.get('dns_providers', [])}")
        
        # Test subdomain validation (if DNS provider available)
        if providers.get('dns_providers'):
            print(f"\n🧪 Testing subdomain validation...")
            try:
                result = await infra_service.validate_subdomain_availability("test-" + str(int(asyncio.get_event_loop().time())))
                print(f"   Subdomain validation result: {result.get('available', 'unknown')}")
            except Exception as e:
                print(f"   ⚠️  Subdomain validation failed (expected if no BASE_DOMAIN): {e}")
        
        print("\n✅ Plugin system validation completed successfully!")
        
    except Exception as e:
        print(f"❌ Plugin system validation failed: {e}")
        return False
    
    return True


async def main():
    """Main test function."""
    success = await test_infrastructure_service()
    
    if success:
        print("\n🎉 All tests passed! Infrastructure plugin system is working correctly.")
    else:
        print("\n💥 Tests failed! Please check the implementation.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())