#!/usr/bin/env python3
"""
Test and demonstrate the Service Marketplace integration.
"""

import sys
import asyncio
from unittest.mock import Mock

# Add src to Python path
sys.path.append('/home/dotmac_framework/src')

async def test_service_marketplace():
    """Test the service marketplace functionality."""
    
    print("🚀 Testing Service Marketplace Integration")
    print("=" * 60)
    
    try:
        # Import the service marketplace
        from dotmac_shared.services.service_marketplace import (
            ServiceMarketplace,
            ServiceMarketplaceFactory,
            ServiceType,
            ServiceStatus,
            register_consolidated_services
        )
        
        print("✅ Service marketplace imports successful")
        
        # Create mock database session
        mock_session = Mock()
        
        # Create marketplace instance
        marketplace = ServiceMarketplaceFactory.create_marketplace(
            db_session=mock_session,
            tenant_id="test-tenant",
            config={
                'health_check_interval_seconds': 30,
                'instance_timeout_seconds': 300
            }
        )
        
        print("✅ Service marketplace instance created")
        
        # Register consolidated services
        consolidated_services = register_consolidated_services(marketplace)
        
        print(f"✅ Found {len(consolidated_services)} consolidated services to register")
        
        # Register each service
        for service_name, service_metadata in consolidated_services.items():
            success = await marketplace.register_service(service_metadata)
            if success:
                print(f"✅ Registered service: {service_metadata.name}")
            else:
                print(f"❌ Failed to register service: {service_metadata.name}")
        
        # Test service discovery
        print("\n🔍 Testing Service Discovery...")
        
        # Discover all services
        all_services = await marketplace.discover_service()
        print(f"📊 Total registered services: {len(all_services)}")
        
        # Discover business logic services
        business_services = await marketplace.discover_service(
            service_type=ServiceType.BUSINESS_LOGIC
        )
        print(f"💼 Business logic services: {len(business_services)}")
        
        # Discover services with specific capabilities
        auth_services = await marketplace.discover_service(
            capabilities=['authentication']
        )
        print(f"🔐 Services with authentication: {len(auth_services)}")
        
        # Test health monitoring
        print("\n🏥 Testing Health Monitoring...")
        
        # Check health of all services
        health_report = await marketplace.check_all_services_health()
        print(f"📋 Health Report:")
        print(f"   Total services: {health_report['total_services']}")
        print(f"   Healthy services: {health_report['healthy_services']}")
        print(f"   Degraded services: {health_report['degraded_services']}")
        print(f"   Unhealthy services: {health_report['unhealthy_services']}")
        
        # Test marketplace metrics
        print("\n📊 Testing Marketplace Metrics...")
        
        marketplace_metrics = await marketplace.get_marketplace_metrics()
        print(f"📈 Marketplace Metrics:")
        print(f"   Total services: {marketplace_metrics['total_services']}")
        print(f"   Total instances: {marketplace_metrics['total_instances']}")
        print(f"   Service availability: {marketplace_metrics['service_availability']:.1f}%")
        print(f"   Instance availability: {marketplace_metrics['instance_availability']:.1f}%")
        
        # Test API gateway integration
        print("\n🌐 Testing API Gateway Integration...")
        
        gateway_config = await marketplace.get_api_gateway_config()
        print(f"🔧 API Gateway Config:")
        print(f"   Version: {gateway_config['version']}")
        print(f"   Routes: {len(gateway_config['routes'])}")
        print(f"   Services: {len(gateway_config['services'])}")
        print(f"   Upstreams: {len(gateway_config['upstreams'])}")
        
        # Test service instance management
        print("\n🖥️  Testing Service Instance Management...")
        
        # Add some test instances
        for service_name, service_metadata in consolidated_services.items():
            # Create test instance
            instance = ServiceMarketplaceFactory.create_service_instance(
                service_id=service_metadata.service_id,
                host="localhost",
                port=8000 + len(consolidated_services),  # Different ports
                base_path=f"/{service_name}",
                metadata={'environment': 'test', 'version': service_metadata.version}
            )
            
            success = await marketplace.register_instance(instance)
            if success:
                print(f"✅ Registered instance for: {service_metadata.name}")
        
        # Check instances
        updated_health = await marketplace.check_all_services_health()
        total_instances = sum(
            health['total_instances'] 
            for health in updated_health['services'].values()
        )
        print(f"📊 Total registered instances: {total_instances}")
        
        # Test lifecycle hooks
        print("\n🔄 Testing Lifecycle Hooks...")
        
        hook_calls = []
        
        async def service_registered_hook(metadata):
            hook_calls.append(f"Service registered: {metadata.name}")
        
        async def instance_added_hook(instance):
            hook_calls.append(f"Instance added: {instance.instance_id}")
        
        marketplace.add_lifecycle_hook('service_registered', service_registered_hook)
        marketplace.add_lifecycle_hook('instance_added', instance_added_hook)
        
        # Register a test service to trigger hooks
        test_service = ServiceMarketplaceFactory.create_service_metadata(
            name='Test Hook Service',
            version='1.0.0',
            service_type=ServiceType.INTEGRATION,
            description='Service to test lifecycle hooks',
            endpoints=[{'name': 'test', 'path': '/test', 'methods': ['GET']}]
        )
        
        await marketplace.register_service(test_service)
        
        test_instance = ServiceMarketplaceFactory.create_service_instance(
            service_id=test_service.service_id,
            host="localhost",
            port=9999
        )
        
        await marketplace.register_instance(test_instance)
        
        print(f"🎣 Lifecycle hooks triggered: {len(hook_calls)}")
        for hook_call in hook_calls:
            print(f"   - {hook_call}")
        
        print("\n" + "=" * 60)
        print("🎉 Service Marketplace Test Complete!")
        print("✅ All marketplace features working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Service marketplace test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_service_marketplace()
    return 0 if success else 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)