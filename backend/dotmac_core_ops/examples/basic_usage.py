#!/usr/bin/env python3
"""
Basic usage examples for the DotMac Core Operations package.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotmac_core_ops.client import OperationsClient
from dotmac_core_ops.sdks import WorkflowSDK, TaskSDK, AutomationSDK
from dotmac_core_ops.sdks.workflow import WorkflowDefinition, WorkflowStep
from dotmac_core_ops.sdks.task import TaskDefinition
from dotmac_core_ops.sdks.automation import AutomationRule
from dotmac_core_ops.contracts.common_schemas import Priority


async def example_client_usage():
    """Example using the client SDK to interact with a remote operations platform."""
    print("=== Client SDK Example ===")

    # Note: This assumes the operations platform is running on localhost:8000
    async with OperationsClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",
        tenant_id="example-tenant"
    ) as client:
        try:
            # Check platform health
            health = await client.health_check()
            print(f"Platform status: {health['status']}")

            # Create a simple workflow
            workflow_id = await client.workflows.create_workflow(
                name="data-processing-pipeline",
                description="A simple data processing pipeline",
                definition={
                    "steps": [
                        {
                            "id": "extract",
                            "type": "action",
                            "action": "extract_data",
                            "timeout_seconds": 300
                        },
                        {
                            "id": "transform",
                            "type": "action",
                            "action": "transform_data",
                            "depends_on": ["extract"],
                            "timeout_seconds": 600
                        },
                        {
                            "id": "load",
                            "type": "action",
                            "action": "load_data",
                            "depends_on": ["transform"],
                            "timeout_seconds": 300
                        }
                    ]
                }
            )
            print(f"Created workflow: {workflow_id}")

            # Execute the workflow
            execution_id = await client.workflows.execute_workflow(
                workflow_id=workflow_id,
                input_data={
                    "source_table": "raw_data",
                    "target_table": "processed_data",
                    "batch_size": 1000
                }
            )
            print(f"Started workflow execution: {execution_id}")

            # Create a task
            task_id = await client.tasks.create_task(
                name="data-validation",
                description="Validate processed data quality",
                priority=Priority.HIGH,
                input_data={"table": "processed_data", "rules": ["not_null", "unique_id"]}
            )
            print(f"Created task: {task_id}")

            # Create an automation rule
            rule_id = await client.automation.create_rule(
                name="auto-cleanup",
                description="Automatically clean up old data",
                triggers=[
                    {"type": "schedule", "cron": "0 2 * * *"}  # Daily at 2 AM
                ],
                conditions=[
                    {"type": "disk_usage", "threshold": 80}
                ],
                actions=[
                    {"type": "cleanup", "target": "old_logs", "retention_days": 30}
                ]
            )
            print(f"Created automation rule: {rule_id}")

        except Exception as e:
            print(f"Error: {e}")


async def example_direct_sdk_usage():  # noqa: PLR0915
    """Example using SDKs directly without the API layer."""
    print("\n=== Direct SDK Example ===")

    # Initialize SDKs
    workflow_sdk = WorkflowSDK()
    task_sdk = TaskSDK()
    automation_sdk = AutomationSDK()

    # Start SDKs
    await workflow_sdk.start()
    await task_sdk.start()
    await automation_sdk.start()

    try:
        # Create a workflow definition
        workflow = WorkflowDefinition(
            id="example-etl-workflow",
            name="ETL Workflow",
            description="Extract, Transform, Load workflow example",
            steps=[
                WorkflowStep(
                    id="extract",
                    type="action",
                    action="extract_data",
                    timeout_seconds=300,
                    retry_policy={"max_retries": 3, "backoff_factor": 2}
                ),
                WorkflowStep(
                    id="validate",
                    type="action",
                    action="validate_data",
                    depends_on=["extract"],
                    timeout_seconds=120
                ),
                WorkflowStep(
                    id="transform",
                    type="action",
                    action="transform_data",
                    depends_on=["validate"],
                    timeout_seconds=600
                ),
                WorkflowStep(
                    id="load",
                    type="action",
                    action="load_data",
                    depends_on=["transform"],
                    timeout_seconds=300
                ),
                WorkflowStep(
                    id="notify_success",
                    type="condition",
                    condition="all_steps_completed",
                    depends_on=["load"]
                )
            ]
        )

        # Register the workflow
        workflow_id = await workflow_sdk.create_workflow(workflow)
        print(f"Created workflow: {workflow_id}")

        # Register step handlers
        @workflow_sdk.step_handler("extract_data")
        async def extract_data(context, input_data):
            print(f"Extracting data from {input_data.get('source', 'unknown')}")
            return {"records_extracted": 1000, "status": "success"}

        @workflow_sdk.step_handler("validate_data")
        async def validate_data(context, input_data):
            print("Validating extracted data")
            return {"validation_passed": True, "issues": []}

        @workflow_sdk.step_handler("transform_data")
        async def transform_data(context, input_data):
            print("Transforming data")
            return {"records_transformed": 950, "status": "success"}

        @workflow_sdk.step_handler("load_data")
        async def load_data(context, input_data):
            print("Loading data to target")
            return {"records_loaded": 950, "status": "success"}

        # Execute the workflow
        execution_id = await workflow_sdk.execute_workflow(
            workflow_id=workflow_id,
            input_data={
                "source": "production_db",
                "target": "data_warehouse",
                "batch_id": "batch_001"
            }
        )
        print(f"Started workflow execution: {execution_id}")

        # Create some tasks
        tasks = []
        for i in range(3):
            task = TaskDefinition(
                id=f"task-{i}",
                name=f"Processing Task {i}",
                description=f"Process batch {i}",
                priority=Priority.MEDIUM,
                timeout_seconds=180,
                retry_count=2,
                input_data={"batch_id": i, "records": 100 * (i + 1)}
            )
            task_id = await task_sdk.create_task(task)
            tasks.append(task_id)
            print(f"Created task: {task_id}")

        # Register task handler
        @task_sdk.task_handler("process_batch")
        async def process_batch(context, input_data):
            batch_id = input_data.get("batch_id", 0)
            records = input_data.get("records", 0)
            print(f"Processing batch {batch_id} with {records} records")
            await asyncio.sleep(1)  # Simulate processing
            return {"processed_records": records, "status": "completed"}

        # Create an automation rule
        rule = AutomationRule(
            id="monitoring-rule",
            name="System Monitoring",
            description="Monitor system health and take actions",
            enabled=True,
            triggers=[
                {"type": "metric", "metric": "cpu_usage", "threshold": 85},
                {"type": "metric", "metric": "memory_usage", "threshold": 90}
            ],
            conditions=[
                {"type": "time_window", "duration_minutes": 5}
            ],
            actions=[
                {"type": "alert", "channel": "slack", "message": "High resource usage detected"},
                {"type": "scale", "service": "worker", "action": "increase", "amount": 2}
            ]
        )

        rule_id = await automation_sdk.create_rule(rule)
        print(f"Created automation rule: {rule_id}")

        # Register automation handlers
        @automation_sdk.action_handler("alert")
        async def send_alert(context, action_data):
            channel = action_data.get("channel", "default")
            message = action_data.get("message", "Alert triggered")
            print(f"Sending alert to {channel}: {message}")
            return {"status": "sent", "channel": channel}

        @automation_sdk.action_handler("scale")
        async def scale_service(context, action_data):
            service = action_data.get("service", "unknown")
            action = action_data.get("action", "increase")
            amount = action_data.get("amount", 1)
            print(f"Scaling {service}: {action} by {amount}")
            return {"status": "scaled", "service": service, "new_instances": amount}

        # Simulate some processing time
        await asyncio.sleep(2)

        # Check workflow status
        execution = await workflow_sdk.get_execution(execution_id)
        if execution:
            print(f"Workflow execution status: {execution.status}")

        # Get task queue status
        queue_status = task_sdk.get_queue_status()
        print(f"Task queue status: {queue_status}")

    finally:
        # Stop SDKs
        await workflow_sdk.stop()
        await task_sdk.stop()
        await automation_sdk.stop()


async def example_complex_workflow():  # noqa: C901
    """Example of a more complex workflow with parallel execution and conditions."""
    print("\n=== Complex Workflow Example ===")

    workflow_sdk = WorkflowSDK()
    await workflow_sdk.start()

    try:
        # Define a complex workflow with parallel branches
        complex_workflow = WorkflowDefinition(
            id="complex-data-pipeline",
            name="Complex Data Pipeline",
            description="A complex pipeline with parallel processing and conditional logic",
            steps=[
                # Initial validation
                WorkflowStep(
                    id="validate_input",
                    type="action",
                    action="validate_input_data"
                ),

                # Parallel processing branches
                WorkflowStep(
                    id="process_customer_data",
                    type="action",
                    action="process_customers",
                    depends_on=["validate_input"]
                ),
                WorkflowStep(
                    id="process_order_data",
                    type="action",
                    action="process_orders",
                    depends_on=["validate_input"]
                ),
                WorkflowStep(
                    id="process_product_data",
                    type="action",
                    action="process_products",
                    depends_on=["validate_input"]
                ),

                # Data quality checks
                WorkflowStep(
                    id="quality_check",
                    type="action",
                    action="data_quality_check",
                    depends_on=["process_customer_data", "process_order_data", "process_product_data"]
                ),

                # Conditional steps based on quality check
                WorkflowStep(
                    id="proceed_check",
                    type="condition",
                    condition="quality_passed",
                    depends_on=["quality_check"]
                ),

                # Final processing if quality check passed
                WorkflowStep(
                    id="generate_reports",
                    type="action",
                    action="generate_reports",
                    depends_on=["proceed_check"]
                ),
                WorkflowStep(
                    id="send_notifications",
                    type="action",
                    action="send_notifications",
                    depends_on=["generate_reports"]
                ),

                # Error handling if quality check failed
                WorkflowStep(
                    id="handle_quality_failure",
                    type="action",
                    action="handle_failure",
                    condition="quality_failed",
                    depends_on=["quality_check"]
                )
            ]
        )

        workflow_id = await workflow_sdk.create_workflow(complex_workflow)
        print(f"Created complex workflow: {workflow_id}")

        # Register step handlers
        @workflow_sdk.step_handler("validate_input_data")
        async def validate_input(context, input_data):
            print("Validating input data...")
            return {"valid": True, "record_count": input_data.get("record_count", 1000)}

        @workflow_sdk.step_handler("process_customers")
        async def process_customers(context, input_data):
            print("Processing customer data...")
            await asyncio.sleep(1)  # Simulate processing
            return {"customers_processed": 500, "status": "success"}

        @workflow_sdk.step_handler("process_orders")
        async def process_orders(context, input_data):
            print("Processing order data...")
            await asyncio.sleep(1.5)  # Simulate processing
            return {"orders_processed": 1200, "status": "success"}

        @workflow_sdk.step_handler("process_products")
        async def process_products(context, input_data):
            print("Processing product data...")
            await asyncio.sleep(0.8)  # Simulate processing
            return {"products_processed": 300, "status": "success"}

        @workflow_sdk.step_handler("data_quality_check")
        async def quality_check(context, input_data):
            print("Performing data quality checks...")
            # Simulate quality check logic
            quality_score = 95  # Simulated score
            passed = quality_score >= 90
            return {
                "quality_score": quality_score,
                "passed": passed,
                "issues": [] if passed else ["data_completeness"]
            }

        @workflow_sdk.condition_handler("quality_passed")
        async def check_quality_passed(context, input_data):
            quality_result = context.get_step_result("quality_check")
            return quality_result and quality_result.get("passed", False)

        @workflow_sdk.condition_handler("quality_failed")
        async def check_quality_failed(context, input_data):
            quality_result = context.get_step_result("quality_check")
            return quality_result and not quality_result.get("passed", True)

        @workflow_sdk.step_handler("generate_reports")
        async def generate_reports(context, input_data):
            print("Generating reports...")
            return {"reports_generated": ["summary", "detailed", "quality"], "status": "success"}

        @workflow_sdk.step_handler("send_notifications")
        async def send_notifications(context, input_data):
            print("Sending notifications...")
            return {"notifications_sent": 3, "status": "success"}

        @workflow_sdk.step_handler("handle_failure")
        async def handle_failure(context, input_data):
            print("Handling quality check failure...")
            return {"action": "data_reprocessing_scheduled", "status": "handled"}

        # Execute the complex workflow
        execution_id = await workflow_sdk.execute_workflow(
            workflow_id=workflow_id,
            input_data={
                "source": "production",
                "record_count": 2000,
                "quality_threshold": 90
            }
        )
        print(f"Started complex workflow execution: {execution_id}")

        # Wait a bit for processing
        await asyncio.sleep(5)

        # Check final status
        execution = await workflow_sdk.get_execution(execution_id)
        if execution:
            print(f"Complex workflow execution status: {execution.status}")
            print(f"Completed steps: {len([s for s in execution.step_results if s.get('status') == 'completed'])}")

    finally:
        await workflow_sdk.stop()


async def main():
    """Run all examples."""
    print("DotMac Core Operations - Usage Examples")
    print("=" * 50)

    # Run direct SDK examples (these will always work)
    await example_direct_sdk_usage()
    await example_complex_workflow()

    # Try client SDK example (this requires the server to be running)
    try:
        await example_client_usage()
    except Exception as e:
        print(f"\nClient SDK example skipped (server not running): {e}")
        print("To run the client example, start the operations platform with: python main.py")


if __name__ == "__main__":
    asyncio.run(main())
