"""
Basic usage examples for DotMac Analytics SDK.
"""

import asyncio
from datetime import datetime, timedelta
from ..core.datetime_utils import utc_now, utc_now_iso

from dotmac_analytics import AnalyticsClient
from dotmac_analytics.models.enums import (
    AggregationMethod,
    EventType,
    MetricType,
    TimeGranularity,
)


async def basic_event_tracking_example():
    """Example of basic event tracking."""
    print("=== Basic Event Tracking Example ===")

    async with AnalyticsClient("example_tenant") as client:
        # Initialize tenant with default metrics
        init_result = await client.initialize_tenant()
        print(f"Tenant initialization: {init_result['status']}")

        # Track page view events
        for i in range(5):
            result = await client.events.track_page_view(
                page_url=f"/page-{i}",
                page_title=f"Page {i}",
                user_id=f"user_{i % 3}",  # 3 different users
                properties={
                    "category": "example",
                    "load_time": 1.2 + (i * 0.1)
                }
            )
            print(f"Tracked page view {i}: {result['event_id']}")

        # Track some click events
        for i in range(3):
            result = await client.events.track_click(
                element_id=f"button-{i}",
                element_text=f"Click Button {i}",
                user_id=f"user_{i}",
                properties={"button_type": "primary"}
            )
            print(f"Tracked click {i}: {result['event_id']}")

        # Query recent events
        events = await client.events.get_events(
            event_type=EventType.PAGE_VIEW,
            limit=3
        )
        print(f"\nFound {len(events)} recent page view events")
        for event in events:
            print(f"  - {event['event_name']} by {event['user_id']} at {event['timestamp']}")


async def metrics_management_example():
    """Example of metrics creation and value recording."""
    print("\n=== Metrics Management Example ===")

    async with AnalyticsClient("example_tenant") as client:
        # Create custom metrics
        metrics_to_create = [
            {
                "name": "api_requests",
                "display_name": "API Requests",
                "metric_type": MetricType.COUNTER,
                "description": "Total API requests",
                "unit": "requests"
            },
            {
                "name": "response_time",
                "display_name": "Response Time",
                "metric_type": MetricType.HISTOGRAM,
                "description": "API response time",
                "unit": "milliseconds"
            },
            {
                "name": "active_connections",
                "display_name": "Active Connections",
                "metric_type": MetricType.GAUGE,
                "description": "Current active connections",
                "unit": "connections"
            }
        ]

        created_metrics = []
        for metric_config in metrics_to_create:
            try:
                result = await client.metrics.create_metric(**metric_config)
                created_metrics.append(result)
                print(f"Created metric: {result['name']}")
            except Exception as e:
                print(f"Metric {metric_config['name']} might already exist: {e}")

        # Record metric values
        print("\nRecording metric values...")

        # API requests (counter)
        for i in range(10):
            await client.metrics.increment("api_requests", value=1)
        print("Recorded 10 API requests")

        # Response times (histogram)
        response_times = [120, 150, 95, 200, 180, 110, 165, 140, 175, 130]
        for rt in response_times:
            await client.metrics.record_timing("response_time", duration_ms=rt)
        print(f"Recorded {len(response_times)} response times")

        # Active connections (gauge)
        connection_values = [25, 30, 28, 35, 32, 29, 33, 31]
        for conn in connection_values:
            await client.metrics.set_gauge("active_connections", value=conn)
        print(f"Recorded {len(connection_values)} connection values")

        # Get metrics list
        metrics = await client.metrics.get_metrics(limit=10)
        print(f"\nFound {len(metrics)} metrics:")
        for metric in metrics:
            print(f"  - {metric['display_name']} ({metric['metric_type']})")


async def dashboard_creation_example():
    """Example of creating dashboards and widgets."""
    print("\n=== Dashboard Creation Example ===")

    async with AnalyticsClient("example_tenant") as client:
        # Create a dashboard
        dashboard_result = await client.dashboards.create_dashboard(
            name="operations_dashboard",
            display_name="Operations Dashboard",
            description="Real-time operations monitoring",
            category="operations",
            layout={
                "columns": 12,
                "rows": 8,
                "theme": "dark"
            }
        )
        dashboard_id = dashboard_result["dashboard_id"]
        print(f"Created dashboard: {dashboard_result['display_name']}")

        # Create widgets for the dashboard
        widgets_config = [
            {
                "name": "api_requests_chart",
                "title": "API Requests Over Time",
                "widget_type": "line_chart",
                "query_config": {
                    "metric": "api_requests",
                    "aggregation": "sum",
                    "granularity": "hour"
                },
                "position_x": 0,
                "position_y": 0,
                "width": 6,
                "height": 3
            },
            {
                "name": "response_time_chart",
                "title": "Average Response Time",
                "widget_type": "area_chart",
                "query_config": {
                    "metric": "response_time",
                    "aggregation": "avg",
                    "granularity": "minute"
                },
                "position_x": 6,
                "position_y": 0,
                "width": 6,
                "height": 3
            },
            {
                "name": "active_connections_gauge",
                "title": "Active Connections",
                "widget_type": "gauge",
                "query_config": {
                    "metric": "active_connections",
                    "aggregation": "last"
                },
                "position_x": 0,
                "position_y": 3,
                "width": 4,
                "height": 2
            }
        ]

        for widget_config in widgets_config:
            result = await client.dashboards.create_widget(
                dashboard_id=dashboard_id,
                **widget_config
            )
            print(f"Created widget: {result['title']}")


async def reporting_example():
    """Example of creating and generating reports."""
    print("\n=== Reporting Example ===")

    async with AnalyticsClient("example_tenant") as client:
        # Create a report
        report_result = await client.reports.create_report(
            name="daily_analytics_report",
            display_name="Daily Analytics Report",
            report_type="analytics",
            description="Daily summary of key metrics",
            query_config={
                "metrics": ["api_requests", "response_time", "active_connections"],
                "time_range": "24h",
                "aggregation": "daily"
            },
            template_config={
                "format": "pdf",
                "include_charts": True,
                "include_summary": True
            }
        )
        report_id = report_result["report_id"]
        print(f"Created report: {report_result['display_name']}")

        # Generate the report
        execution_result = await client.reports.generate_report(report_id)
        print(f"Generated report execution: {execution_result['execution_id']}")
        print(f"Report status: {execution_result['status']}")
        print(f"Output files: {execution_result['output_files']}")

        # Subscribe to report notifications
        subscription_result = await client.reports.subscribe_to_report(
            report_id=report_id,
            user_id="admin_user",
            email="admin@example.com",
            delivery_method="email",
            preferred_format="pdf"
        )
        print(f"Created subscription: {subscription_result['subscription_id']}")


async def segmentation_example():
    """Example of customer segmentation."""
    print("\n=== Customer Segmentation Example ===")

    async with AnalyticsClient("example_tenant") as client:
        # Create user segments
        segments_config = [
            {
                "name": "active_users",
                "display_name": "Active Users",
                "entity_type": "user",
                "description": "Users active in the last 7 days",
                "category": "engagement"
            },
            {
                "name": "power_users",
                "display_name": "Power Users",
                "entity_type": "user",
                "description": "Users with high API usage",
                "category": "usage"
            }
        ]

        created_segments = []
        for segment_config in segments_config:
            result = await client.segments.create_segment(**segment_config)
            created_segments.append(result)
            print(f"Created segment: {result['display_name']}")

        # Add rules to segments
        from dotmac_analytics.models.enums import SegmentOperator

        # Active users: last activity within 7 days
        await client.segments.add_segment_rule(
            segment_id=created_segments[0]["segment_id"],
            field_name="last_activity",
            operator=SegmentOperator.GREATER_THAN,
            value=(utc_now() - timedelta(days=7)).isoformat()
        )
        print("Added rule to active_users segment")

        # Power users: more than 100 API requests
        await client.segments.add_segment_rule(
            segment_id=created_segments[1]["segment_id"],
            field_name="api_request_count",
            operator=SegmentOperator.GREATER_THAN,
            value=100
        )
        print("Added rule to power_users segment")


async def data_analysis_example():
    """Example of data analysis and aggregation."""
    print("\n=== Data Analysis Example ===")

    async with AnalyticsClient("example_tenant") as client:
        # Aggregate events by time
        end_time = utc_now()
        start_time = end_time - timedelta(hours=24)

        event_aggregates = await client.events.aggregate(
            granularity=TimeGranularity.HOUR,
            start_time=start_time,
            end_time=end_time,
            event_type=EventType.PAGE_VIEW
        )

        print(f"Event aggregation results ({len(event_aggregates)} time buckets):")
        for aggregate in event_aggregates[-5:]:  # Show last 5 hours
            print(f"  {aggregate['time_bucket']}: {aggregate['event_count']} events, "
                  f"{aggregate['unique_users']} unique users")

        # Aggregate metrics
        try:
            metric_aggregates = await client.metrics.aggregate(
                metric_id="api_requests",
                aggregation_method=AggregationMethod.SUM,
                granularity=TimeGranularity.HOUR,
                start_time=start_time,
                end_time=end_time
            )

            print(f"\nMetric aggregation results ({len(metric_aggregates)} time buckets):")
            for aggregate in metric_aggregates[-3:]:  # Show last 3 hours
                print(f"  {aggregate['time_bucket']}: {aggregate['value']} total requests")

        except Exception as e:
            print(f"Metric aggregation skipped: {e}")

        # Funnel analysis
        funnel_steps = ["page_view", "click", "conversion"]
        try:
            funnel_result = await client.events.funnel_analysis(
                funnel_steps=funnel_steps,
                start_time=start_time,
                end_time=end_time
            )

            print("\nFunnel analysis results:")
            for step, data in funnel_result["funnel_data"].items():
                print(f"  {step}: {data['count']} users "
                      f"({data['conversion_rate']:.1%} conversion)")

        except Exception as e:
            print(f"Funnel analysis skipped: {e}")


async def main():
    """Run all examples."""
    print("DotMac Analytics SDK Examples")
    print("=" * 50)

    try:
        await basic_event_tracking_example()
        await metrics_management_example()
        await dashboard_creation_example()
        await reporting_example()
        await segmentation_example()
        await data_analysis_example()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"\nExample failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
