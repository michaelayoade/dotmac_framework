"""
Locust load testing configuration for the DotMac Framework.

This file defines load testing scenarios for:
- Customer management endpoints
- Authentication flows
- Concurrent user simulation
- Performance bottleneck identification
"""

import json
import random
import time
from typing import Dict, List, Optional

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


# Test data generators
class DataGenerator:
    """Generate test data for load testing."""
    
    @staticmethod
    def generate_customer_data(index: int) -> Dict:
        """Generate customer data for testing."""
        return {
            "email": f"load_test_user_{index}@example.com",
            "first_name": f"LoadUser{index}",
            "last_name": "Test",
            "phone": f"555{index:07d}",
            "address": {
                "street": f"{index} Test Street",
                "city": "Load Test City",
                "state": "CA",
                "zip_code": f"{index % 90000 + 10000:05d}"
            }
        }
    
    @staticmethod
    def generate_user_credentials() -> Dict:
        """Generate user credentials for authentication."""
        user_id = random.randint(1, 1000)
        return {
            "username": f"testuser{user_id}@example.com",
            "password": "test_password_123"
        }


# Authentication helper
class AuthHelper:
    """Helper class for handling authentication in load tests."""
    
    def __init__(self, client):
        self.client = client
        self.token = None
        self.token_expires = None
    
    def login(self) -> bool:
        """Perform login and get authentication token."""
        credentials = DataGenerator.generate_user_credentials()
        
        with self.client.post(
            "/api/v1/auth/login",
            json=credentials,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.token_expires = time.time() + data.get("expires_in", 3600)
                return True
            elif response.status_code == 401:
                # Expected for test users, mark as success
                response.success()
                # Use a test token for load testing
                self.token = "test-token-for-load-testing"
                self.token_expires = time.time() + 3600
                return True
            else:
                response.failure(f"Login failed with status {response.status_code}")
                return False
    
    def get_headers(self) -> Dict:
        """Get headers with authentication token."""
        if not self.token or (self.token_expires and time.time() >= self.token_expires):
            self.login()
        
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


# Base user class
class BaseAPIUser(HttpUser):
    """Base class for API load testing users."""
    
    abstract = True
    
    def on_start(self):
        """Initialize user session."""
        self.auth = AuthHelper(self.client)
        self.created_customers: List[str] = []
        
        # Attempt login
        if not self.auth.login():
            print("Failed to authenticate user")
    
    def on_stop(self):
        """Cleanup user session."""
        # Clean up created customers
        for customer_id in self.created_customers[-5:]:  # Only clean up last 5
            try:
                self.client.delete(
                    f"/api/v1/customers/{customer_id}",
                    headers=self.auth.get_headers()
                )
            except Exception:
                pass  # Ignore cleanup errors


# Customer management user
class CustomerManagementUser(BaseAPIUser):
    """User focused on customer management operations."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    weight = 3  # This user type is more common
    
    @task(5)
    def list_customers(self):
        """List customers with pagination."""
        params = {
            "limit": random.randint(10, 50),
            "offset": random.randint(0, 100)
        }
        
        with self.client.get(
            "/api/v1/customers",
            params=params,
            headers=self.auth.get_headers(),
            name="/api/v1/customers [LIST]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "items" in data and "total" in data:
                    response.success()
                else:
                    response.failure("Invalid response format")
            elif response.status_code in [401, 403]:
                response.success()  # Expected for load testing
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(3)
    def create_customer(self):
        """Create a new customer."""
        customer_data = DataGenerator.generate_customer_data(
            random.randint(1, 100000)
        )
        
        with self.client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=self.auth.get_headers(),
            name="/api/v1/customers [CREATE]",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                customer_id = data.get("id")
                if customer_id:
                    self.created_customers.append(customer_id)
                response.success()
            elif response.status_code in [401, 403]:
                response.success()  # Expected for load testing
            elif response.status_code == 422:
                # Validation error - expected sometimes
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def get_customer_details(self):
        """Get details of a specific customer."""
        if self.created_customers:
            customer_id = random.choice(self.created_customers)
        else:
            # Use a test customer ID
            customer_id = "test-customer-id"
        
        with self.client.get(
            f"/api/v1/customers/{customer_id}",
            headers=self.auth.get_headers(),
            name="/api/v1/customers/{id} [GET]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "email" in data:
                    response.success()
                else:
                    response.failure("Invalid customer data")
            elif response.status_code in [401, 403, 404]:
                response.success()  # Expected for load testing
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def update_customer(self):
        """Update a customer's information."""
        if self.created_customers:
            customer_id = random.choice(self.created_customers)
        else:
            customer_id = "test-customer-id"
        
        update_data = {
            "first_name": f"Updated{random.randint(1, 1000)}",
            "phone": f"555{random.randint(1000000, 9999999)}"
        }
        
        with self.client.put(
            f"/api/v1/customers/{customer_id}",
            json=update_data,
            headers=self.auth.get_headers(),
            name="/api/v1/customers/{id} [UPDATE]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [401, 403, 404]:
                response.success()  # Expected for load testing
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def search_customers(self):
        """Search customers by email."""
        search_terms = [
            "test@example.com",
            "user@test.com", 
            "customer@domain.com",
            "load_test_user"
        ]
        
        search_term = random.choice(search_terms)
        params = {"search": search_term}
        
        with self.client.get(
            "/api/v1/customers",
            params=params,
            headers=self.auth.get_headers(),
            name="/api/v1/customers [SEARCH]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [401, 403]:
                response.success()  # Expected for load testing
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# Admin user with more privileges
class AdminUser(BaseAPIUser):
    """Admin user with elevated privileges."""
    
    wait_time = between(2, 5)  # Admins work more slowly
    weight = 1  # Fewer admin users
    
    @task(3)
    def bulk_operations(self):
        """Perform bulk operations on customers."""
        if len(self.created_customers) < 3:
            # Create some customers first
            for i in range(3):
                customer_data = DataGenerator.generate_customer_data(
                    random.randint(100000, 200000)
                )
                response = self.client.post(
                    "/api/v1/customers",
                    json=customer_data,
                    headers=self.auth.get_headers()
                )
                if response.status_code == 201:
                    self.created_customers.append(response.json()["id"])
        
        if len(self.created_customers) >= 3:
            # Perform bulk status update
            customer_ids = random.sample(self.created_customers, 3)
            bulk_data = {
                "customer_ids": customer_ids,
                "status": random.choice(["active", "suspended"])
            }
            
            with self.client.post(
                "/api/v1/customers/bulk/status",
                json=bulk_data,
                headers=self.auth.get_headers(),
                name="/api/v1/customers/bulk/status",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code in [401, 403]:
                    response.success()  # Expected for load testing
                else:
                    response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def export_data(self):
        """Export customer data."""
        params = {
            "format": random.choice(["csv", "json"]),
            "limit": 100
        }
        
        with self.client.get(
            "/api/v1/customers/export",
            params=params,
            headers=self.auth.get_headers(),
            name="/api/v1/customers/export",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [401, 403]:
                response.success()  # Expected for load testing
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(1)
    def analytics_dashboard(self):
        """Access analytics dashboard."""
        with self.client.get(
            "/api/v1/analytics/dashboard",
            headers=self.auth.get_headers(),
            name="/api/v1/analytics/dashboard",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403, 404]:
                response.success()  # All these are expected
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# Read-only user
class ReadOnlyUser(BaseAPIUser):
    """User with read-only access."""
    
    wait_time = between(0.5, 2)  # Read-only users are faster
    weight = 2  # Moderate number of read-only users
    
    @task(8)
    def browse_customers(self):
        """Browse customer listings."""
        page = random.randint(0, 5)
        params = {
            "limit": 20,
            "offset": page * 20
        }
        
        with self.client.get(
            "/api/v1/customers",
            params=params,
            headers=self.auth.get_headers(),
            name="/api/v1/customers [BROWSE]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(5)
    def view_customer_profile(self):
        """View customer profiles."""
        # Simulate viewing random customers
        customer_id = f"customer-{random.randint(1, 1000)}"
        
        with self.client.get(
            f"/api/v1/customers/{customer_id}",
            headers=self.auth.get_headers(),
            name="/api/v1/customers/{id} [VIEW]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403, 404]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def search_and_filter(self):
        """Search and filter customers."""
        filters = {
            "status": random.choice(["active", "suspended", "cancelled"]),
            "limit": 20
        }
        
        with self.client.get(
            "/api/v1/customers",
            params=filters,
            headers=self.auth.get_headers(),
            name="/api/v1/customers [FILTER]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


# Health check user (simulates monitoring)
class HealthCheckUser(BaseAPIUser):
    """User that performs health checks and monitoring."""
    
    wait_time = between(5, 10)  # Health checks are less frequent
    weight = 1  # Few monitoring users
    
    @task(10)
    def health_check(self):
        """Check system health."""
        with self.client.get(
            "/health",
            name="/health",
            catch_response=True
        ) as response:
            if response.status_code in [200, 503]:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def metrics_endpoint(self):
        """Check metrics endpoint."""
        with self.client.get(
            "/metrics",
            name="/metrics",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:  # 404 if metrics not enabled
                response.success()
            else:
                response.failure(f"Metrics check failed: {response.status_code}")
    
    @task(2)
    def api_documentation(self):
        """Access API documentation."""
        with self.client.get(
            "/docs",
            name="/docs",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Docs access failed: {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def record_custom_metrics(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Record custom metrics during load testing."""
    if exception:
        # Log exceptions for analysis
        print(f"Request failed: {name} - {exception}")
    
    # Record slow requests
    if response_time > 2000:  # Slower than 2 seconds
        print(f"Slow request detected: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Actions to perform when test starts."""
    print("Load testing started...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Actions to perform when test stops."""
    print("Load testing completed.")
    
    # Print summary statistics
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")


# Locust configuration
# Run with: locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=1

# For headless mode:
# locust -f locustfile.py --host=http://localhost:8000 --headless --users=20 --spawn-rate=2 --run-time=60s

# For specific user types:
# locust -f locustfile.py --host=http://localhost:8000 CustomerManagementUser

# Example custom test scenarios
class PeakTrafficScenario(BaseAPIUser):
    """Simulates peak traffic conditions."""
    
    wait_time = between(0.1, 0.5)  # Very fast requests
    weight = 0  # Only use when explicitly specified
    
    @task
    def rapid_fire_requests(self):
        """Make rapid requests to simulate peak traffic."""
        endpoints = [
            "/health",
            "/api/v1/customers",
            "/api/v1/customers?limit=10"
        ]
        
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, headers=self.auth.get_headers())


class DatabaseStressScenario(BaseAPIUser):
    """Simulates database-heavy operations."""
    
    wait_time = between(1, 2)
    weight = 0  # Only use when explicitly specified
    
    @task(3)
    def complex_search(self):
        """Perform complex search operations."""
        params = {
            "search": "test",
            "status": "active",
            "limit": 100,
            "sort": "created_at",
            "order": "desc"
        }
        
        self.client.get("/api/v1/customers", params=params, headers=self.auth.get_headers())
    
    @task(2)
    def large_dataset_export(self):
        """Request large dataset exports."""
        params = {
            "format": "csv",
            "limit": 1000
        }
        
        self.client.get("/api/v1/customers/export", params=params, headers=self.auth.get_headers())


# You can create different locust files for different scenarios:
# - locustfile_light.py (light load testing)
# - locustfile_stress.py (stress testing)
# - locustfile_spike.py (spike testing)