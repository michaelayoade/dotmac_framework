#!/usr/bin/env python3
"""
Container Smoke Test Script

This script validates that Docker containers start correctly and pass health checks.
Used in CI/CD pipeline for Gate D validation.
"""

import asyncio
import aiohttp
import docker
import logging
import time
import sys
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContainerSmokeTester:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_container_health(self, container_name: str) -> Tuple[bool, str]:
        """Get health status of a container."""
        try:
            container = self.docker_client.containers.get(container_name)
            state = container.attrs['State']
            
            if 'Health' in state:
                health_status = state['Health']['Status']
                return health_status == 'healthy', health_status
            else:
                # No health check defined, check if running
                return state['Status'] == 'running', state['Status']
                
        except docker.errors.NotFound:
            return False, "not_found"
        except Exception as e:
            return False, f"error: {e}"
    
    def wait_for_container_health(self, container_name: str, timeout: int = 120) -> bool:
        """Wait for container to become healthy."""
        logger.info(f"Waiting for {container_name} to become healthy...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            healthy, status = self.get_container_health(container_name)
            
            if healthy:
                logger.info(f"✅ {container_name} is healthy")
                return True
            elif status in ['not_found', 'exited', 'dead']:
                logger.error(f"❌ {container_name} failed: {status}")
                return False
            
            logger.info(f"⏳ {container_name} status: {status}, waiting...")
            time.sleep(5)
        
        logger.error(f"❌ {container_name} health check timed out after {timeout}s")
        return False
    
    async def test_http_endpoint(self, url: str, expected_status: int = 200) -> bool:
        """Test HTTP endpoint availability."""
        try:
            async with self.session.get(url) as response:
                if response.status == expected_status:
                    logger.info(f"✅ HTTP endpoint OK: {url} -> {response.status}")
                    return True
                else:
                    logger.error(f"❌ HTTP endpoint failed: {url} -> {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ HTTP endpoint error: {url} -> {e}")
            return False
    
    async def test_health_endpoints(self) -> bool:
        """Test health endpoints for all services."""
        endpoints = [
            ("ISP Framework Health", "http://localhost:8001/health"),
            ("Management Platform Health", "http://localhost:8000/health"),
            ("SignOz Frontend", "http://localhost:3301", 200),
            ("SignOz Query Service", "http://localhost:8080/api/v1/version"),
        ]
        
        results = []
        for name, url, *expected in endpoints:
            expected_status = expected[0] if expected else 200
            logger.info(f"Testing {name}...")
            result = await self.test_http_endpoint(url, expected_status)
            results.append((name, result))
        
        return all(result for _, result in results)
    
    def test_container_startup(self, containers: List[str]) -> bool:
        """Test that containers start and become healthy."""
        logger.info("🐳 Testing container startup...")
        
        results = []
        for container in containers:
            healthy = self.wait_for_container_health(container, timeout=180)
            results.append((container, healthy))
        
        return all(result for _, result in results)
    
    async def test_database_connectivity(self) -> bool:
        """Test database connectivity through container."""
        try:
            # Test PostgreSQL connectivity via container exec
            postgres_container = self.docker_client.containers.get("dotmac-postgres-shared")
            
            # Run pg_isready command
            result = postgres_container.exec_run(
                ["pg_isready", "-U", "dotmac_admin", "-d", "dotmac_isp"]
            )
            
            if result.exit_code == 0:
                logger.info("✅ PostgreSQL connectivity OK")
                return True
            else:
                logger.error(f"❌ PostgreSQL connectivity failed: {result.output.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database connectivity test error: {e}")
            return False
    
    async def test_redis_connectivity(self) -> bool:
        """Test Redis connectivity through container."""
        try:
            redis_container = self.docker_client.containers.get("dotmac-redis-shared")
            
            # Get Redis password from environment
            redis_password = redis_container.attrs['Config']['Env']
            redis_pass = None
            for env in redis_password:
                if env.startswith('requirepass'):
                    redis_pass = env.split('requirepass ')[1]
                    break
            
            # Run Redis ping
            if redis_pass:
                result = redis_container.exec_run(
                    ["redis-cli", "-a", redis_pass, "ping"]
                )
            else:
                result = redis_container.exec_run(["redis-cli", "ping"])
            
            if result.exit_code == 0 and b"PONG" in result.output:
                logger.info("✅ Redis connectivity OK")
                return True
            else:
                logger.error(f"❌ Redis connectivity failed: {result.output.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Redis connectivity test error: {e}")
            return False
    
    def get_container_logs(self, container_name: str, lines: int = 50) -> str:
        """Get recent logs from container."""
        try:
            container = self.docker_client.containers.get(container_name)
            logs = container.logs(tail=lines).decode('utf-8', errors='ignore')
            return logs
        except Exception as e:
            return f"Error getting logs: {e}"
    
    async def run_comprehensive_tests(self) -> bool:
        """Run all smoke tests."""
        logger.info("🔥 Starting comprehensive container smoke tests...")
        
        # Define containers to test (in dependency order)
        infrastructure_containers = [
            "dotmac-postgres-shared",
            "dotmac-redis-shared", 
            "dotmac-openbao-shared",
            "dotmac-clickhouse",
            "dotmac-signoz-collector",
            "dotmac-signoz-query",
            "dotmac-signoz-frontend"
        ]
        
        application_containers = [
            "dotmac-isp-framework",
            "dotmac-management-platform"
        ]
        
        all_tests = [
            ("Infrastructure Container Health", 
             lambda: self.test_container_startup(infrastructure_containers)),
            ("Application Container Health", 
             lambda: self.test_container_startup(application_containers)),
            ("Database Connectivity", self.test_database_connectivity),
            ("Redis Connectivity", self.test_redis_connectivity),
            ("HTTP Health Endpoints", self.test_health_endpoints),
        ]
        
        results = []
        for test_name, test_func in all_tests:
            logger.info(f"\n--- Running {test_name} ---")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                results.append((test_name, result))
                
                if not result:
                    # Log container status for failed tests
                    logger.info("Container status after failure:")
                    for container in infrastructure_containers + application_containers:
                        healthy, status = self.get_container_health(container)
                        logger.info(f"  {container}: {status}")
                        
            except Exception as e:
                logger.error(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info("\n📊 Container Smoke Test Summary:")
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"  {status}: {test_name}")
            if not passed:
                all_passed = False
        
        if all_passed:
            logger.info("🎉 All container smoke tests passed!")
        else:
            logger.error("💥 Some container smoke tests failed!")
            
            # Print logs for failed containers
            logger.info("\n📋 Recent logs from failed containers:")
            for container in infrastructure_containers + application_containers:
                healthy, status = self.get_container_health(container)
                if not healthy:
                    logger.info(f"\n--- Logs for {container} ---")
                    logs = self.get_container_logs(container)
                    logger.info(logs[-1000:])  # Last 1000 chars
        
        return all_passed

async def main():
    """Main entry point."""
    logger.info("🚀 Starting container smoke tests...")
    
    async with ContainerSmokeTester() as tester:
        success = await tester.run_comprehensive_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())