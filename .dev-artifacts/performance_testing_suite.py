#!/usr/bin/env python3
"""
Performance Testing Suite for Workflow Orchestration
Phase 4: Production Readiness

This module provides comprehensive performance testing and optimization
tools for workflow orchestration components.
"""

import asyncio
import time
import statistics
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import psutil
import logging
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta


@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    test_name: str
    operation: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    
    @property
    def duration_ms(self) -> float:
        return self.duration * 1000


@dataclass
class PerformanceReport:
    """Comprehensive performance test report."""
    test_suite: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    success_rate: float
    total_duration: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput_per_second: float
    metrics: List[PerformanceMetric]
    system_metrics: Dict[str, Any]
    recommendations: List[str]


class WorkflowPerformanceTester:
    """Performance testing framework for workflow orchestration."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results_dir = Path("/home/dotmac_framework/.dev-artifacts/performance-results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for performance tests."""
        logger = logging.getLogger("performance_tester")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def test_saga_performance(self, concurrent_requests: int = 10, total_requests: int = 100) -> PerformanceReport:
        """Test saga orchestration performance under load."""
        self.logger.info(f"Starting saga performance test: {concurrent_requests} concurrent, {total_requests} total")
        
        metrics = []
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def single_saga_test() -> PerformanceMetric:
            async with semaphore:
                start_time = time.time()
                start_memory = psutil.virtual_memory().percent
                start_cpu = psutil.cpu_percent()
                
                try:
                    async with aiohttp.ClientSession() as session:
                        # Test tenant provisioning saga
                        payload = {
                            "tenant_name": f"test-tenant-{int(start_time * 1000)}",
                            "plan_id": "standard",
                            "admin_email": "admin@example.com",
                            "organization_name": "Test Organization"
                        }
                        
                        async with session.post(
                            f"{self.base_url}/api/sagas/tenant-provision",
                            json=payload,
                            headers={"x-internal-request": "true"}
                        ) as response:
                            result = await response.json()
                            success = response.status == 200 or response.status == 202
                            
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            return PerformanceMetric(
                                test_name="saga_performance",
                                operation="tenant_provision",
                                start_time=start_time,
                                end_time=end_time,
                                duration=duration,
                                success=success,
                                memory_usage=psutil.virtual_memory().percent - start_memory,
                                cpu_usage=psutil.cpu_percent() - start_cpu
                            )
                
                except Exception as e:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    return PerformanceMetric(
                        test_name="saga_performance",
                        operation="tenant_provision",
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        success=False,
                        error_message=str(e)
                    )
        
        # Run concurrent tests
        tasks = [single_saga_test() for _ in range(total_requests)]
        test_start = time.time()
        
        for completed_task in asyncio.as_completed(tasks):
            metric = await completed_task
            metrics.append(metric)
            
            if len(metrics) % 10 == 0:
                self.logger.info(f"Completed {len(metrics)}/{total_requests} saga tests")
        
        test_end = time.time()
        total_duration = test_end - test_start
        
        return self._generate_report("saga_performance", metrics, total_duration)
    
    async def test_idempotency_performance(self, concurrent_requests: int = 20, total_requests: int = 200) -> PerformanceReport:
        """Test idempotency manager performance under load."""
        self.logger.info(f"Starting idempotency performance test: {concurrent_requests} concurrent, {total_requests} total")
        
        metrics = []
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        # Use the same operation key for half the requests to test deduplication
        operation_keys = [f"test-billing-{i // 2}" for i in range(total_requests)]
        
        async def single_idempotency_test(operation_key: str) -> PerformanceMetric:
            async with semaphore:
                start_time = time.time()
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{self.base_url}/api/idempotency/{operation_key}",
                            headers={"x-internal-request": "true"}
                        ) as response:
                            result = await response.json()
                            success = response.status in [200, 404]  # 404 is expected for new keys
                            
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            return PerformanceMetric(
                                test_name="idempotency_performance",
                                operation="check_operation",
                                start_time=start_time,
                                end_time=end_time,
                                duration=duration,
                                success=success
                            )
                
                except Exception as e:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    return PerformanceMetric(
                        test_name="idempotency_performance",
                        operation="check_operation",
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        success=False,
                        error_message=str(e)
                    )
        
        # Run concurrent tests
        tasks = [single_idempotency_test(key) for key in operation_keys]
        test_start = time.time()
        
        for completed_task in asyncio.as_completed(tasks):
            metric = await completed_task
            metrics.append(metric)
            
            if len(metrics) % 20 == 0:
                self.logger.info(f"Completed {len(metrics)}/{total_requests} idempotency tests")
        
        test_end = time.time()
        total_duration = test_end - test_start
        
        return self._generate_report("idempotency_performance", metrics, total_duration)
    
    async def test_health_check_performance(self, concurrent_requests: int = 50, total_requests: int = 500) -> PerformanceReport:
        """Test health check endpoint performance under high load."""
        self.logger.info(f"Starting health check performance test: {concurrent_requests} concurrent, {total_requests} total")
        
        metrics = []
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def single_health_test() -> PerformanceMetric:
            async with semaphore:
                start_time = time.time()
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}/api/workflows/health") as response:
                            result = await response.json()
                            success = response.status == 200
                            
                            end_time = time.time()
                            duration = end_time - start_time
                            
                            return PerformanceMetric(
                                test_name="health_check_performance",
                                operation="health_check",
                                start_time=start_time,
                                end_time=end_time,
                                duration=duration,
                                success=success
                            )
                
                except Exception as e:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    return PerformanceMetric(
                        test_name="health_check_performance",
                        operation="health_check",
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        success=False,
                        error_message=str(e)
                    )
        
        # Run concurrent tests
        tasks = [single_health_test() for _ in range(total_requests)]
        test_start = time.time()
        
        for completed_task in asyncio.as_completed(tasks):
            metric = await completed_task
            metrics.append(metric)
            
            if len(metrics) % 50 == 0:
                self.logger.info(f"Completed {len(metrics)}/{total_requests} health check tests")
        
        test_end = time.time()
        total_duration = test_end - test_start
        
        return self._generate_report("health_check_performance", metrics, total_duration)
    
    def test_database_performance(self) -> Dict[str, Any]:
        """Test database performance for workflow tables."""
        self.logger.info("Starting database performance test")
        
        # This would require database connection - for now, return mock results
        # In a real implementation, this would test:
        # - Insert performance for saga_executions
        # - Query performance for saga status lookups
        # - Update performance for saga step updates
        # - Idempotency key lookup performance
        
        return {
            "saga_insert_avg_ms": 5.2,
            "saga_query_avg_ms": 2.1,
            "saga_update_avg_ms": 3.8,
            "idempotency_lookup_avg_ms": 1.5,
            "recommendations": [
                "Consider adding index on saga_executions.correlation_id",
                "Monitor connection pool utilization",
                "Consider read replicas for saga status queries"
            ]
        }
    
    def _generate_report(self, test_name: str, metrics: List[PerformanceMetric], total_duration: float) -> PerformanceReport:
        """Generate comprehensive performance report."""
        successful_metrics = [m for m in metrics if m.success]
        failed_metrics = [m for m in metrics if not m.success]
        
        durations = [m.duration for m in successful_metrics]
        
        if durations:
            avg_response_time = statistics.mean(durations)
            min_response_time = min(durations)
            max_response_time = max(durations)
            p95_response_time = statistics.quantiles(durations, n=20)[18]  # 95th percentile
            p99_response_time = statistics.quantiles(durations, n=100)[98]  # 99th percentile
            throughput_per_second = len(successful_metrics) / total_duration
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
            throughput_per_second = 0
        
        # Generate recommendations
        recommendations = []
        if len(failed_metrics) > 0:
            recommendations.append(f"Investigation needed: {len(failed_metrics)} failed requests")
        
        if avg_response_time > 1.0:  # > 1 second
            recommendations.append("High average response time detected - consider optimization")
        
        if p95_response_time > 5.0:  # > 5 seconds at 95th percentile
            recommendations.append("High tail latency detected - investigate slow requests")
        
        if throughput_per_second < 10:  # < 10 RPS
            recommendations.append("Low throughput detected - consider scaling or optimization")
        
        # Collect system metrics
        system_metrics = {
            "cpu_usage_percent": psutil.cpu_percent(),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
            "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        }
        
        return PerformanceReport(
            test_suite=test_name,
            total_tests=len(metrics),
            successful_tests=len(successful_metrics),
            failed_tests=len(failed_metrics),
            success_rate=len(successful_metrics) / len(metrics) * 100 if metrics else 0,
            total_duration=total_duration,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput_per_second=throughput_per_second,
            metrics=metrics,
            system_metrics=system_metrics,
            recommendations=recommendations
        )
    
    def save_report(self, report: PerformanceReport, filename: Optional[str] = None) -> str:
        """Save performance report to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{report.test_suite}_{timestamp}.json"
        
        filepath = self.results_dir / filename
        
        # Convert report to dict, handling PerformanceMetric objects
        report_dict = asdict(report)
        
        with open(filepath, "w") as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        self.logger.info(f"Performance report saved to: {filepath}")
        return str(filepath)
    
    def generate_visualizations(self, report: PerformanceReport) -> List[str]:
        """Generate performance visualization charts."""
        chart_files = []
        
        # Response time distribution
        successful_metrics = [m for m in report.metrics if m.success]
        durations_ms = [m.duration_ms for m in successful_metrics]
        
        if durations_ms:
            # Response time histogram
            plt.figure(figsize=(10, 6))
            plt.hist(durations_ms, bins=30, alpha=0.7, edgecolor='black')
            plt.title(f'{report.test_suite} - Response Time Distribution')
            plt.xlabel('Response Time (ms)')
            plt.ylabel('Frequency')
            plt.axvline(report.avg_response_time * 1000, color='red', linestyle='--', label=f'Average: {report.avg_response_time*1000:.1f}ms')
            plt.axvline(report.p95_response_time * 1000, color='orange', linestyle='--', label=f'95th percentile: {report.p95_response_time*1000:.1f}ms')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            chart_file = self.results_dir / f"{report.test_suite}_response_time_histogram.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(str(chart_file))
            
            # Response time over time
            plt.figure(figsize=(12, 6))
            timestamps = [m.start_time for m in successful_metrics]
            start_time = min(timestamps)
            relative_times = [(t - start_time) for t in timestamps]
            
            plt.plot(relative_times, durations_ms, alpha=0.6, marker='o', markersize=2)
            plt.title(f'{report.test_suite} - Response Time Over Time')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Response Time (ms)')
            plt.grid(True, alpha=0.3)
            
            chart_file = self.results_dir / f"{report.test_suite}_response_time_timeline.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            chart_files.append(str(chart_file))
        
        return chart_files
    
    def print_summary(self, report: PerformanceReport) -> None:
        """Print performance test summary."""
        print(f"\n{'='*60}")
        print(f"PERFORMANCE TEST REPORT: {report.test_suite.upper()}")
        print(f"{'='*60}")
        
        print(f"\n📊 Test Overview:")
        print(f"  Total Tests: {report.total_tests}")
        print(f"  Successful: {report.successful_tests}")
        print(f"  Failed: {report.failed_tests}")
        print(f"  Success Rate: {report.success_rate:.1f}%")
        print(f"  Total Duration: {report.total_duration:.2f}s")
        
        print(f"\n⚡ Performance Metrics:")
        print(f"  Average Response Time: {report.avg_response_time*1000:.1f}ms")
        print(f"  Min Response Time: {report.min_response_time*1000:.1f}ms")
        print(f"  Max Response Time: {report.max_response_time*1000:.1f}ms")
        print(f"  95th Percentile: {report.p95_response_time*1000:.1f}ms")
        print(f"  99th Percentile: {report.p99_response_time*1000:.1f}ms")
        print(f"  Throughput: {report.throughput_per_second:.1f} req/sec")
        
        print(f"\n🖥️  System Metrics:")
        print(f"  CPU Usage: {report.system_metrics['cpu_usage_percent']:.1f}%")
        print(f"  Memory Usage: {report.system_metrics['memory_usage_percent']:.1f}%")
        print(f"  Disk Usage: {report.system_metrics['disk_usage_percent']:.1f}%")
        
        if report.recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")
        
        print(f"\n{'='*60}\n")


class OptimizationSuggestions:
    """Generate optimization suggestions based on performance results."""
    
    @staticmethod
    def analyze_saga_performance(report: PerformanceReport) -> List[str]:
        """Analyze saga performance and suggest optimizations."""
        suggestions = []
        
        if report.avg_response_time > 2.0:
            suggestions.append("Consider implementing saga step parallelization for independent operations")
            suggestions.append("Review database query performance in saga coordinators")
        
        if report.p95_response_time > 10.0:
            suggestions.append("Implement timeout mechanisms to prevent long-running sagas")
            suggestions.append("Consider saga step checkpointing for better recovery")
        
        if report.success_rate < 95:
            suggestions.append("Implement more robust error handling and retry mechanisms")
            suggestions.append("Add circuit breakers for external service calls")
        
        if report.throughput_per_second < 5:
            suggestions.append("Consider increasing database connection pool size")
            suggestions.append("Implement saga batching for bulk operations")
        
        return suggestions
    
    @staticmethod
    def analyze_idempotency_performance(report: PerformanceReport) -> List[str]:
        """Analyze idempotency performance and suggest optimizations."""
        suggestions = []
        
        if report.avg_response_time > 0.1:
            suggestions.append("Consider caching frequently accessed idempotency keys")
            suggestions.append("Optimize database indexes on idempotent_operations table")
        
        if report.throughput_per_second < 100:
            suggestions.append("Consider using Redis for idempotency key storage")
            suggestions.append("Implement connection pooling for idempotency checks")
        
        return suggestions
    
    @staticmethod
    def generate_optimization_report(reports: List[PerformanceReport]) -> Dict[str, Any]:
        """Generate comprehensive optimization report from multiple test results."""
        optimization_report = {
            "timestamp": datetime.now().isoformat(),
            "test_summary": {},
            "overall_recommendations": [],
            "specific_optimizations": {}
        }
        
        for report in reports:
            optimization_report["test_summary"][report.test_suite] = {
                "success_rate": report.success_rate,
                "avg_response_time_ms": report.avg_response_time * 1000,
                "throughput_rps": report.throughput_per_second,
                "p95_response_time_ms": report.p95_response_time * 1000
            }
            
            if "saga" in report.test_suite:
                optimization_report["specific_optimizations"]["saga"] = OptimizationSuggestions.analyze_saga_performance(report)
            elif "idempotency" in report.test_suite:
                optimization_report["specific_optimizations"]["idempotency"] = OptimizationSuggestions.analyze_idempotency_performance(report)
        
        # Generate overall recommendations
        avg_success_rates = [r.success_rate for r in reports]
        if statistics.mean(avg_success_rates) < 95:
            optimization_report["overall_recommendations"].append("Overall system reliability needs improvement")
        
        avg_response_times = [r.avg_response_time for r in reports]
        if statistics.mean(avg_response_times) > 1.0:
            optimization_report["overall_recommendations"].append("Consider horizontal scaling of application instances")
        
        return optimization_report


async def main():
    """Run comprehensive performance test suite."""
    print("🚀 Starting Workflow Orchestration Performance Test Suite")
    print("Phase 4: Production Readiness")
    print()
    
    tester = WorkflowPerformanceTester()
    reports = []
    
    try:
        # Test saga performance
        print("1. Testing Saga Performance...")
        saga_report = await tester.test_saga_performance(concurrent_requests=5, total_requests=50)
        reports.append(saga_report)
        tester.print_summary(saga_report)
        tester.save_report(saga_report)
        
        # Test idempotency performance
        print("2. Testing Idempotency Performance...")
        idempotency_report = await tester.test_idempotency_performance(concurrent_requests=10, total_requests=100)
        reports.append(idempotency_report)
        tester.print_summary(idempotency_report)
        tester.save_report(idempotency_report)
        
        # Test health check performance
        print("3. Testing Health Check Performance...")
        health_report = await tester.test_health_check_performance(concurrent_requests=25, total_requests=250)
        reports.append(health_report)
        tester.print_summary(health_report)
        tester.save_report(health_report)
        
        # Generate optimization report
        optimization_report = OptimizationSuggestions.generate_optimization_report(reports)
        
        # Save optimization report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        optimization_file = tester.results_dir / f"optimization_report_{timestamp}.json"
        with open(optimization_file, "w") as f:
            json.dump(optimization_report, f, indent=2, default=str)
        
        print(f"📈 Optimization report saved to: {optimization_file}")
        
        # Generate visualizations
        for report in reports:
            charts = tester.generate_visualizations(report)
            print(f"📊 Charts generated for {report.test_suite}: {len(charts)} files")
        
        print("\n✅ Performance testing suite completed successfully!")
        print("\n📋 Summary of Results:")
        for report in reports:
            print(f"  • {report.test_suite}: {report.success_rate:.1f}% success, {report.avg_response_time*1000:.1f}ms avg, {report.throughput_per_second:.1f} req/sec")
        
        print(f"\n📁 All results saved to: {tester.results_dir}")
        
    except Exception as e:
        print(f"❌ Error running performance tests: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))