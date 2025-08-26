#!/usr/bin/env python3
"""
Container Smoke Tests for DotMac Framework
Validates that all containers can start, respond, and work together properly.
"""

import asyncio
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiohttp
import docker
import yaml


class ContainerSmokeTests:
    """Comprehensive container smoke testing system."""
    
    def __init__(self):
        self.docker_client = None
        self.test_results = {}
        self.containers_started = []
        self.networks_created = []
        self.volumes_created = []
        
    async def setup(self):
        """Initialize Docker client and test environment."""
        try:
            self.docker_client = docker.from_env()
            print("✅ Docker client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Docker client: {e}")
            return False
        
        # Set test environment variables
        self.test_env = {
            'ENVIRONMENT': 'test',
            'POSTGRES_PASSWORD': 'test_password_123',
            'REDIS_PASSWORD': 'test_redis_123',
            'VAULT_TOKEN': 'test_vault_token_123',
            'CLICKHOUSE_PASSWORD': 'test_clickhouse_123',
            'MGMT_SECRET_KEY': 'test-mgmt-secret-key-minimum-32-chars-long',
            'MGMT_JWT_SECRET_KEY': 'test-jwt-secret-key-minimum-32-chars-long',
            'DATABASE_URL': 'postgresql+asyncpg://dotmac_admin:test_password_123@postgres-shared:5432/dotmac_isp',
            'REDIS_URL': 'redis://:test_redis_123@redis-shared:6379/0',
        }
        
        return True
    
    def cleanup(self):
        """Clean up test containers, networks, and volumes."""
        print("\n🧹 Cleaning up test resources...")
        
        # Stop and remove containers
        for container_id in self.containers_started:
            try:
                container = self.docker_client.containers.get(container_id)
                container.stop(timeout=10)
                container.remove()
                print(f"✅ Stopped and removed container: {container_id[:12]}")
            except Exception as e:
                print(f"⚠️ Failed to cleanup container {container_id[:12]}: {e}")
        
        # Remove networks
        for network_name in self.networks_created:
            try:
                network = self.docker_client.networks.get(network_name)
                network.remove()
                print(f"✅ Removed network: {network_name}")
            except Exception as e:
                print(f"⚠️ Failed to cleanup network {network_name}: {e}")
        
        # Remove volumes
        for volume_name in self.volumes_created:
            try:
                volume = self.docker_client.volumes.get(volume_name)
                volume.remove()
                print(f"✅ Removed volume: {volume_name}")
            except Exception as e:
                print(f"⚠️ Failed to cleanup volume {volume_name}: {e}")

    def create_test_network(self) -> str:
        """Create isolated test network."""
        network_name = "dotmac-test-network"
        
        try:
            # Remove existing test network if it exists
            try:
                existing_network = self.docker_client.networks.get(network_name)
                existing_network.remove()
            except docker.errors.NotFound:
                pass
            
            # Create new test network
            network = self.docker_client.networks.create(
                name=network_name,
                driver="bridge"
            )
            self.networks_created.append(network_name)
            print(f"✅ Created test network: {network_name}")
            return network_name
            
        except Exception as e:
            print(f"❌ Failed to create test network: {e}")
            return ""

    def start_database_container(self, network_name: str) -> Optional[str]:
        """Start PostgreSQL test container."""
        container_name = "dotmac-test-postgres"
        
        try:
            # Remove existing container if it exists
            try:
                existing_container = self.docker_client.containers.get(container_name)
                existing_container.stop()
                existing_container.remove()
            except docker.errors.NotFound:
                pass
            
            # Start PostgreSQL container
            container = self.docker_client.containers.run(
                "postgres:15-alpine",
                name=container_name,
                environment={
                    "POSTGRES_USER": "dotmac_admin",
                    "POSTGRES_PASSWORD": self.test_env["POSTGRES_PASSWORD"],
                    "POSTGRES_DB": "dotmac_isp",
                },
                network=network_name,
                ports={"5432/tcp": None},  # Random host port
                healthcheck={
                    "test": ["CMD-SHELL", "pg_isready -U dotmac_admin"],
                    "interval": 10_000_000_000,  # 10 seconds in nanoseconds
                    "timeout": 5_000_000_000,   # 5 seconds in nanoseconds
                    "retries": 5
                },
                detach=True
            )
            
            self.containers_started.append(container.id)
            print(f"✅ Started PostgreSQL container: {container_name}")
            
            # Wait for health check
            return self.wait_for_health_check(container, "PostgreSQL")
            
        except Exception as e:
            print(f"❌ Failed to start PostgreSQL container: {e}")
            return None

    def start_redis_container(self, network_name: str) -> Optional[str]:
        """Start Redis test container."""
        container_name = "dotmac-test-redis"
        
        try:
            # Remove existing container if it exists
            try:
                existing_container = self.docker_client.containers.get(container_name)
                existing_container.stop()
                existing_container.remove()
            except docker.errors.NotFound:
                pass
            
            # Start Redis container
            container = self.docker_client.containers.run(
                "redis:7-alpine",
                name=container_name,
                command=f"redis-server --appendonly yes --requirepass {self.test_env['REDIS_PASSWORD']}",
                network=network_name,
                ports={"6379/tcp": None},  # Random host port
                healthcheck={
                    "test": ["CMD", "redis-cli", "--raw", "incr", "ping"],
                    "interval": 10_000_000_000,
                    "timeout": 5_000_000_000,
                    "retries": 5
                },
                detach=True
            )
            
            self.containers_started.append(container.id)
            print(f"✅ Started Redis container: {container_name}")
            
            return self.wait_for_health_check(container, "Redis")
            
        except Exception as e:
            print(f"❌ Failed to start Redis container: {e}")
            return None

    def wait_for_health_check(self, container, service_name: str, timeout: int = 60) -> Optional[str]:
        """Wait for container health check to pass."""
        print(f"⏳ Waiting for {service_name} health check...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                container.reload()
                health = container.attrs.get('State', {}).get('Health', {})
                status = health.get('Status', 'unknown')
                
                if status == 'healthy':
                    print(f"✅ {service_name} is healthy")
                    return container.id
                elif status == 'unhealthy':
                    print(f"❌ {service_name} health check failed")
                    return None
                
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Error checking {service_name} health: {e}")
                time.sleep(2)
        
        print(f"❌ {service_name} health check timed out")
        return None

    def start_app_container(self, image_name: str, container_name: str, network_name: str, 
                          build_context: str, dockerfile: str, port: int) -> Optional[str]:
        """Start application container (ISP Framework or Management Platform)."""
        
        try:
            # Remove existing container if it exists
            try:
                existing_container = self.docker_client.containers.get(container_name)
                existing_container.stop()
                existing_container.remove()
            except docker.errors.NotFound:
                pass
            
            # Build the image first
            print(f"🔨 Building {image_name}...")
            try:
                image, build_logs = self.docker_client.images.build(
                    path=build_context,
                    dockerfile=dockerfile,
                    tag=f"{image_name}:test",
                    target="development",
                    rm=True
                )
                print(f"✅ Built image: {image_name}:test")
            except Exception as e:
                print(f"❌ Failed to build {image_name}: {e}")
                return None
            
            # Start application container
            container = self.docker_client.containers.run(
                f"{image_name}:test",
                name=container_name,
                environment=self.test_env,
                network=network_name,
                ports={f"{port}/tcp": None},  # Random host port
                healthcheck={
                    "test": ["CMD", "curl", "-f", f"http://localhost:{port}/health"],
                    "interval": 15_000_000_000,  # 15 seconds
                    "timeout": 10_000_000_000,   # 10 seconds
                    "retries": 5,
                    "start_period": 30_000_000_000  # 30 seconds
                },
                detach=True
            )
            
            self.containers_started.append(container.id)
            print(f"✅ Started {container_name}")
            
            return self.wait_for_health_check(container, container_name, timeout=120)
            
        except Exception as e:
            print(f"❌ Failed to start {container_name}: {e}")
            return None

    async def test_http_endpoint(self, container, endpoint: str, expected_status: int = 200) -> bool:
        """Test HTTP endpoint of a running container."""
        try:
            # Get container port mapping
            container.reload()
            ports = container.attrs['NetworkSettings']['Ports']
            
            # Find the mapped port for the service
            mapped_port = None
            for container_port, host_configs in ports.items():
                if host_configs:
                    mapped_port = host_configs[0]['HostPort']
                    break
            
            if not mapped_port:
                print(f"❌ No port mapping found for container {container.name}")
                return False
            
            url = f"http://localhost:{mapped_port}{endpoint}"
            print(f"🌐 Testing endpoint: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == expected_status:
                        print(f"✅ Endpoint {endpoint} responded with status {response.status}")
                        return True
                    else:
                        print(f"❌ Endpoint {endpoint} returned status {response.status}, expected {expected_status}")
                        return False
            
        except Exception as e:
            print(f"❌ Failed to test endpoint {endpoint}: {e}")
            return False

    async def run_smoke_tests(self) -> bool:
        """Run complete smoke test suite."""
        print("🚀 DotMac Framework Container Smoke Tests")
        print("=" * 60)
        
        success = True
        
        try:
            # Setup phase
            print("\n📋 SETUP PHASE")
            print("=" * 30)
            
            if not await self.setup():
                return False
            
            # Create test network
            network_name = self.create_test_network()
            if not network_name:
                return False
            
            # Infrastructure tests
            print("\n🏗️ INFRASTRUCTURE TESTS")
            print("=" * 30)
            
            # Start PostgreSQL
            postgres_id = self.start_database_container(network_name)
            if not postgres_id:
                success = False
            
            # Start Redis
            redis_id = self.start_redis_container(network_name)
            if not redis_id:
                success = False
            
            # Give infrastructure time to stabilize
            if postgres_id and redis_id:
                print("⏳ Letting infrastructure stabilize...")
                await asyncio.sleep(10)
            
            # Application tests
            print("\n🏢 APPLICATION TESTS")
            print("=" * 30)
            
            # Test ISP Framework
            framework_root = Path(__file__).parent.parent
            isp_container_id = self.start_app_container(
                image_name="dotmac-isp-test",
                container_name="dotmac-test-isp-framework",
                network_name=network_name,
                build_context=str(framework_root / "isp-framework"),
                dockerfile="Dockerfile",
                port=8000
            )
            
            if isp_container_id:
                isp_container = self.docker_client.containers.get(isp_container_id)
                # Test ISP Framework endpoints
                await asyncio.sleep(15)  # Give app time to fully start
                isp_health = await self.test_http_endpoint(isp_container, "/health")
                if not isp_health:
                    success = False
            else:
                success = False
            
            # Test Management Platform
            mgmt_container_id = self.start_app_container(
                image_name="dotmac-mgmt-test",
                container_name="dotmac-test-management-platform",
                network_name=network_name,
                build_context=str(framework_root / "management-platform"),
                dockerfile="Dockerfile",
                port=8000
            )
            
            if mgmt_container_id:
                mgmt_container = self.docker_client.containers.get(mgmt_container_id)
                # Test Management Platform endpoints
                await asyncio.sleep(15)  # Give app time to fully start
                mgmt_health = await self.test_http_endpoint(mgmt_container, "/health")
                if not mgmt_health:
                    success = False
            else:
                success = False
            
            # Integration tests
            if isp_container_id and mgmt_container_id:
                print("\n🔗 INTEGRATION TESTS")
                print("=" * 30)
                
                # Test basic API endpoints
                isp_container = self.docker_client.containers.get(isp_container_id)
                mgmt_container = self.docker_client.containers.get(mgmt_container_id)
                
                isp_api_test = await self.test_http_endpoint(isp_container, "/")
                mgmt_api_test = await self.test_http_endpoint(mgmt_container, "/")
                
                if not (isp_api_test and mgmt_api_test):
                    success = False
            
            # Log collection for debugging
            print("\n📋 LOG COLLECTION")
            print("=" * 30)
            
            for container_id in self.containers_started:
                try:
                    container = self.docker_client.containers.get(container_id)
                    logs = container.logs(tail=20, timestamps=True)
                    print(f"\n--- {container.name} logs (last 20 lines) ---")
                    print(logs.decode('utf-8'))
                except Exception as e:
                    print(f"⚠️ Failed to get logs for {container_id[:12]}: {e}")
            
        except Exception as e:
            print(f"❌ Smoke test failed with exception: {e}")
            success = False
        
        finally:
            # Always cleanup
            self.cleanup()
        
        # Print summary
        self.print_summary(success)
        return success

    def print_summary(self, success: bool):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 SMOKE TEST SUMMARY")
        print("=" * 60)
        
        if success:
            print("🎉 ALL SMOKE TESTS PASSED!")
            print("   All containers started successfully and are responding to health checks.")
            print("   The framework is ready for development and deployment.")
        else:
            print("💥 SMOKE TESTS FAILED!")
            print("   Some containers failed to start or health checks failed.")
            print("   Please check the logs above for specific error details.")
        
        print(f"\n📋 Test Results:")
        print(f"   • Containers started: {len(self.containers_started)}")
        print(f"   • Networks created: {len(self.networks_created)}")
        print(f"   • Status: {'PASSED' if success else 'FAILED'}")
        
        print("\n" + "=" * 60)


async def main():
    """Main smoke test entry point."""
    smoke_tests = ContainerSmokeTests()
    success = await smoke_tests.run_smoke_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main()