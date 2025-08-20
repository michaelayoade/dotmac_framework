"""
REST API usage examples for DotMac Analytics.
"""

import asyncio
from datetime import datetime, timedelta
from ..core.datetime_utils import utc_now, utc_now_iso

import httpx


class AnalyticsAPIClient:
    """Simple client for DotMac Analytics REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", tenant_id: str = "example_tenant"):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": tenant_id
        }

    async def health_check(self):
        """Check API health."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            return response.json()

    async def track_event(self, event_data: dict):
        """Track an event via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/events/track",
                headers=self.headers,
                json=event_data
            )
            return response.json()

    async def track_event_batch(self, events: list):
        """Track multiple events via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/events/track/batch",
                headers=self.headers,
                json={"events": events}
            )
            return response.json()

    async def query_events(self, query_params: dict):
        """Query events via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/events/query",
                headers=self.headers,
                json=query_params
            )
            return response.json()

    async def create_metric(self, metric_data: dict):
        """Create a metric via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/metrics/",
                headers=self.headers,
                json=metric_data
            )
            return response.json()

    async def record_metric_value(self, value_data: dict):
        """Record a metric value via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/metrics/values",
                headers=self.headers,
                json=value_data
            )
            return response.json()

    async def aggregate_metrics(self, aggregation_data: dict):
        """Aggregate metrics via API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/metrics/aggregate",
                headers=self.headers,
                json=aggregation_data
            )
            return response.json()


async def api_health_check_example():
    """Example of API health check."""
    print("=== API Health Check Example ===")

    api_client = AnalyticsAPIClient()

    try:
        health = await api_client.health_check()
        print(f"API Status: {health['status']}")
        print(f"Service: {health['service']}")
        print(f"Timestamp: {health['timestamp']}")
    except Exception as e:
        print(f"Health check failed: {e}")


async def api_event_tracking_example():
    """Example of event tracking via API."""
    print("\n=== API Event Tracking Example ===")

    api_client = AnalyticsAPIClient()

    # Track single event
    event_data = {
        "event_type": "page_view",
        "event_name": "home_page_view",
        "user_id": "api_user_123",
        "session_id": "api_session_456",
        "properties": {
            "page_url": "/api-example",
            "page_title": "API Example Page",
            "source": "api_demo"
        },
        "context": {
            "user_agent": "Analytics-API-Client/1.0",
            "ip_address": "127.0.0.1"
        }
    }

    try:
        result = await api_client.track_event(event_data)
        print(f"Single event tracked: {result['event_id']}")
    except Exception as e:
        print(f"Single event tracking failed: {e}")

    # Track batch of events
    batch_events = []
    for i in range(5):
        batch_events.append({
            "event_type": "click",
            "event_name": f"button_click_{i}",
            "user_id": f"api_user_{i}",
            "properties": {
                "button_id": f"btn_{i}",
                "button_text": f"Button {i}"
            },
            "timestamp": utc_now().isoformat()
        })

    try:
        batch_result = await api_client.track_event_batch(batch_events)
        print(f"Batch tracked: {batch_result['success_count']} events")
    except Exception as e:
        print(f"Batch event tracking failed: {e}")

    # Query events
    query_params = {
        "event_type": "page_view",
        "limit": 5,
        "start_time": (utc_now() - timedelta(hours=1)).isoformat(),
        "end_time": utc_now().isoformat()
    }

    try:
        query_result = await api_client.query_events(query_params)
        print(f"Found {query_result['count']} events in query")
        for event in query_result["events"][:3]:
            print(f"  - {event['event_name']} by {event['user_id']}")
    except Exception as e:
        print(f"Event query failed: {e}")


async def api_metrics_example():
    """Example of metrics management via API."""
    print("\n=== API Metrics Example ===")

    api_client = AnalyticsAPIClient()

    # Create a metric
    metric_data = {
        "name": "api_response_time",
        "display_name": "API Response Time",
        "metric_type": "histogram",
        "description": "Response time for API calls",
        "unit": "milliseconds",
        "dimensions": ["endpoint", "method"],
        "tags": {"category": "performance"}
    }

    try:
        metric_result = await api_client.create_metric(metric_data)
        metric_id = metric_result["metric_id"]
        print(f"Created metric: {metric_result['name']}")
    except Exception as e:
        print(f"Metric creation failed: {e}")
        return

    # Record metric values
    endpoints = ["/users", "/orders", "/products", "/analytics"]
    methods = ["GET", "POST", "PUT", "DELETE"]

    for i in range(20):
        value_data = {
            "metric_id": metric_id,
            "value": 50 + (i * 10) + (i % 5) * 20,  # Simulated response times
            "dimensions": {
                "endpoint": endpoints[i % len(endpoints)],
                "method": methods[i % len(methods)]
            },
            "context": {"request_id": f"req_{i}"}
        }

        try:
            await api_client.record_metric_value(value_data)
        except Exception as e:
            print(f"Failed to record value {i}: {e}")

    print("Recorded 20 metric values")

    # Aggregate metrics
    aggregation_data = {
        "metric_id": metric_id,
        "aggregation_method": "avg",
        "granularity": "hour",
        "start_time": (utc_now() - timedelta(hours=2)).isoformat(),
        "end_time": utc_now().isoformat(),
        "dimensions": ["endpoint"]
    }

    try:
        agg_result = await api_client.aggregate_metrics(aggregation_data)
        print(f"Aggregation returned {agg_result['count']} time buckets")
        for agg in agg_result["aggregates"][:3]:
            print(f"  {agg['time_bucket']}: avg = {agg['value']:.1f}ms")
    except Exception as e:
        print(f"Metric aggregation failed: {e}")


async def api_advanced_queries_example():
    """Example of advanced API queries."""
    print("\n=== Advanced API Queries Example ===")

    api_client = AnalyticsAPIClient()

    # Event aggregation
    aggregation_params = {
        "granularity": "hour",
        "start_time": (utc_now() - timedelta(hours=6)).isoformat(),
        "end_time": utc_now().isoformat(),
        "event_type": "click",
        "dimensions": ["button_id"]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_client.base_url}/events/aggregate",
                headers=api_client.headers,
                json=aggregation_params
            )
            agg_result = response.json()
            print(f"Event aggregation: {agg_result['count']} time buckets")
    except Exception as e:
        print(f"Event aggregation failed: {e}")

    # Funnel analysis
    funnel_params = {
        "funnel_steps": ["page_view", "click", "conversion"],
        "start_time": (utc_now() - timedelta(hours=24)).isoformat(),
        "end_time": utc_now().isoformat(),
        "user_id_field": "user_id"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_client.base_url}/events/funnel",
                headers=api_client.headers,
                json=funnel_params
            )
            funnel_result = response.json()
            print("Funnel analysis completed")
            for step, data in funnel_result.get("funnel_data", {}).items():
                print(f"  {step}: {data.get('count', 0)} users")
    except Exception as e:
        print(f"Funnel analysis failed: {e}")


async def api_error_handling_example():
    """Example of API error handling."""
    print("\n=== API Error Handling Example ===")

    api_client = AnalyticsAPIClient()

    # Test invalid event type
    invalid_event = {
        "event_type": "invalid_type",
        "event_name": "test_event"
    }

    try:
        await api_client.track_event(invalid_event)
    except Exception as e:
        print(f"Expected error for invalid event type: {e}")

    # Test invalid metric ID
    invalid_metric_value = {
        "metric_id": "non_existent_metric",
        "value": 100
    }

    try:
        await api_client.record_metric_value(invalid_metric_value)
    except Exception as e:
        print(f"Expected error for invalid metric ID: {e}")

    # Test malformed request
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_client.base_url}/events/track",
                headers=api_client.headers,
                json={"invalid": "data"}
            )
            if response.status_code >= 400:
                print(f"Expected error response: {response.status_code}")
    except Exception as e:
        print(f"Request error: {e}")


async def api_authentication_example():
    """Example of API authentication (simulated)."""
    print("\n=== API Authentication Example ===")

    # Simulate different authentication scenarios
    scenarios = [
        {"tenant_id": "valid_tenant", "expected": "success"},
        {"tenant_id": "", "expected": "error"},
        {"tenant_id": None, "expected": "error"}
    ]

    for scenario in scenarios:
        print(f"Testing with tenant_id: {scenario['tenant_id']}")

        headers = {"Content-Type": "application/json"}
        if scenario["tenant_id"]:
            headers["X-Tenant-ID"] = scenario["tenant_id"]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/health",
                    headers=headers
                )
                print(f"  Status: {response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")


async def api_performance_example():
    """Example of API performance testing."""
    print("\n=== API Performance Example ===")

    api_client = AnalyticsAPIClient()

    # Concurrent event tracking
    async def track_concurrent_events(count: int):
        tasks = []
        for i in range(count):
            event_data = {
                "event_type": "performance_test",
                "event_name": f"perf_event_{i}",
                "user_id": f"perf_user_{i}",
                "properties": {"test_id": "performance", "batch": count}
            }
            tasks.append(api_client.track_event(event_data))

        start_time = utc_now()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = utc_now()

        successful = sum(1 for r in results if not isinstance(r, Exception))
        duration = (end_time - start_time).total_seconds()

        print(f"Tracked {successful}/{count} events in {duration:.2f}s")
        print(f"Rate: {successful/duration:.1f} events/second")

    try:
        await track_concurrent_events(10)
    except Exception as e:
        print(f"Performance test failed: {e}")


async def main():
    """Run all API examples."""
    print("DotMac Analytics REST API Examples")
    print("=" * 50)
    print("Note: These examples assume the API server is running on localhost:8000")
    print("Start the server with: uvicorn dotmac_analytics.api.main:app --reload")
    print()

    try:
        await api_health_check_example()
        await api_event_tracking_example()
        await api_metrics_example()
        await api_advanced_queries_example()
        await api_error_handling_example()
        await api_authentication_example()
        await api_performance_example()

        print("\n" + "=" * 50)
        print("All API examples completed!")

    except Exception as e:
        print(f"\nAPI examples failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
