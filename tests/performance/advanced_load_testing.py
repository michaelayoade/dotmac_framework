"""
Advanced Performance Testing Framework
Includes stress testing, spike testing, endurance testing, and database performance testing
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import statistics
import json

from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import psutil
import asyncpg
import redis


class TestType(Enum):
    LOAD = "load"
    STRESS = "stress" 
    SPIKE = "spike"
    ENDURANCE = "endurance"
    VOLUME = "volume"


@dataclass
class PerformanceThresholds:
    """Performance thresholds for different test types"""
    max_response_time_ms: int
    max_error_rate_percent: float
    min_throughput_rps: float
    max_cpu_percent: float
    max_memory_percent: float
    max_db_connections: int


class AdvancedLoadTestFramework:
    """Advanced load testing framework with multiple test patterns"""
    
    def __init__(self):
        self.results = {}
        self.monitoring_data = {}
        
    async def run_stress_test(self, 
                            target_host: str,
                            max_users: int = 1000,
                            spawn_rate: int = 50,
                            duration: int = 300) -> Dict[str, Any]:
        """
        Stress test: Gradually increase load beyond normal capacity to find breaking point
        """
        print(f"🔥 Starting stress test: {max_users} max users, {duration}s duration")
        
        class StressTestUser(HttpUser):
            wait_time = between(0.1, 0.5)  # Aggressive timing
            host = target_host
            
            @task(3)
            def customer_login(self):
                """Simulate customer login - most frequent operation"""
                self.client.post("/api/auth/login", json={
                    "email": f"stress_user_{self.user_id}@example.com",
                    "password": "test123"
                })
            
            @task(2)
            def browse_service_plans(self):
                """Browse available service plans"""
                self.client.get("/api/service-plans")
            
            @task(2)
            def check_service_status(self):
                """Check service status"""
                self.client.get(f"/api/customer/{self.user_id}/service-status")
            
            @task(1)
            def update_profile(self):
                """Update customer profile"""
                self.client.put(f"/api/customer/{self.user_id}/profile", json={
                    "preferences": {"notifications": True}
                })
            
            @task(1)
            def generate_invoice(self):
                """Generate customer invoice - database intensive"""
                self.client.post(f"/api/billing/{self.user_id}/generate-invoice")
            
            def on_start(self):
                self.user_id = hash(self) % 10000  # Simulate user ID
        
        # Setup monitoring
        monitoring_task = asyncio.create_task(
            self._monitor_system_resources(duration, test_type=TestType.STRESS)
        )
        
        # Configure and run stress test
        env = Environment(user_classes=[StressTestUser])
        env.create_local_runner()
        
        # Start with baseline load and ramp up aggressively
        stress_phases = [
            (50, 10),    # 50 users in 10s
            (150, 20),   # 150 users in 20s  
            (300, 30),   # 300 users in 30s
            (500, 40),   # 500 users in 40s
            (750, 50),   # 750 users in 50s
            (max_users, 60)  # Max users in 60s
        ]
        
        results = {}
        for target_users, ramp_time in stress_phases:
            print(f"📈 Ramping to {target_users} users over {ramp_time}s")
            
            env.runner.start(target_users, spawn_rate=target_users/ramp_time)
            await asyncio.sleep(ramp_time + 30)  # Ramp time + observation period
            
            # Capture metrics at this load level
            stats = env.runner.stats
            results[f"{target_users}_users"] = {
                "avg_response_time": stats.total.avg_response_time,
                "max_response_time": stats.total.max_response_time, 
                "requests_per_sec": stats.total.current_rps,
                "failure_rate": stats.total.fail_ratio,
                "total_requests": stats.total.num_requests,
                "error_count": stats.total.num_failures
            }
            
            # Check if we've hit breaking point
            if (stats.total.avg_response_time > 5000 or  # 5s response time
                stats.total.fail_ratio > 0.10):         # 10% error rate
                print(f"💥 Breaking point reached at {target_users} users")
                break
        
        env.runner.stop()
        
        # Wait for monitoring to complete
        monitoring_data = await monitoring_task
        
        return {
            "test_type": TestType.STRESS.value,
            "load_phases": results,
            "breaking_point": self._identify_breaking_point(results),
            "system_resources": monitoring_data,
            "recommendations": self._generate_stress_test_recommendations(results, monitoring_data)
        }

    async def run_spike_test(self,
                           target_host: str,
                           baseline_users: int = 100,
                           spike_users: int = 1000,
                           spike_duration: int = 60) -> Dict[str, Any]:
        """
        Spike test: Sudden traffic increases to test system resilience
        """
        print(f"⚡ Starting spike test: {baseline_users} → {spike_users} users for {spike_duration}s")
        
        class SpikeTestUser(HttpUser):
            wait_time = between(1, 3)
            host = target_host
            
            @task
            def mixed_operations(self):
                """Mix of operations during spike"""
                operations = [
                    lambda: self.client.get("/api/health"),
                    lambda: self.client.get("/api/service-plans"), 
                    lambda: self.client.post("/api/auth/login", json={
                        "email": f"spike_user_{hash(self) % 1000}@example.com",
                        "password": "test123"
                    }),
                    lambda: self.client.get(f"/api/customer/{hash(self) % 1000}/dashboard")
                ]
                
                import random
                operation = random.choice(operations)
                operation()
        
        env = Environment(user_classes=[SpikeTestUser])
        env.runner = env.create_local_runner()
        
        # Phase 1: Establish baseline
        print("📊 Establishing baseline performance...")
        monitoring_task = asyncio.create_task(
            self._monitor_system_resources(300, test_type=TestType.SPIKE)
        )
        
        env.runner.start(baseline_users, spawn_rate=10)
        await asyncio.sleep(60)  # Baseline period
        
        baseline_stats = {
            "avg_response_time": env.runner.stats.total.avg_response_time,
            "rps": env.runner.stats.total.current_rps,
            "error_rate": env.runner.stats.total.fail_ratio
        }
        
        # Phase 2: Execute spike
        print(f"🚀 Executing spike: {baseline_users} → {spike_users} users")
        spike_start = time.time()
        
        env.runner.start(spike_users, spawn_rate=100)  # Rapid spike
        await asyncio.sleep(spike_duration)
        
        spike_stats = {
            "avg_response_time": env.runner.stats.total.avg_response_time,
            "rps": env.runner.stats.total.current_rps, 
            "error_rate": env.runner.stats.total.fail_ratio,
            "duration": time.time() - spike_start
        }
        
        # Phase 3: Return to baseline
        print("📉 Returning to baseline...")
        env.runner.start(baseline_users, spawn_rate=20)
        await asyncio.sleep(60)  # Recovery observation
        
        recovery_stats = {
            "avg_response_time": env.runner.stats.total.avg_response_time,
            "rps": env.runner.stats.total.current_rps,
            "error_rate": env.runner.stats.total.fail_ratio
        }
        
        env.runner.stop()
        monitoring_data = await monitoring_task
        
        return {
            "test_type": TestType.SPIKE.value,
            "baseline": baseline_stats,
            "spike": spike_stats,
            "recovery": recovery_stats,
            "spike_impact": self._calculate_spike_impact(baseline_stats, spike_stats),
            "recovery_time": self._calculate_recovery_time(spike_stats, recovery_stats),
            "system_resources": monitoring_data,
            "resilience_score": self._calculate_resilience_score(baseline_stats, spike_stats, recovery_stats)
        }

    async def run_endurance_test(self,
                               target_host: str, 
                               users: int = 200,
                               duration_hours: int = 4) -> Dict[str, Any]:
        """
        Endurance test: Sustained load over extended period to detect memory leaks and degradation
        """
        duration_seconds = duration_hours * 3600
        print(f"⏰ Starting endurance test: {users} users for {duration_hours} hours")
        
        class EnduranceTestUser(HttpUser):
            wait_time = between(2, 8)  # Realistic user behavior
            host = target_host
            
            @task(5)
            def browse_dashboard(self):
                """Regular dashboard browsing"""
                self.client.get(f"/api/customer/{hash(self) % 1000}/dashboard")
            
            @task(3) 
            def check_usage(self):
                """Check data usage"""
                self.client.get(f"/api/customer/{hash(self) % 1000}/usage")
            
            @task(2)
            def view_bills(self):
                """View billing history"""
                self.client.get(f"/api/billing/{hash(self) % 1000}/invoices")
            
            @task(1)
            def update_settings(self):
                """Occasional settings updates"""
                self.client.put(f"/api/customer/{hash(self) % 1000}/settings", json={
                    "email_notifications": True,
                    "sms_notifications": False
                })
        
        env = Environment(user_classes=[EnduranceTestUser])
        env.runner = env.create_local_runner()
        
        # Start monitoring for extended period
        monitoring_task = asyncio.create_task(
            self._monitor_system_resources(duration_seconds, test_type=TestType.ENDURANCE)
        )
        
        # Start endurance test
        env.runner.start(users, spawn_rate=5)
        
        # Collect metrics at regular intervals
        metrics_collection = []
        collection_interval = 300  # 5 minutes
        
        for hour in range(duration_hours):
            for interval in range(0, 3600, collection_interval):
                await asyncio.sleep(collection_interval)
                
                current_stats = {
                    "timestamp": datetime.now().isoformat(),
                    "hour": hour,
                    "avg_response_time": env.runner.stats.total.avg_response_time,
                    "rps": env.runner.stats.total.current_rps,
                    "error_rate": env.runner.stats.total.fail_ratio,
                    "total_requests": env.runner.stats.total.num_requests,
                    "active_users": env.runner.user_count
                }
                metrics_collection.append(current_stats)
                
                print(f"⏱️  Hour {hour+1}, Interval {interval//60}min: "
                      f"Avg RT: {current_stats['avg_response_time']:.2f}ms, "
                      f"RPS: {current_stats['rps']:.2f}, "
                      f"Errors: {current_stats['error_rate']:.2%}")
        
        env.runner.stop()
        monitoring_data = await monitoring_task
        
        # Analyze endurance results
        degradation_analysis = self._analyze_performance_degradation(metrics_collection)
        memory_leak_analysis = self._analyze_memory_patterns(monitoring_data)
        
        return {
            "test_type": TestType.ENDURANCE.value,
            "duration_hours": duration_hours,
            "metrics_timeline": metrics_collection,
            "degradation_analysis": degradation_analysis,
            "memory_leak_analysis": memory_leak_analysis,
            "system_resources": monitoring_data,
            "stability_score": self._calculate_stability_score(metrics_collection),
            "recommendations": self._generate_endurance_recommendations(degradation_analysis, memory_leak_analysis)
        }

    async def run_database_performance_test(self,
                                          db_config: Dict[str, str],
                                          concurrent_connections: int = 100,
                                          duration: int = 300) -> Dict[str, Any]:
        """
        Database performance test: Test database under various load patterns
        """
        print(f"🗄️ Starting database performance test: {concurrent_connections} connections for {duration}s")
        
        # Database test scenarios
        test_scenarios = [
            {
                "name": "read_heavy_workload",
                "weight": 70,
                "operations": [
                    "SELECT * FROM customers WHERE tier = $1 LIMIT 50",
                    "SELECT * FROM service_plans WHERE active = true",
                    "SELECT * FROM invoices WHERE customer_id = $1 ORDER BY created_at DESC LIMIT 10",
                    "SELECT COUNT(*) FROM usage_records WHERE customer_id = $1 AND date >= $2"
                ]
            },
            {
                "name": "write_heavy_workload", 
                "weight": 20,
                "operations": [
                    "INSERT INTO usage_records (customer_id, bytes_used, timestamp) VALUES ($1, $2, $3)",
                    "UPDATE customers SET last_activity = $1 WHERE id = $2",
                    "INSERT INTO audit_logs (action, user_id, timestamp) VALUES ($1, $2, $3)"
                ]
            },
            {
                "name": "mixed_transactions",
                "weight": 10,
                "operations": [
                    # Complex transaction with multiple tables
                    """
                    BEGIN;
                    UPDATE customers SET balance = balance - $1 WHERE id = $2;
                    INSERT INTO transactions (customer_id, amount, type) VALUES ($2, $1, 'charge');
                    INSERT INTO invoices (customer_id, amount, due_date) VALUES ($2, $1, $3);
                    COMMIT;
                    """
                ]
            }
        ]
        
        # Connection pool setup
        pool = await asyncpg.create_pool(
            host=db_config["host"],
            port=db_config["port"], 
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            min_size=concurrent_connections//2,
            max_size=concurrent_connections
        )
        
        # Monitoring setup
        db_monitoring_task = asyncio.create_task(
            self._monitor_database_performance(pool, duration)
        )
        
        # Run concurrent database operations
        test_tasks = []
        for i in range(concurrent_connections):
            task = asyncio.create_task(
                self._database_worker(pool, test_scenarios, duration, worker_id=i)
            )
            test_tasks.append(task)
        
        # Wait for all workers to complete
        worker_results = await asyncio.gather(*test_tasks)
        db_monitoring_data = await db_monitoring_task
        
        await pool.close()
        
        # Aggregate results
        total_operations = sum(result["total_operations"] for result in worker_results)
        total_errors = sum(result["errors"] for result in worker_results)
        avg_response_time = statistics.mean([result["avg_response_time"] for result in worker_results])
        
        return {
            "test_type": "database_performance",
            "concurrent_connections": concurrent_connections,
            "duration": duration,
            "total_operations": total_operations,
            "operations_per_second": total_operations / duration,
            "error_rate": total_errors / total_operations if total_operations > 0 else 0,
            "avg_response_time_ms": avg_response_time,
            "worker_results": worker_results,
            "database_metrics": db_monitoring_data,
            "connection_pool_stats": self._analyze_connection_pool_performance(worker_results),
            "query_performance_analysis": self._analyze_query_performance(worker_results),
            "recommendations": self._generate_database_recommendations(db_monitoring_data, worker_results)
        }

    async def _monitor_system_resources(self, duration: int, test_type: TestType) -> Dict[str, Any]:
        """Monitor system resources during performance tests"""
        monitoring_data = {
            "cpu_percent": [],
            "memory_percent": [],
            "disk_io": [],
            "network_io": [],
            "timestamps": []
        }
        
        interval = 5  # Monitor every 5 seconds
        for _ in range(0, duration, interval):
            timestamp = datetime.now().isoformat()
            
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            # Network I/O
            network_io = psutil.net_io_counters()
            
            monitoring_data["timestamps"].append(timestamp)
            monitoring_data["cpu_percent"].append(cpu_percent)
            monitoring_data["memory_percent"].append(memory.percent)
            monitoring_data["disk_io"].append({
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes
            })
            monitoring_data["network_io"].append({
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv
            })
            
            await asyncio.sleep(interval)
        
        return monitoring_data

    async def _database_worker(self, pool: asyncpg.Pool, scenarios: List[Dict], 
                             duration: int, worker_id: int) -> Dict[str, Any]:
        """Individual database worker for performance testing"""
        start_time = time.time()
        operations = 0
        errors = 0
        response_times = []
        
        import random
        
        while time.time() - start_time < duration:
            try:
                # Select scenario based on weight
                scenario = random.choices(
                    scenarios,
                    weights=[s["weight"] for s in scenarios]
                )[0]
                
                # Execute random operation from scenario
                operation = random.choice(scenario["operations"])
                
                operation_start = time.time()
                
                async with pool.acquire() as connection:
                    if "BEGIN" in operation:
                        # Transaction operation
                        await connection.execute(operation)
                    else:
                        # Simple query with mock parameters
                        params = self._generate_query_parameters(operation, worker_id)
                        await connection.fetchrow(operation, *params)
                
                response_time = (time.time() - operation_start) * 1000
                response_times.append(response_time)
                operations += 1
                
            except Exception as e:
                errors += 1
                print(f"Database worker {worker_id} error: {e}")
            
            # Small delay to prevent overwhelming
            await asyncio.sleep(random.uniform(0.01, 0.1))
        
        return {
            "worker_id": worker_id,
            "total_operations": operations,
            "errors": errors,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0
        }

    def _generate_query_parameters(self, query: str, worker_id: int) -> List[Any]:
        """Generate realistic parameters for database queries"""
        import random
        from datetime import datetime, timedelta
        
        params = []
        
        # Count parameter placeholders
        param_count = query.count('$')
        
        for i in range(param_count):
            if "customer_id" in query.lower():
                params.append(f"cust_{random.randint(1, 10000)}")
            elif "tier" in query.lower():
                params.append(random.choice(["basic", "premium", "enterprise"]))
            elif "bytes_used" in query.lower():
                params.append(random.randint(1000000, 100000000))  # 1MB to 100MB
            elif "timestamp" in query.lower() or "date" in query.lower():
                params.append(datetime.now() - timedelta(days=random.randint(1, 30)))
            elif "amount" in query.lower():
                params.append(round(random.uniform(10.0, 500.0), 2))
            elif "due_date" in query.lower():
                params.append(datetime.now() + timedelta(days=30))
            else:
                # Generic parameter
                params.append(f"param_{worker_id}_{i}")
        
        return params

    async def _monitor_database_performance(self, pool: asyncpg.Pool, duration: int) -> Dict[str, Any]:
        """Monitor database-specific performance metrics"""
        monitoring_data = {
            "active_connections": [],
            "idle_connections": [],
            "queries_per_second": [],
            "timestamps": []
        }
        
        interval = 10  # Monitor every 10 seconds
        for _ in range(0, duration, interval):
            timestamp = datetime.now().isoformat()
            
            # Pool statistics
            pool_stats = {
                "size": pool.get_size(),
                "max_size": pool.get_max_size(),
                "min_size": pool.get_min_size()
            }
            
            monitoring_data["timestamps"].append(timestamp)
            monitoring_data["active_connections"].append(pool_stats["size"])
            monitoring_data["idle_connections"].append(pool_stats["max_size"] - pool_stats["size"])
            
            await asyncio.sleep(interval)
        
        return monitoring_data

    def _identify_breaking_point(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Identify system breaking point from stress test results"""
        breaking_point = None
        
        for load_level, metrics in results.items():
            if (metrics["avg_response_time"] > 5000 or 
                metrics["failure_rate"] > 0.10):
                breaking_point = {
                    "load_level": load_level,
                    "response_time_ms": metrics["avg_response_time"],
                    "failure_rate": metrics["failure_rate"],
                    "throughput_rps": metrics["requests_per_sec"]
                }
                break
        
        return breaking_point or {"message": "Breaking point not reached within test parameters"}

    def _calculate_spike_impact(self, baseline: Dict, spike: Dict) -> Dict[str, Any]:
        """Calculate the impact of traffic spike on system performance"""
        return {
            "response_time_degradation": ((spike["avg_response_time"] - baseline["avg_response_time"]) 
                                        / baseline["avg_response_time"]) * 100,
            "throughput_change": ((spike["rps"] - baseline["rps"]) 
                                / baseline["rps"]) * 100,
            "error_rate_increase": spike["error_rate"] - baseline["error_rate"]
        }

    def _generate_stress_test_recommendations(self, results: Dict, monitoring: Dict) -> List[str]:
        """Generate recommendations based on stress test results"""
        recommendations = []
        
        # Check CPU utilization
        max_cpu = max(monitoring["cpu_percent"])
        if max_cpu > 80:
            recommendations.append(f"High CPU utilization detected ({max_cpu}%). Consider horizontal scaling.")
        
        # Check memory usage
        max_memory = max(monitoring["memory_percent"])
        if max_memory > 85:
            recommendations.append(f"High memory usage detected ({max_memory}%). Investigate memory leaks.")
        
        # Check response times
        breaking_point = self._identify_breaking_point(results)
        if breaking_point and "load_level" in breaking_point:
            recommendations.append(f"System breaks at {breaking_point['load_level']}. "
                                 f"Current capacity limit identified.")
        
        return recommendations

    def _analyze_performance_degradation(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Analyze performance degradation over time during endurance test"""
        if len(metrics) < 2:
            return {"error": "Insufficient data for degradation analysis"}
        
        first_hour = [m for m in metrics if m["hour"] == 0]
        last_hour = [m for m in metrics if m["hour"] == max(m["hour"] for m in metrics)]
        
        if not first_hour or not last_hour:
            return {"error": "Incomplete hourly data"}
        
        first_avg_rt = statistics.mean([m["avg_response_time"] for m in first_hour])
        last_avg_rt = statistics.mean([m["avg_response_time"] for m in last_hour])
        
        return {
            "response_time_degradation_percent": ((last_avg_rt - first_avg_rt) / first_avg_rt) * 100,
            "initial_avg_response_time": first_avg_rt,
            "final_avg_response_time": last_avg_rt,
            "performance_trend": "degrading" if last_avg_rt > first_avg_rt else "stable"
        }

    def _calculate_stability_score(self, metrics: List[Dict]) -> float:
        """Calculate system stability score based on performance consistency"""
        if len(metrics) < 10:
            return 0.0
        
        response_times = [m["avg_response_time"] for m in metrics]
        rps_values = [m["rps"] for m in metrics]
        
        # Calculate coefficient of variation (lower is more stable)
        rt_cv = statistics.stdev(response_times) / statistics.mean(response_times) if response_times else 1
        rps_cv = statistics.stdev(rps_values) / statistics.mean(rps_values) if rps_values else 1
        
        # Stability score (0-100, higher is better)
        stability_score = max(0, 100 - (rt_cv + rps_cv) * 50)
        
        return round(stability_score, 2)