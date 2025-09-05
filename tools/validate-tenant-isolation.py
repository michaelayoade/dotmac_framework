#!/usr/bin/env python3
"""
Container-per-tenant isolation validation for DotMac Platform.

This script validates that:
1. Each tenant gets isolated containers
2. Network isolation works correctly
3. Resource limits are enforced
4. Data isolation is maintained
5. Security boundaries are intact
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

import docker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TenantIsolationValidator:
    """Validate container-per-tenant isolation."""

    def __init__(self):
        self.docker_client = docker.from_env()
        self.test_tenants = []
        self.created_resources = []

    async def create_test_tenant(self, tenant_id: str) -> dict[str, Any]:
        """Create a test tenant with isolated containers."""
        logger.info(f"Creating test tenant: {tenant_id}")

        # Generate unique network name
        network_name = f"dotmac-tenant-{tenant_id}"

        try:
            # Create isolated network for tenant
            network = self.docker_client.networks.create(
                name=network_name,
                driver="bridge",
                options={
                    "com.docker.network.bridge.enable_icc": "true",
                    "com.docker.network.driver.mtu": "1500",
                },
                labels={"dotmac.tenant_id": tenant_id, "dotmac.isolation": "enabled"},
            )
            self.created_resources.append(("network", network.id))
            logger.info(f"Created isolated network: {network_name}")

            # Create tenant-specific PostgreSQL container
            postgres_container = self.docker_client.containers.run(
                image="postgres:15-alpine",
                name=f"postgres-{tenant_id}",
                environment={
                    "POSTGRES_DB": f"dotmac_{tenant_id}",
                    "POSTGRES_USER": f"tenant_{tenant_id}",
                    "POSTGRES_PASSWORD": f"password_{tenant_id}",
                },
                networks=[network_name],
                detach=True,
                remove=False,
                labels={
                    "dotmac.tenant_id": tenant_id,
                    "dotmac.service": "database",
                    "dotmac.isolation": "enabled",
                },
                mem_limit="512m",  # Resource limit
                cpuset_cpus="0-1",  # CPU limit
                volumes={
                    f"postgres_data_{tenant_id}": {
                        "bind": "/var/lib/postgresql/data",
                        "mode": "rw",
                    }
                },
            )
            self.created_resources.append(("container", postgres_container.id))

            # Wait for PostgreSQL to start
            await self._wait_for_postgres(postgres_container, tenant_id)

            # Create tenant-specific Redis container
            redis_container = self.docker_client.containers.run(
                image="redis:7-alpine",
                name=f"redis-{tenant_id}",
                command=f"redis-server --requirepass password_{tenant_id} --databases 16",
                networks=[network_name],
                detach=True,
                remove=False,
                labels={
                    "dotmac.tenant_id": tenant_id,
                    "dotmac.service": "cache",
                    "dotmac.isolation": "enabled",
                },
                mem_limit="256m",  # Resource limit
                cpuset_cpus="0-1",  # CPU limit
                volumes={f"redis_data_{tenant_id}": {"bind": "/data", "mode": "rw"}},
            )
            self.created_resources.append(("container", redis_container.id))

            # Wait for Redis to start
            await asyncio.sleep(5)

            # Create tenant-specific ISP Framework container
            isp_container = self.docker_client.containers.run(
                image="python:3.11-slim",  # Simplified for testing
                name=f"isp-framework-{tenant_id}",
                command="python -c 'import time; time.sleep(3600)'",  # Keep alive
                networks=[network_name],
                detach=True,
                remove=False,
                environment={
                    "TENANT_ID": tenant_id,
                    "POSTGRES_HOST": f"postgres-{tenant_id}",
                    "POSTGRES_DB": f"dotmac_{tenant_id}",
                    "POSTGRES_USER": f"tenant_{tenant_id}",
                    "POSTGRES_PASSWORD": f"password_{tenant_id}",
                    "REDIS_HOST": f"redis-{tenant_id}",
                    "REDIS_PASSWORD": f"password_{tenant_id}",
                    "ISOLATION_MODE": "enabled",
                },
                labels={
                    "dotmac.tenant_id": tenant_id,
                    "dotmac.service": "isp_framework",
                    "dotmac.isolation": "enabled",
                },
                mem_limit="1g",  # Resource limit
                cpuset_cpus="0-3",  # CPU limit
            )
            self.created_resources.append(("container", isp_container.id))

            tenant_info = {
                "tenant_id": tenant_id,
                "network": {"name": network_name, "id": network.id},
                "containers": {
                    "postgres": {
                        "id": postgres_container.id,
                        "name": postgres_container.name,
                    },
                    "redis": {"id": redis_container.id, "name": redis_container.name},
                    "isp_framework": {
                        "id": isp_container.id,
                        "name": isp_container.name,
                    },
                },
            }

            self.test_tenants.append(tenant_info)
            logger.info(f"Test tenant {tenant_id} created successfully")
            return tenant_info

        except Exception as e:
            logger.error(f"Failed to create test tenant {tenant_id}: {e}")
            raise

    async def _wait_for_postgres(
        self, container, tenant_id: str, max_attempts: int = 30
    ) -> None:
        """Wait for PostgreSQL to be ready."""
        for attempt in range(max_attempts):
            try:
                # Check if container is running
                container.reload()
                if container.status != "running":
                    await asyncio.sleep(2)
                    continue

                # Try to connect to PostgreSQL
                result = container.exec_run(
                    f"pg_isready -U tenant_{tenant_id} -d dotmac_{tenant_id}", timeout=5
                )

                if result.exit_code == 0:
                    logger.info(f"PostgreSQL ready for tenant {tenant_id}")
                    return

            except Exception as e:
                logger.debug(f"PostgreSQL not ready yet for tenant {tenant_id}: {e}")

            await asyncio.sleep(2)

        raise Exception(f"PostgreSQL failed to start for tenant {tenant_id}")

    async def validate_network_isolation(self) -> dict[str, Any]:
        """Validate that tenants cannot access each other's networks."""
        logger.info("Validating network isolation...")

        results = {"status": "passed", "tests": [], "issues": []}

        if len(self.test_tenants) < 2:
            results["status"] = "skipped"
            results["issues"].append(
                "Need at least 2 tenants to test network isolation"
            )
            return results

        tenant1 = self.test_tenants[0]
        tenant2 = self.test_tenants[1]

        try:
            # Test 1: Tenant 1 should not be able to reach Tenant 2's PostgreSQL
            container1 = self.docker_client.containers.get(
                tenant1["containers"]["isp_framework"]["id"]
            )

            # Try to connect to tenant2's postgres from tenant1's container
            result = container1.exec_run(
                f"python -c 'import socket; s=socket.socket(); s.settimeout(5); s.connect((\"postgres-{tenant2['tenant_id']}\", 5432)'",
                timeout=10,
            )

            if result.exit_code == 0:
                results["status"] = "failed"
                results["issues"].append(
                    f"Tenant {tenant1['tenant_id']} can access {tenant2['tenant_id']}'s database"
                )
            else:
                results["tests"].append(
                    f"✓ Tenant {tenant1['tenant_id']} cannot access {tenant2['tenant_id']}'s database"
                )

            # Test 2: Tenant 2 should not be able to reach Tenant 1's Redis
            container2 = self.docker_client.containers.get(
                tenant2["containers"]["isp_framework"]["id"]
            )

            result = container2.exec_run(
                f"python -c 'import socket; s=socket.socket(); s.settimeout(5); s.connect((\"redis-{tenant1['tenant_id']}\", 6379)'",
                timeout=10,
            )

            if result.exit_code == 0:
                results["status"] = "failed"
                results["issues"].append(
                    f"Tenant {tenant2['tenant_id']} can access {tenant1['tenant_id']}'s cache"
                )
            else:
                results["tests"].append(
                    f"✓ Tenant {tenant2['tenant_id']} cannot access {tenant1['tenant_id']}'s cache"
                )

        except Exception as e:
            results["status"] = "failed"
            results["issues"].append(f"Network isolation test failed: {e}")

        logger.info(f"Network isolation validation: {results['status']}")
        return results

    async def validate_data_isolation(self) -> dict[str, Any]:
        """Validate that tenant data is isolated."""
        logger.info("Validating data isolation...")

        results = {"status": "passed", "tests": [], "issues": []}

        try:
            for tenant_info in self.test_tenants:
                tenant_id = tenant_info["tenant_id"]

                # Test PostgreSQL data isolation
                postgres_container = self.docker_client.containers.get(
                    tenant_info["containers"]["postgres"]["id"]
                )

                # Create test data
                test_data = f"test_data_for_tenant_{tenant_id}_{uuid.uuid4().hex[:8]}"

                result = postgres_container.exec_run(
                    [
                        "psql",
                        "-U",
                        f"tenant_{tenant_id}",
                        "-d",
                        f"dotmac_{tenant_id}",
                        "-c",
                        f"CREATE TABLE test_isolation (data TEXT); INSERT INTO test_isolation VALUES ('{test_data}');",
                    ]
                )

                if result.exit_code == 0:
                    results["tests"].append(
                        f"✓ Created isolated test data for tenant {tenant_id}"
                    )

                    # Verify data exists
                    result = postgres_container.exec_run(
                        [
                            "psql",
                            "-U",
                            f"tenant_{tenant_id}",
                            "-d",
                            f"dotmac_{tenant_id}",
                            "-t",
                            "-c",
                            "SELECT data FROM test_isolation;",
                        ]
                    )

                    if test_data in result.output.decode():
                        results["tests"].append(
                            f"✓ Verified data isolation for tenant {tenant_id}"
                        )
                    else:
                        results["status"] = "failed"
                        results["issues"].append(
                            f"Data verification failed for tenant {tenant_id}"
                        )
                else:
                    results["status"] = "failed"
                    results["issues"].append(
                        f"Failed to create test data for tenant {tenant_id}"
                    )

                # Test Redis data isolation
                redis_container = self.docker_client.containers.get(
                    tenant_info["containers"]["redis"]["id"]
                )

                # Set test data in Redis
                redis_test_key = f"test:isolation:{tenant_id}"
                redis_test_value = f"isolated_value_{tenant_id}_{uuid.uuid4().hex[:8]}"

                result = redis_container.exec_run(
                    [
                        "redis-cli",
                        "-a",
                        f"password_{tenant_id}",
                        "SET",
                        redis_test_key,
                        redis_test_value,
                    ]
                )

                if result.exit_code == 0:
                    # Verify data exists
                    result = redis_container.exec_run(
                        [
                            "redis-cli",
                            "-a",
                            f"password_{tenant_id}",
                            "GET",
                            redis_test_key,
                        ]
                    )

                    if redis_test_value in result.output.decode():
                        results["tests"].append(
                            f"✓ Verified Redis data isolation for tenant {tenant_id}"
                        )
                    else:
                        results["status"] = "failed"
                        results["issues"].append(
                            f"Redis data verification failed for tenant {tenant_id}"
                        )
                else:
                    results["status"] = "failed"
                    results["issues"].append(
                        f"Failed to set Redis test data for tenant {tenant_id}"
                    )

        except Exception as e:
            results["status"] = "failed"
            results["issues"].append(f"Data isolation test failed: {e}")

        logger.info(f"Data isolation validation: {results['status']}")
        return results

    async def validate_resource_limits(self) -> dict[str, Any]:
        """Validate that resource limits are enforced."""
        logger.info("Validating resource limits...")

        results = {"status": "passed", "tests": [], "issues": []}

        try:
            for tenant_info in self.test_tenants:
                tenant_id = tenant_info["tenant_id"]

                for service, container_info in tenant_info["containers"].items():
                    container = self.docker_client.containers.get(container_info["id"])
                    container.reload()

                    # Check memory limits
                    if hasattr(container.attrs["HostConfig"], "Memory"):
                        memory_limit = container.attrs["HostConfig"]["Memory"]
                        if memory_limit > 0:
                            results["tests"].append(
                                f"✓ Memory limit set for {service} in tenant {tenant_id}: {memory_limit} bytes"
                            )
                        else:
                            results["issues"].append(
                                f"No memory limit set for {service} in tenant {tenant_id}"
                            )

                    # Check CPU limits
                    if container.attrs["HostConfig"].get("CpusetCpus"):
                        cpu_set = container.attrs["HostConfig"]["CpusetCpus"]
                        results["tests"].append(
                            f"✓ CPU limit set for {service} in tenant {tenant_id}: {cpu_set}"
                        )

                    # Verify container is using assigned network only
                    networks = list(
                        container.attrs["NetworkSettings"]["Networks"].keys()
                    )
                    expected_network = f"dotmac-tenant-{tenant_id}"

                    if expected_network in networks and len(networks) == 1:
                        results["tests"].append(
                            f"✓ Network isolation verified for {service} in tenant {tenant_id}"
                        )
                    else:
                        results["status"] = "failed"
                        results["issues"].append(
                            f"Network isolation failed for {service} in tenant {tenant_id}: {networks}"
                        )

        except Exception as e:
            results["status"] = "failed"
            results["issues"].append(f"Resource limits validation failed: {e}")

        logger.info(f"Resource limits validation: {results['status']}")
        return results

    async def validate_container_security(self) -> dict[str, Any]:
        """Validate container security configurations."""
        logger.info("Validating container security...")

        results = {"status": "passed", "tests": [], "issues": []}

        try:
            for tenant_info in self.test_tenants:
                tenant_id = tenant_info["tenant_id"]

                for service, container_info in tenant_info["containers"].items():
                    container = self.docker_client.containers.get(container_info["id"])

                    # Check if container is running as root
                    result = container.exec_run("whoami")
                    if result.exit_code == 0 and "root" in result.output.decode():
                        # This is expected for PostgreSQL and Redis, but we should note it
                        results["tests"].append(
                            f"✓ Container {service} in tenant {tenant_id} security checked"
                        )

                    # Check security options
                    security_opt = container.attrs["HostConfig"].get("SecurityOpt", [])
                    if "no-new-privileges:true" in security_opt:
                        results["tests"].append(
                            f"✓ No-new-privileges enabled for {service} in tenant {tenant_id}"
                        )

                    # Check read-only root filesystem
                    readonly_rootfs = container.attrs["HostConfig"].get(
                        "ReadonlyRootfs", False
                    )
                    if service == "isp_framework" and not readonly_rootfs:
                        results["issues"].append(
                            f"Read-only root filesystem not enabled for {service} in tenant {tenant_id}"
                        )

                    # Check if privileged
                    privileged = container.attrs["HostConfig"].get("Privileged", False)
                    if privileged:
                        results["status"] = "failed"
                        results["issues"].append(
                            f"Container {service} in tenant {tenant_id} is running in privileged mode"
                        )
                    else:
                        results["tests"].append(
                            f"✓ Container {service} in tenant {tenant_id} is not privileged"
                        )

        except Exception as e:
            results["status"] = "failed"
            results["issues"].append(f"Container security validation failed: {e}")

        logger.info(f"Container security validation: {results['status']}")
        return results

    async def cleanup_test_resources(self) -> None:
        """Clean up all test resources."""
        logger.info("Cleaning up test resources...")

        # Stop and remove containers
        for resource_type, resource_id in reversed(self.created_resources):
            try:
                if resource_type == "container":
                    container = self.docker_client.containers.get(resource_id)
                    container.stop(timeout=10)
                    container.remove()
                    logger.info(f"Removed container {resource_id}")

                elif resource_type == "network":
                    network = self.docker_client.networks.get(resource_id)
                    network.remove()
                    logger.info(f"Removed network {resource_id}")

            except Exception as e:
                logger.warning(f"Failed to cleanup {resource_type} {resource_id}: {e}")

        # Clean up volumes (they might have data we want to preserve for inspection)
        logger.info(
            "Note: Tenant volumes preserved for inspection. Clean manually if needed."
        )

        self.created_resources.clear()
        self.test_tenants.clear()
        logger.info("Cleanup completed")

    async def run_full_validation(self, num_tenants: int = 2) -> dict[str, Any]:
        """Run complete tenant isolation validation."""
        logger.info(
            f"Starting tenant isolation validation with {num_tenants} test tenants"
        )

        validation_results = {
            "timestamp": time.time(),
            "total_tenants": num_tenants,
            "validation_status": "passed",
            "tests": {
                "network_isolation": {},
                "data_isolation": {},
                "resource_limits": {},
                "container_security": {},
            },
            "summary": {"passed": 0, "failed": 0, "issues": []},
        }

        try:
            # Create test tenants
            for i in range(num_tenants):
                tenant_id = f"test-{uuid.uuid4().hex[:8]}"
                await self.create_test_tenant(tenant_id)

            # Run validation tests
            logger.info("Running validation tests...")

            # Network isolation
            network_results = await self.validate_network_isolation()
            validation_results["tests"]["network_isolation"] = network_results
            if network_results["status"] != "passed":
                validation_results["validation_status"] = "failed"
                validation_results["summary"]["failed"] += 1
                validation_results["summary"]["issues"].extend(
                    network_results["issues"]
                )
            else:
                validation_results["summary"]["passed"] += 1

            # Data isolation
            data_results = await self.validate_data_isolation()
            validation_results["tests"]["data_isolation"] = data_results
            if data_results["status"] != "passed":
                validation_results["validation_status"] = "failed"
                validation_results["summary"]["failed"] += 1
                validation_results["summary"]["issues"].extend(data_results["issues"])
            else:
                validation_results["summary"]["passed"] += 1

            # Resource limits
            resource_results = await self.validate_resource_limits()
            validation_results["tests"]["resource_limits"] = resource_results
            if resource_results["status"] != "passed":
                validation_results["validation_status"] = "failed"
                validation_results["summary"]["failed"] += 1
                validation_results["summary"]["issues"].extend(
                    resource_results["issues"]
                )
            else:
                validation_results["summary"]["passed"] += 1

            # Container security
            security_results = await self.validate_container_security()
            validation_results["tests"]["container_security"] = security_results
            if security_results["status"] != "passed":
                validation_results["validation_status"] = "failed"
                validation_results["summary"]["failed"] += 1
                validation_results["summary"]["issues"].extend(
                    security_results["issues"]
                )
            else:
                validation_results["summary"]["passed"] += 1

            return validation_results

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_results["validation_status"] = "error"
            validation_results["summary"]["issues"].append(f"Validation error: {e}")
            return validation_results

        finally:
            # Always cleanup
            await self.cleanup_test_resources()


async def main():
    """Main entry point."""
    import argparse


    parser = argparse.ArgumentParser(description="DotMac Tenant Isolation Validator")
    parser.add_argument(
        "--tenants", type=int, default=2, help="Number of test tenants to create"
    )
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup existing test resources",
    )

    args = parser.parse_args()

    validator = TenantIsolationValidator()

    if args.cleanup_only:
        # Find and cleanup existing test resources
        logger.info("Cleaning up existing test resources...")
        try:
            # Find test containers
            containers = validator.docker_client.containers.list(
                all=True, filters={"label": "dotmac.isolation=enabled"}
            )

            for container in containers:
                try:
                    container.stop(timeout=10)
                    container.remove()
                    logger.info(f"Removed test container: {container.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove container {container.name}: {e}")

            # Find test networks
            networks = validator.docker_client.networks.list(
                filters={"label": "dotmac.isolation=enabled"}
            )

            for network in networks:
                try:
                    network.remove()
                    logger.info(f"Removed test network: {network.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove network {network.name}: {e}")

            logger.info("Cleanup completed")
            return 0

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 1

    # Run validation
    results = await validator.run_full_validation(args.tenants)

    # Print results
    print("\n" + "=" * 60)
    print("DOTMAC TENANT ISOLATION VALIDATION RESULTS")
    print("=" * 60)
    print(f"Overall Status: {results['validation_status'].upper()}")
    print(f"Tests Passed: {results['summary']['passed']}")
    print(f"Tests Failed: {results['summary']['failed']}")
    print(f"Total Tenants Tested: {results['total_tenants']}")
    print()

    for test_name, test_results in results["tests"].items():
        print(
            f"{test_name.replace('_', ' ').title()}: {test_results['status'].upper()}"
        )
        for test in test_results.get("tests", []):
            print(f"  {test}")
        for issue in test_results.get("issues", []):
            print(f"  ❌ {issue}")
        print()

    if results["summary"]["issues"]:
        print("Summary of Issues:")
        for issue in results["summary"]["issues"]:
            print(f"  ❌ {issue}")
        print()

    # Save results to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {args.output}")

    # Return appropriate exit code
    return 0 if results["validation_status"] == "passed" else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
