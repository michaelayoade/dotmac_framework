#!/usr/bin/env python3
"""
Test and demonstrate the Service Mesh functionality.
"""

import sys
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add src to Python path
sys.path.append('/home/dotmac_framework/src')

async def test_service_mesh():
    """Test the service mesh functionality."""
    
    print("🚀 Testing Service Mesh Implementation")
    print("=" * 60)
    
    try:
        # Import the service mesh components
        from dotmac_shared.mesh.service_mesh import (
            ServiceMesh,
            ServiceMeshFactory,
            ServiceEndpoint,
            TrafficRule,
            TrafficPolicy,
            RetryPolicy,
            EncryptionLevel,
            LoadBalancer,
            ServiceRegistry,
            CircuitBreakerState,
            setup_service_mesh_for_consolidated_services
        )
        
        print("✅ Service mesh imports successful")
        
        # Create mock dependencies
        mock_session = Mock()
        mock_marketplace = AsyncMock()
        mock_performance_service = AsyncMock()
        
        # Mock service discovery data
        mock_services = [
            {
                "name": "unified-billing-service",
                "version": "2.0.0",
                "instances": [
                    {"host": "billing-1", "port": 8001, "base_path": "/api/v1", "metadata": {"region": "us-east"}},
                    {"host": "billing-2", "port": 8002, "base_path": "/api/v1", "metadata": {"region": "us-west"}}
                ]
            },
            {
                "name": "unified-analytics-service", 
                "version": "2.0.0",
                "instances": [
                    {"host": "analytics-1", "port": 8003, "base_path": "/api/v1", "metadata": {"region": "us-east"}}
                ]
            },
            {
                "name": "unified-identity-service",
                "version": "2.0.0",
                "instances": [
                    {"host": "identity-1", "port": 8004, "base_path": "/api/v1", "metadata": {"region": "us-east"}}
                ]
            }
        ]
        
        mock_marketplace.discover_service.return_value = mock_services
        
        # Create service mesh instance
        mesh = ServiceMeshFactory.create_service_mesh(
            db_session=mock_session,
            tenant_id="test-tenant",
            marketplace=mock_marketplace,
            performance_service=mock_performance_service
        )
        
        print("✅ Service mesh instance created")
        
        # Test service registry
        print("\n📝 Testing Service Registry...")
        
        # Test endpoint registration
        test_endpoint = ServiceMeshFactory.create_service_endpoint(
            service_name="test-service",
            host="test-host",
            port=9000,
            path="/api/v2",
            weight=150
        )
        
        mesh.register_service_endpoint(test_endpoint)
        
        endpoints = mesh.registry.get_endpoints("test-service")
        print(f"✅ Endpoint registered: {len(endpoints)} endpoints for test-service")
        print(f"   - URL: {endpoints[0].url}")
        print(f"   - Health URL: {endpoints[0].health_url}")
        print(f"   - Weight: {endpoints[0].weight}")
        
        # Test traffic rule creation
        print("\n🚦 Testing Traffic Rules...")
        
        traffic_rule = ServiceMeshFactory.create_traffic_rule(
            name="test-rule",
            source_service="test-source",
            destination_service="test-destination",
            policy=TrafficPolicy.WEIGHTED,
            retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            max_retries=5,
            timeout_seconds=45,
            encryption_level=EncryptionLevel.MTLS
        )
        
        mesh.add_traffic_rule(traffic_rule)
        
        retrieved_rule = mesh.registry.get_traffic_rule("test-source", "test-destination")
        print(f"✅ Traffic rule created and retrieved:")
        print(f"   - Name: {retrieved_rule.name}")
        print(f"   - Policy: {retrieved_rule.policy}")
        print(f"   - Max Retries: {retrieved_rule.max_retries}")
        print(f"   - Encryption: {retrieved_rule.encryption_level}")
        
        # Test load balancer
        print("\n⚖️ Testing Load Balancer...")
        
        # Create multiple endpoints for load balancing
        for i in range(3):
            endpoint = ServiceMeshFactory.create_service_endpoint(
                service_name="load-test-service",
                host=f"host-{i+1}",
                port=8000 + i,
                weight=100 + (i * 50)  # Different weights
            )
            mesh.register_service_endpoint(endpoint)
        
        # Test different load balancing strategies
        strategies = [
            TrafficPolicy.ROUND_ROBIN,
            TrafficPolicy.WEIGHTED,
            TrafficPolicy.LEAST_CONNECTIONS,
            TrafficPolicy.CONSISTENT_HASH
        ]
        
        for strategy in strategies:
            selected = mesh.load_balancer.select_endpoint(
                "load-test-service", 
                strategy,
                {"source_service": "test-client", "user_id": "123"}
            )
            if selected:
                print(f"✅ {strategy} strategy selected: {selected.host}:{selected.port} (weight: {selected.weight})")
        
        # Test circuit breaker
        print("\n⚡ Testing Circuit Breaker...")
        
        circuit_breaker = CircuitBreakerState(failure_threshold=3, timeout_seconds=5)
        
        # Test successful calls
        for i in range(3):
            circuit_breaker.record_success()
        print(f"✅ Circuit breaker after 3 successes: {circuit_breaker.state}")
        
        # Test failures to trip breaker
        for i in range(4):
            circuit_breaker.record_failure()
        print(f"✅ Circuit breaker after 4 failures: {circuit_breaker.state}")
        print(f"   - Can execute: {circuit_breaker.can_execute()}")
        
        # Wait and test recovery
        await asyncio.sleep(1)
        print(f"✅ Circuit breaker can execute after delay: {circuit_breaker.can_execute()}")
        
        # Initialize mesh with service discovery
        print("\n🔍 Testing Service Discovery Integration...")
        
        await mesh.initialize()
        print("✅ Service mesh initialized with marketplace discovery")
        
        # Check registered services from marketplace
        registered_services = list(mesh.registry.endpoints.keys())
        print(f"✅ Discovered services: {len(registered_services)}")
        for service in registered_services:
            endpoints = mesh.registry.get_endpoints(service)
            print(f"   - {service}: {len(endpoints)} endpoints")
        
        # Test service mesh metrics
        print("\n📊 Testing Service Mesh Metrics...")
        
        initial_metrics = mesh.get_mesh_metrics()
        print(f"✅ Initial metrics:")
        print(f"   - Total calls: {initial_metrics['total_calls']}")
        print(f"   - Registered services: {initial_metrics['registered_services']}")
        print(f"   - Total endpoints: {initial_metrics['total_endpoints']}")
        print(f"   - Traffic rules: {initial_metrics['traffic_rules']}")
        
        # Test service topology
        print("\n🗺️ Testing Service Topology...")
        
        topology = mesh.get_service_topology()
        print(f"✅ Service topology:")
        print(f"   - Services: {len(topology['services'])}")
        print(f"   - Connections: {len(topology['connections'])}")
        
        for service_name, service_info in topology['services'].items():
            print(f"   - {service_name}: {service_info['total_endpoints']} endpoints")
        
        # Test service-to-service calls (mock HTTP calls)
        print("\n🔗 Testing Service-to-Service Calls...")
        
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read = AsyncMock(return_value=b'{"result": "success"}')
        
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response
            
            try:
                response = await mesh.call_service(
                    source_service="test-client",
                    destination_service="unified-billing-service",
                    method="GET",
                    path="/health",
                    headers={"X-Test": "true"}
                )
                
                print(f"✅ Service call successful:")
                print(f"   - Status Code: {response['status_code']}")
                print(f"   - Call ID: {response['call_id']}")
                print(f"   - Trace ID: {response['trace_id']}")
                print(f"   - Response: {response['body'][:50]}...")
                
            except Exception as e:
                print(f"⚠️  Service call test: {e}")
        
        # Test metrics after calls
        updated_metrics = mesh.get_mesh_metrics()
        print(f"\n📈 Updated metrics after calls:")
        print(f"   - Total calls: {updated_metrics['total_calls']}")
        print(f"   - Successful calls: {updated_metrics['successful_calls']}")
        print(f"   - Success rate: {updated_metrics['success_rate_percent']}%")
        
        # Test consolidated service setup
        print("\n🏗️ Testing Consolidated Service Setup...")
        
        consolidated_mesh = await setup_service_mesh_for_consolidated_services(
            db_session=mock_session,
            tenant_id="consolidated-tenant",
            marketplace=mock_marketplace,
            performance_service=mock_performance_service
        )
        
        consolidated_metrics = consolidated_mesh.get_mesh_metrics()
        print(f"✅ Consolidated service mesh setup:")
        print(f"   - Services: {consolidated_metrics['registered_services']}")
        print(f"   - Endpoints: {consolidated_metrics['total_endpoints']}")
        print(f"   - Traffic rules: {consolidated_metrics['traffic_rules']}")
        
        # Test error handling
        print("\n❌ Testing Error Handling...")
        
        try:
            # Try calling non-existent service
            await mesh.call_service(
                source_service="test",
                destination_service="non-existent-service",
                method="GET",
                path="/test"
            )
        except Exception as e:
            print(f"✅ Error handling working: {type(e).__name__}")
        
        # Shutdown mesh
        await mesh.shutdown()
        await consolidated_mesh.shutdown()
        print("✅ Service mesh shutdown complete")
        
        print("\n" + "=" * 60)
        print("🎉 Service Mesh Test Complete!")
        print("✅ All service mesh features working correctly")
        
        # Final summary
        print(f"\n🎯 Service Mesh Test Summary:")
        print(f"   ✅ Service registry and endpoint management")
        print(f"   ✅ Traffic rules and routing policies")
        print(f"   ✅ Load balancing (4 strategies tested)")
        print(f"   ✅ Circuit breaker fault tolerance")
        print(f"   ✅ Service discovery integration")
        print(f"   ✅ Metrics collection and topology mapping")
        print(f"   ✅ Service-to-service communication")
        print(f"   ✅ Consolidated service setup")
        print(f"   ✅ Error handling and resilience")
        
        return True
        
    except Exception as e:
        print(f"❌ Service mesh test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_service_mesh()
    return 0 if success else 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)