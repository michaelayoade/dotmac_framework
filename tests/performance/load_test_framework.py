#!/usr/bin/env python3
"""
DotMac Framework Load Testing Framework
=======================================
Comprehensive load and performance testing using Locust.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner


class DotMacLoadTestUser(HttpUser):
    """Base load test user for DotMac Framework."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Initialize user session."""
        self.tenant_id = f"load-test-tenant-{uuid4().hex[:8]}"
        self.user_token = None
        self.customer_id = None
        self.login()
    
    def login(self):
        """Authenticate user."""
        login_data = {
            "username": f"loadtest-{uuid4().hex[:8]}@example.com",
            "password": "LoadTest123!",
            "tenant_id": self.tenant_id
        }
        
        with self.client.post("/api/v2/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                self.user_token = response.json().get("access_token")
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    def get_headers(self):
        """Get authenticated headers."""
        if self.user_token:
            return {"Authorization": f"Bearer {self.user_token}"}
        return {}


class ISPAdminUser(DotMacLoadTestUser):
    """ISP Admin portal user simulation."""
    
    weight = 2  # Lower weight = fewer users
    
    @task(3)
    def view_dashboard(self):
        """Load admin dashboard."""
        with self.client.get("/api/v2/admin/dashboard", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard failed: {response.status_code}")
    
    @task(2)
    def list_customers(self):
        """List customers with pagination."""
        params = {"page": 1, "limit": 20}
        with self.client.get("/api/v2/admin/customers", params=params, headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Customer list failed: {response.status_code}")
    
    @task(1)
    def create_customer(self):
        """Create new customer."""
        customer_data = {
            "name": f"Load Test Customer {uuid4().hex[:8]}",
            "email": f"customer-{uuid4().hex[:8]}@example.com",
            "plan": "basic",
            "tenant_id": self.tenant_id
        }
        
        with self.client.post("/api/v2/admin/customers", json=customer_data, headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 201:
                self.customer_id = response.json().get("id")
                response.success()
            else:
                response.failure(f"Customer creation failed: {response.status_code}")
    
    @task(2)
    def view_network_status(self):
        """Check network monitoring dashboard."""
        with self.client.get("/api/v2/admin/network/status", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Network status failed: {response.status_code}")
    
    @task(1)
    def generate_report(self):
        """Generate usage report."""
        report_data = {
            "type": "usage",
            "date_range": "last_30_days",
            "format": "json"
        }
        
        with self.client.post("/api/v2/admin/reports/generate", json=report_data, headers=self.get_headers(), catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Report generation failed: {response.status_code}")


class CustomerPortalUser(DotMacLoadTestUser):
    """Customer portal user simulation."""
    
    weight = 5  # Higher weight = more users
    
    @task(4)
    def view_dashboard(self):
        """Load customer dashboard."""
        with self.client.get("/api/v2/customer/dashboard", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Customer dashboard failed: {response.status_code}")
    
    @task(3)
    def view_usage(self):
        """Check usage statistics."""
        with self.client.get("/api/v2/customer/usage", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Usage view failed: {response.status_code}")
    
    @task(2)
    def view_billing(self):
        """Check billing information."""
        with self.client.get("/api/v2/customer/billing", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Billing view failed: {response.status_code}")
    
    @task(1)
    def create_support_ticket(self):
        """Create support ticket."""
        ticket_data = {
            "title": f"Load Test Issue {uuid4().hex[:8]}",
            "description": "This is a load test support ticket.",
            "priority": "medium",
            "category": "technical"
        }
        
        with self.client.post("/api/v2/customer/support/tickets", json=ticket_data, headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Support ticket creation failed: {response.status_code}")
    
    @task(1)
    def update_profile(self):
        """Update customer profile."""
        profile_data = {
            "phone": f"+1555{uuid4().hex[:7]}",
            "preferences": {
                "notifications": True,
                "newsletter": False
            }
        }
        
        with self.client.patch("/api/v2/customer/profile", json=profile_data, headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Profile update failed: {response.status_code}")


class ResellerUser(DotMacLoadTestUser):
    """Reseller portal user simulation."""
    
    weight = 1  # Lowest weight = fewest users
    
    @task(3)
    def view_dashboard(self):
        """Load reseller dashboard."""
        with self.client.get("/api/v2/reseller/dashboard", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Reseller dashboard failed: {response.status_code}")
    
    @task(2)
    def view_commissions(self):
        """Check commission reports."""
        with self.client.get("/api/v2/reseller/commissions", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Commission view failed: {response.status_code}")
    
    @task(2)
    def manage_territory(self):
        """View territory management."""
        with self.client.get("/api/v2/reseller/territory", headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Territory view failed: {response.status_code}")
    
    @task(1)
    def create_lead(self):
        """Create new sales lead."""
        lead_data = {
            "name": f"Load Test Lead {uuid4().hex[:8]}",
            "email": f"lead-{uuid4().hex[:8]}@example.com",
            "phone": f"+1555{uuid4().hex[:7]}",
            "interest_level": "high",
            "source": "load_test"
        }
        
        with self.client.post("/api/v2/reseller/leads", json=lead_data, headers=self.get_headers(), catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Lead creation failed: {response.status_code}")


class APIOnlyUser(DotMacLoadTestUser):
    """API-only user for testing backend performance."""
    
    weight = 3
    
    @task(3)
    def health_check(self):
        """Basic health check."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(2)
    def metrics_endpoint(self):
        """Check metrics endpoint."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")
    
    @task(2)
    def api_info(self):
        """Get API information."""
        with self.client.get("/api/v2/info", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"API info failed: {response.status_code}")


# Load test configuration profiles
LOAD_TEST_PROFILES = {
    "smoke": {
        "users": 5,
        "spawn_rate": 1,
        "run_time": "2m",
        "description": "Light smoke test to verify basic functionality"
    },
    "normal": {
        "users": 50,
        "spawn_rate": 2,
        "run_time": "10m",
        "description": "Normal load simulation"
    },
    "peak": {
        "users": 200,
        "spawn_rate": 5,
        "run_time": "15m",
        "description": "Peak traffic simulation"
    },
    "stress": {
        "users": 500,
        "spawn_rate": 10,
        "run_time": "20m",
        "description": "Stress test to find breaking points"
    },
    "spike": {
        "users": 1000,
        "spawn_rate": 50,
        "run_time": "5m",
        "description": "Spike test with rapid user ramp-up"
    }
}


class LoadTestReporter:
    """Custom load test reporter."""
    
    def __init__(self):
        self.test_start_time = None
        self.test_results = []
        
    def on_test_start(self, environment, **kwargs):
        """Called when test starts."""
        self.test_start_time = datetime.now()
        print(f"🚀 Load test started at {self.test_start_time}")
        
    def on_test_stop(self, environment, **kwargs):
        """Called when test stops."""
        test_end_time = datetime.now()
        duration = test_end_time - self.test_start_time
        
        # Collect statistics
        stats = environment.stats
        
        report = {
            "test_info": {
                "start_time": self.test_start_time.isoformat(),
                "end_time": test_end_time.isoformat(),
                "duration": str(duration),
                "total_users": environment.parsed_options.num_users,
                "spawn_rate": environment.parsed_options.spawn_rate
            },
            "results": {
                "total_requests": stats.total.num_requests,
                "total_failures": stats.total.num_failures,
                "avg_response_time": stats.total.avg_response_time,
                "min_response_time": stats.total.min_response_time,
                "max_response_time": stats.total.max_response_time,
                "requests_per_second": stats.total.total_rps,
                "failure_rate": stats.total.fail_ratio
            },
            "endpoints": {}
        }
        
        # Add per-endpoint statistics
        for name, entry in stats.entries.items():
            if name != "Total":
                report["endpoints"][name] = {
                    "requests": entry.num_requests,
                    "failures": entry.num_failures,
                    "avg_response_time": entry.avg_response_time,
                    "min_response_time": entry.min_response_time,
                    "max_response_time": entry.max_response_time,
                    "rps": entry.total_rps,
                    "failure_rate": entry.fail_ratio
                }
        
        # Save report
        report_path = f"test-results/load-test-report-{test_end_time.strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("test-results", exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_summary(report)
        
        # Save HTML report
        self.generate_html_report(report, report_path.replace('.json', '.html'))
    
    def print_summary(self, report):
        """Print load test summary."""
        print("\n" + "="*60)
        print("⚡ DOTMAC FRAMEWORK - LOAD TEST REPORT")
        print("="*60)
        
        results = report["results"]
        test_info = report["test_info"]
        
        print(f"👥 Users: {test_info['total_users']}")
        print(f"🕐 Duration: {test_info['duration']}")
        print(f"📊 Total Requests: {results['total_requests']:,}")
        print(f"❌ Total Failures: {results['total_failures']:,}")
        print(f"📈 Requests/sec: {results['requests_per_second']:.2f}")
        print(f"⏱️  Avg Response Time: {results['avg_response_time']:.2f}ms")
        print(f"⚡ Min Response Time: {results['min_response_time']:.2f}ms")
        print(f"🐌 Max Response Time: {results['max_response_time']:.2f}ms")
        print(f"💥 Failure Rate: {results['failure_rate']*100:.2f}%")
        
        # Performance thresholds
        print("\n📊 Performance Analysis:")
        print("-" * 60)
        
        if results['avg_response_time'] < 500:
            print("✅ Average response time: EXCELLENT (< 500ms)")
        elif results['avg_response_time'] < 1000:
            print("⚠️  Average response time: GOOD (< 1s)")
        elif results['avg_response_time'] < 2000:
            print("⚠️  Average response time: ACCEPTABLE (< 2s)")
        else:
            print("❌ Average response time: POOR (> 2s)")
            
        if results['failure_rate'] < 0.01:
            print("✅ Failure rate: EXCELLENT (< 1%)")
        elif results['failure_rate'] < 0.05:
            print("⚠️  Failure rate: ACCEPTABLE (< 5%)")
        else:
            print("❌ Failure rate: HIGH (> 5%)")
            
        if results['requests_per_second'] > 100:
            print("✅ Throughput: EXCELLENT (> 100 RPS)")
        elif results['requests_per_second'] > 50:
            print("⚠️  Throughput: GOOD (> 50 RPS)")
        else:
            print("❌ Throughput: LOW (< 50 RPS)")
        
        print("\n" + "="*60)
    
    def generate_html_report(self, report, output_path):
        """Generate HTML load test report."""
        html_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DotMac Framework - Load Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; border-left: 4px solid #007bff; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; font-size: 12px; text-transform: uppercase; margin-top: 5px; }}
        .success {{ border-left-color: #28a745; }}
        .warning {{ border-left-color: #ffc107; }}
        .danger {{ border-left-color: #dc3545; }}
        .endpoints {{ margin-top: 30px; }}
        .endpoint {{ background: #f8f9fa; margin-bottom: 15px; padding: 15px; border-radius: 6px; }}
        .endpoint-name {{ font-weight: bold; font-size: 16px; margin-bottom: 10px; }}
        .endpoint-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ DotMac Framework - Load Test Report</h1>
            <p>Generated on {timestamp}</p>
            <p>Duration: {duration} | Users: {users} | Spawn Rate: {spawn_rate}/s</p>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{total_requests:,}</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric {failure_class}">
                <div class="metric-value">{total_failures:,}</div>
                <div class="metric-label">Failures</div>
            </div>
            <div class="metric">
                <div class="metric-value">{rps:.1f}</div>
                <div class="metric-label">Requests/sec</div>
            </div>
            <div class="metric {response_time_class}">
                <div class="metric-value">{avg_response_time:.0f}ms</div>
                <div class="metric-label">Avg Response</div>
            </div>
            <div class="metric {failure_rate_class}">
                <div class="metric-value">{failure_rate:.2f}%</div>
                <div class="metric-label">Failure Rate</div>
            </div>
        </div>
        
        <div class="endpoints">
            <h2>Endpoint Performance</h2>
            {endpoints_html}
        </div>
    </div>
</body>
</html>
        '''
        
        # Generate endpoint stats
        endpoints_html = ""
        for endpoint_name, stats in report["endpoints"].items():
            endpoints_html += f'''
            <div class="endpoint">
                <div class="endpoint-name">{endpoint_name}</div>
                <div class="endpoint-stats">
                    <div><strong>Requests:</strong> {stats["requests"]:,}</div>
                    <div><strong>Failures:</strong> {stats["failures"]:,}</div>
                    <div><strong>Avg Time:</strong> {stats["avg_response_time"]:.0f}ms</div>
                    <div><strong>Min Time:</strong> {stats["min_response_time"]:.0f}ms</div>
                    <div><strong>Max Time:</strong> {stats["max_response_time"]:.0f}ms</div>
                    <div><strong>RPS:</strong> {stats["rps"]:.1f}</div>
                </div>
            </div>
            '''
        
        # Determine CSS classes based on performance
        results = report["results"]
        
        failure_class = "success" if results["total_failures"] == 0 else "danger"
        response_time_class = "success" if results["avg_response_time"] < 500 else "warning" if results["avg_response_time"] < 1000 else "danger"
        failure_rate_class = "success" if results["failure_rate"] < 0.01 else "warning" if results["failure_rate"] < 0.05 else "danger"
        
        html_content = html_template.format(
            timestamp=report["test_info"]["end_time"],
            duration=report["test_info"]["duration"],
            users=report["test_info"]["total_users"],
            spawn_rate=report["test_info"]["spawn_rate"],
            total_requests=results["total_requests"],
            total_failures=results["total_failures"],
            rps=results["requests_per_second"],
            avg_response_time=results["avg_response_time"],
            failure_rate=results["failure_rate"] * 100,
            endpoints_html=endpoints_html,
            failure_class=failure_class,
            response_time_class=response_time_class,
            failure_rate_class=failure_rate_class
        )
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"✅ HTML report generated: {output_path}")


# Event listeners
reporter = LoadTestReporter()
events.test_start.add_listener(reporter.on_test_start)
events.test_stop.add_listener(reporter.on_test_stop)


def run_load_test(profile_name: str = "normal", host: str = "http://localhost:8000"):
    """Run load test with specified profile."""
    import subprocess
    import sys
    
    if profile_name not in LOAD_TEST_PROFILES:
        print(f"❌ Unknown profile: {profile_name}")
        print(f"Available profiles: {list(LOAD_TEST_PROFILES.keys())}")
        return 1
    
    profile = LOAD_TEST_PROFILES[profile_name]
    
    print(f"🚀 Starting load test: {profile_name}")
    print(f"📋 {profile['description']}")
    print(f"👥 Users: {profile['users']}")
    print(f"📈 Spawn rate: {profile['spawn_rate']}/s")
    print(f"⏱️  Duration: {profile['run_time']}")
    print(f"🎯 Host: {host}")
    
    # Run Locust
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", host,
        "--users", str(profile['users']),
        "--spawn-rate", str(profile['spawn_rate']),
        "--run-time", profile['run_time'],
        "--headless",
        "--html", f"test-results/locust-report-{profile_name}.html",
        "--csv", f"test-results/locust-report-{profile_name}"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("✅ Load test completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Load test failed: {e}")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="DotMac Framework Load Testing")
    parser.add_argument("--profile", default="normal", choices=LOAD_TEST_PROFILES.keys(),
                      help="Load test profile to run")
    parser.add_argument("--host", default="http://localhost:8000",
                      help="Target host for load testing")
    
    args = parser.parse_args()
    
    exit_code = run_load_test(args.profile, args.host)
    exit(exit_code)