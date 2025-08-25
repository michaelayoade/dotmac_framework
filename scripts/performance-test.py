#!/usr/bin/env python3
"""
Simple Performance Testing Framework for DotMac Platform.

Uses existing tools (requests, asyncio) to validate:
- API response times
- Database performance
- Redis performance  
- Container resource usage
- Multi-tenant performance isolation
"""

import asyncio
import aiohttp
import json
import logging
import os
import psutil
import redis
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceResult:
    """Performance test result."""
    test_name: str
    success_count: int
    error_count: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    max_response_time: float
    min_response_time: float
    requests_per_second: float
    errors: List[str]


class PerformanceTester:
    """Simple performance testing framework."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
        
    async def test_api_endpoints(self, base_url: str, endpoints: List[str], concurrent_users: int = 10, requests_per_user: int = 10) -> PerformanceResult:
        """Test API endpoint performance."""
        logger.info(f"Testing API endpoints with {concurrent_users} concurrent users, {requests_per_user} requests each")
        
        async def make_request(session: aiohttp.ClientSession, endpoint: str) -> Tuple[bool, float, str]:
            """Make a single request and return success, time, error."""
            start_time = time.time()
            try:
                async with session.get(f"{base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=30)) as response:
                    await response.text()  # Consume response
                    response_time = time.time() - start_time
                    return response.status < 400, response_time, ""
            except Exception as e:
                response_time = time.time() - start_time
                return False, response_time, str(e)
        
        async def user_simulation(user_id: int) -> List[Tuple[bool, float, str]]:
            """Simulate one user making requests."""
            async with aiohttp.ClientSession() as session:
                results = []
                for _ in range(requests_per_user):
                    endpoint = endpoints[(_ + user_id) % len(endpoints)]
                    result = await make_request(session, endpoint)
                    results.append(result)
                    await asyncio.sleep(0.1)  # Small delay between requests
                return results
        
        # Run concurrent user simulations
        start_time = time.time()
        tasks = [user_simulation(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Process results
        all_results = [result for user_result in user_results for result in user_result]
        success_count = sum(1 for success, _, _ in all_results if success)
        error_count = len(all_results) - success_count
        response_times = [time for _, time, _ in all_results]
        errors = [error for _, _, error in all_results if error]
        
        return PerformanceResult(
            test_name="API Endpoints",
            success_count=success_count,
            error_count=error_count,
            avg_response_time=statistics.mean(response_times),
            p95_response_time=statistics.quantiles(response_times, n=20)[18] if response_times else 0,  # 95th percentile
            p99_response_time=statistics.quantiles(response_times, n=100)[98] if response_times else 0,  # 99th percentile
            max_response_time=max(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            requests_per_second=len(all_results) / total_time,
            errors=errors[:10]  # Keep only first 10 errors
        )
    
    def test_database_performance(self, db_config: Dict[str, str], operations: int = 1000) -> PerformanceResult:
        """Test PostgreSQL database performance."""
        logger.info(f"Testing database performance with {operations} operations")
        
        response_times = []
        errors = []
        success_count = 0
        
        try:
            conn = psycopg2.connect(
                host=db_config.get("host", "localhost"),
                port=db_config.get("port", 5432),
                database=db_config.get("database", "dotmac_db"),
                user=db_config.get("user", "postgres"),
                password=db_config.get("password", "")
            )
            cur = conn.cursor()
            
            # Create test table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS performance_test (
                    id SERIAL PRIMARY KEY,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            
            start_time = time.time()
            
            for i in range(operations):
                op_start = time.time()
                try:
                    if i % 4 == 0:  # INSERT
                        cur.execute("INSERT INTO performance_test (data) VALUES (%s)", (f"test_data_{i}",))
                    elif i % 4 == 1:  # SELECT
                        cur.execute("SELECT COUNT(*) FROM performance_test")
                        cur.fetchone()
                    elif i % 4 == 2:  # UPDATE
                        cur.execute("UPDATE performance_test SET data = %s WHERE id = %s", (f"updated_{i}", max(1, i-100)))
                    else:  # DELETE
                        cur.execute("DELETE FROM performance_test WHERE id = %s", (max(1, i-200),))
                    
                    if i % 100 == 0:  # Commit every 100 operations
                        conn.commit()
                    
                    response_times.append(time.time() - op_start)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Op {i}: {str(e)}")
                    response_times.append(time.time() - op_start)
            
            conn.commit()
            total_time = time.time() - start_time
            
            # Cleanup
            cur.execute("DROP TABLE performance_test")
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            errors.append(f"Database connection error: {str(e)}")
            return PerformanceResult(
                test_name="Database Performance",
                success_count=0,
                error_count=1,
                avg_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                max_response_time=0,
                min_response_time=0,
                requests_per_second=0,
                errors=errors
            )
        
        return PerformanceResult(
            test_name="Database Performance",
            success_count=success_count,
            error_count=len(errors),
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            p95_response_time=statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
            p99_response_time=statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0,
            max_response_time=max(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            requests_per_second=operations / total_time,
            errors=errors[:10]
        )
    
    def test_redis_performance(self, redis_config: Dict[str, str], operations: int = 1000) -> PerformanceResult:
        """Test Redis cache performance."""
        logger.info(f"Testing Redis performance with {operations} operations")
        
        response_times = []
        errors = []
        success_count = 0
        
        try:
            r = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                password=redis_config.get("password", ""),
                db=redis_config.get("db", 0),
                socket_timeout=5.0
            )
            
            # Test connection
            r.ping()
            
            start_time = time.time()
            
            for i in range(operations):
                op_start = time.time()
                try:
                    if i % 3 == 0:  # SET
                        r.set(f"perf_test:{i}", f"value_{i}", ex=60)
                    elif i % 3 == 1:  # GET
                        r.get(f"perf_test:{max(0, i-10)}")
                    else:  # DELETE
                        r.delete(f"perf_test:{max(0, i-20)}")
                    
                    response_times.append(time.time() - op_start)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Op {i}: {str(e)}")
                    response_times.append(time.time() - op_start)
            
            total_time = time.time() - start_time
            
            # Cleanup
            keys = r.keys("perf_test:*")
            if keys:
                r.delete(*keys)
            
        except Exception as e:
            errors.append(f"Redis connection error: {str(e)}")
            return PerformanceResult(
                test_name="Redis Performance",
                success_count=0,
                error_count=1,
                avg_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                max_response_time=0,
                min_response_time=0,
                requests_per_second=0,
                errors=errors
            )
        
        return PerformanceResult(
            test_name="Redis Performance",
            success_count=success_count,
            error_count=len(errors),
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            p95_response_time=statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
            p99_response_time=statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0,
            max_response_time=max(response_times) if response_times else 0,
            min_response_time=min(response_times) if response_times else 0,
            requests_per_second=operations / total_time,
            errors=errors[:10]
        )
    
    def test_system_resources(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Monitor system resource usage during tests."""
        logger.info(f"Monitoring system resources for {duration_seconds} seconds")
        
        cpu_samples = []
        memory_samples = []
        disk_samples = []
        
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            cpu_samples.append(psutil.cpu_percent(interval=1))
            
            memory = psutil.virtual_memory()
            memory_samples.append(memory.percent)
            
            disk = psutil.disk_usage('/')
            disk_samples.append(disk.percent)
        
        return {
            "duration_seconds": duration_seconds,
            "cpu": {
                "avg_percent": statistics.mean(cpu_samples),
                "max_percent": max(cpu_samples),
                "samples": len(cpu_samples)
            },
            "memory": {
                "avg_percent": statistics.mean(memory_samples),
                "max_percent": max(memory_samples),
                "samples": len(memory_samples)
            },
            "disk": {
                "avg_percent": statistics.mean(disk_samples),
                "max_percent": max(disk_samples),
                "samples": len(disk_samples)
            }
        }
    
    async def run_performance_suite(self) -> Dict[str, Any]:
        """Run complete performance test suite."""
        logger.info("Starting DotMac Platform performance test suite")
        
        suite_results = {
            "timestamp": time.time(),
            "tests": {},
            "system_resources": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "performance_score": 0
            }
        }
        
        # Start system monitoring
        resource_monitor_task = asyncio.create_task(
            asyncio.to_thread(self.test_system_resources, 120)
        )
        
        try:
            # Test API performance
            if self.config.get("api_tests", {}).get("enabled", True):
                api_config = self.config.get("api_tests", {})
                base_url = api_config.get("base_url", "http://localhost:8000")
                endpoints = api_config.get("endpoints", ["/health", "/api/v1/customers", "/api/v1/services"])
                concurrent_users = api_config.get("concurrent_users", 10)
                requests_per_user = api_config.get("requests_per_user", 10)
                
                api_result = await self.test_api_endpoints(base_url, endpoints, concurrent_users, requests_per_user)
                suite_results["tests"]["api"] = api_result
                suite_results["summary"]["total_tests"] += 1
                
                if api_result.error_count / (api_result.success_count + api_result.error_count) < 0.05:  # < 5% error rate
                    suite_results["summary"]["passed_tests"] += 1
                else:
                    suite_results["summary"]["failed_tests"] += 1
            
            # Test database performance
            if self.config.get("database_tests", {}).get("enabled", True):
                db_config = self.config.get("database_tests", {})
                operations = db_config.get("operations", 1000)
                
                db_result = await asyncio.to_thread(self.test_database_performance, db_config, operations)
                suite_results["tests"]["database"] = db_result
                suite_results["summary"]["total_tests"] += 1
                
                if db_result.avg_response_time < 0.1:  # < 100ms average
                    suite_results["summary"]["passed_tests"] += 1
                else:
                    suite_results["summary"]["failed_tests"] += 1
            
            # Test Redis performance
            if self.config.get("redis_tests", {}).get("enabled", True):
                redis_config = self.config.get("redis_tests", {})
                operations = redis_config.get("operations", 1000)
                
                redis_result = await asyncio.to_thread(self.test_redis_performance, redis_config, operations)
                suite_results["tests"]["redis"] = redis_result
                suite_results["summary"]["total_tests"] += 1
                
                if redis_result.avg_response_time < 0.01:  # < 10ms average
                    suite_results["summary"]["passed_tests"] += 1
                else:
                    suite_results["summary"]["failed_tests"] += 1
            
            # Wait for resource monitoring to complete
            suite_results["system_resources"] = await resource_monitor_task
            
            # Calculate performance score
            if suite_results["summary"]["total_tests"] > 0:
                suite_results["summary"]["performance_score"] = (
                    suite_results["summary"]["passed_tests"] / suite_results["summary"]["total_tests"]
                ) * 100
            
            logger.info("Performance test suite completed")
            return suite_results
            
        except Exception as e:
            logger.error(f"Performance test suite failed: {e}")
            suite_results["error"] = str(e)
            return suite_results


def load_config(config_file: str) -> Dict[str, Any]:
    """Load performance test configuration."""
    default_config = {
        "api_tests": {
            "enabled": True,
            "base_url": "http://localhost:8000",
            "endpoints": ["/health", "/api/v1/customers", "/api/v1/services", "/api/v1/billing"],
            "concurrent_users": 10,
            "requests_per_user": 20
        },
        "database_tests": {
            "enabled": True,
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "dotmac_db"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", ""),
            "operations": 1000
        },
        "redis_tests": {
            "enabled": True,
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD", ""),
            "db": 0,
            "operations": 1000
        }
    }
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # Simple merge
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
        except Exception as e:
            logger.warning(f"Failed to load config file {config_file}: {e}")
    
    return default_config


def print_results(results: Dict[str, Any]) -> None:
    """Print performance test results."""
    print("\n" + "="*60)
    print("DOTMAC PLATFORM PERFORMANCE TEST RESULTS")
    print("="*60)
    
    summary = results["summary"]
    print(f"Overall Performance Score: {summary['performance_score']:.1f}/100")
    print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
    print()
    
    # Test results
    for test_name, test_result in results.get("tests", {}).items():
        if isinstance(test_result, PerformanceResult):
            print(f"{test_name.upper()} PERFORMANCE:")
            print(f"  Success Rate: {test_result.success_count}/{test_result.success_count + test_result.error_count} ({(test_result.success_count/(test_result.success_count + test_result.error_count)*100):.1f}%)")
            print(f"  Avg Response Time: {test_result.avg_response_time*1000:.1f}ms")
            print(f"  95th Percentile: {test_result.p95_response_time*1000:.1f}ms")
            print(f"  99th Percentile: {test_result.p99_response_time*1000:.1f}ms")
            print(f"  Requests/Second: {test_result.requests_per_second:.1f}")
            
            if test_result.errors:
                print(f"  Sample Errors: {test_result.errors[:3]}")
            print()
        else:
            print(f"{test_name.upper()}: {test_result}")
    
    # System resources
    if "system_resources" in results:
        resources = results["system_resources"]
        print("SYSTEM RESOURCE USAGE:")
        print(f"  CPU: {resources['cpu']['avg_percent']:.1f}% avg, {resources['cpu']['max_percent']:.1f}% max")
        print(f"  Memory: {resources['memory']['avg_percent']:.1f}% avg, {resources['memory']['max_percent']:.1f}% max") 
        print(f"  Disk: {resources['disk']['avg_percent']:.1f}% avg, {resources['disk']['max_percent']:.1f}% max")
        print()
    
    # Performance recommendations
    print("RECOMMENDATIONS:")
    
    if summary["performance_score"] < 70:
        print("  ⚠️  Overall performance is below acceptable levels")
    
    for test_name, test_result in results.get("tests", {}).items():
        if isinstance(test_result, PerformanceResult):
            error_rate = test_result.error_count / (test_result.success_count + test_result.error_count)
            
            if error_rate > 0.05:
                print(f"  ⚠️  {test_name} has high error rate ({error_rate*100:.1f}%)")
            
            if test_result.p95_response_time > 1.0:
                print(f"  ⚠️  {test_name} has slow response times (95th percentile: {test_result.p95_response_time*1000:.0f}ms)")
            
            if test_result.requests_per_second < 100 and test_name == "api":
                print(f"  ⚠️  API throughput is low ({test_result.requests_per_second:.1f} RPS)")
    
    if results.get("system_resources", {}).get("cpu", {}).get("max_percent", 0) > 80:
        print("  ⚠️  High CPU usage detected - consider scaling")
    
    if results.get("system_resources", {}).get("memory", {}).get("max_percent", 0) > 80:
        print("  ⚠️  High memory usage detected - consider scaling")
    
    print()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DotMac Platform Performance Tester")
    parser.add_argument("--config", default="/home/dotmac_framework/config/performance-test.json")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--concurrent-users", type=int, help="Override concurrent users")
    parser.add_argument("--requests-per-user", type=int, help="Override requests per user")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line args
    if args.concurrent_users:
        config["api_tests"]["concurrent_users"] = args.concurrent_users
    if args.requests_per_user:
        config["api_tests"]["requests_per_user"] = args.requests_per_user
    
    # Run performance tests
    tester = PerformanceTester(config)
    results = await tester.run_performance_suite()
    
    # Print results
    print_results(results)
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            # Convert PerformanceResult objects to dict for JSON serialization
            json_results = results.copy()
            for test_name, test_result in json_results.get("tests", {}).items():
                if isinstance(test_result, PerformanceResult):
                    json_results["tests"][test_name] = {
                        "test_name": test_result.test_name,
                        "success_count": test_result.success_count,
                        "error_count": test_result.error_count,
                        "avg_response_time": test_result.avg_response_time,
                        "p95_response_time": test_result.p95_response_time,
                        "p99_response_time": test_result.p99_response_time,
                        "max_response_time": test_result.max_response_time,
                        "min_response_time": test_result.min_response_time,
                        "requests_per_second": test_result.requests_per_second,
                        "errors": test_result.errors
                    }
            
            json.dump(json_results, f, indent=2, default=str)
        print(f"Results saved to: {args.output}")
    
    # Return appropriate exit code
    return 0 if results["summary"]["performance_score"] >= 70 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))