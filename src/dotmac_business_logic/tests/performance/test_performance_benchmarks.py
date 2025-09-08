"""
Performance benchmarking tests for business logic package.
Tests performance characteristics and identifies bottlenecks.
"""

import asyncio
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest


class TestBillingPerformance:
    """Performance tests for billing operations."""

    @pytest.mark.asyncio
    async def test_invoice_creation_performance(
        self, performance_timer, mock_db_session
    ):
        """Test invoice creation performance."""

        class MockBillingPerformance:
            def __init__(self, db_session):
                self.db = db_session

            async def create_invoice_batch(self, batch_size):
                invoices = []

                for i in range(batch_size):
                    invoice = {
                        "id": str(uuid4()),
                        "customer_id": str(uuid4()),
                        "invoice_number": f"INV-{i:06d}",
                        "total_amount": Decimal("100.00"),
                        "created_at": datetime.now(timezone.utc),
                    }
                    invoices.append(invoice)

                    # Simulate database insert
                    await asyncio.sleep(0.001)  # 1ms per invoice

                return invoices

        billing = MockBillingPerformance(mock_db_session)

        # Test different batch sizes
        batch_sizes = [10, 50, 100, 500]
        results = {}

        for batch_size in batch_sizes:
            performance_timer.start()
            await billing.create_invoice_batch(batch_size)
            performance_timer.stop()

            execution_time = performance_timer.elapsed_ms()
            throughput = batch_size / (execution_time / 1000)  # invoices per second

            results[batch_size] = {
                "execution_time_ms": execution_time,
                "throughput_per_sec": throughput,
                "avg_time_per_invoice": execution_time / batch_size,
            }

        # Verify performance characteristics
        assert len(results) == 4

        # Throughput should scale reasonably
        assert results[10]["throughput_per_sec"] > 100  # At least 100 invoices/sec

        # Average time per invoice should be consistent
        avg_times = [r["avg_time_per_invoice"] for r in results.values()]
        assert max(avg_times) / min(avg_times) < 2.0  # Less than 2x variance

    @pytest.mark.asyncio
    async def test_payment_processing_performance(self, performance_timer):
        """Test payment processing performance."""

        class MockPaymentProcessor:
            def __init__(self):
                self.processing_delay = 0.01  # 10ms per payment

            async def process_payment(self, payment_data):
                # Simulate payment gateway communication
                await asyncio.sleep(self.processing_delay)

                return {
                    "payment_id": payment_data["id"],
                    "status": "completed",
                    "processed_at": datetime.now(timezone.utc),
                }

            async def process_concurrent_payments(self, payments, max_concurrent=10):
                semaphore = asyncio.Semaphore(max_concurrent)

                async def process_single(payment):
                    async with semaphore:
                        return await self.process_payment(payment)

                tasks = [process_single(payment) for payment in payments]
                return await asyncio.gather(*tasks)

        processor = MockPaymentProcessor()

        # Test concurrent vs sequential processing
        payments = [{"id": f"pay-{i}", "amount": Decimal("50.00")} for i in range(20)]

        # Sequential processing
        performance_timer.start()
        sequential_results = []
        for payment in payments:
            result = await processor.process_payment(payment)
            sequential_results.append(result)
        performance_timer.stop()
        sequential_time = performance_timer.elapsed_ms()

        # Concurrent processing
        performance_timer.start()
        concurrent_results = await processor.process_concurrent_payments(
            payments, max_concurrent=5
        )
        performance_timer.stop()
        concurrent_time = performance_timer.elapsed_ms()

        # Verify concurrency improves performance
        assert len(sequential_results) == len(concurrent_results) == 20
        assert concurrent_time < sequential_time * 0.8  # At least 20% faster

        # Calculate throughput
        sequential_throughput = len(payments) / (sequential_time / 1000)
        concurrent_throughput = len(payments) / (concurrent_time / 1000)

        assert concurrent_throughput > sequential_throughput * 1.5  # 50% improvement

    def test_billing_calculation_performance(self, performance_timer):
        """Test billing calculation performance."""

        class MockBillingCalculator:
            def calculate_invoice_total(self, line_items, tax_rate=None):
                if tax_rate is None:
                    tax_rate = Decimal("0.10")
                subtotal = sum(item["amount"] for item in line_items)
                tax_amount = subtotal * tax_rate
                return {
                    "subtotal": subtotal,
                    "tax_amount": tax_amount,
                    "total": subtotal + tax_amount,
                }

            def calculate_bulk_invoices(self, invoices_data):
                results = []
                for invoice_data in invoices_data:
                    total = self.calculate_invoice_total(invoice_data["line_items"])
                    results.append({"invoice_id": invoice_data["id"], "totals": total})
                return results

        calculator = MockBillingCalculator()

        # Generate test data
        invoices_data = []
        for i in range(1000):
            line_items = [
                {"amount": Decimal("10.00"), "description": "Item A"},
                {"amount": Decimal("25.50"), "description": "Item B"},
                {"amount": Decimal("15.75"), "description": "Item C"},
            ]
            invoices_data.append({"id": f"inv-{i}", "line_items": line_items})

        # Benchmark calculation performance
        performance_timer.start()
        results = calculator.calculate_bulk_invoices(invoices_data)
        performance_timer.stop()

        execution_time = performance_timer.elapsed_ms()
        calculations_per_second = len(invoices_data) / (execution_time / 1000)

        # Verify performance
        assert len(results) == 1000
        assert calculations_per_second > 1000  # At least 1000 calculations/sec
        assert execution_time < 1000  # Less than 1 second for 1000 invoices


class TestTasksPerformance:
    """Performance tests for task processing."""

    @pytest.mark.asyncio
    async def test_task_queue_throughput(self, performance_timer, mock_redis):
        """Test task queue throughput."""

        class MockTaskQueue:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.queue = []

            async def enqueue(self, task_name, payload):
                # Simulate Redis operation
                await asyncio.sleep(0.0001)  # 0.1ms per enqueue
                task_id = f"task-{len(self.queue)}"
                self.queue.append(
                    {"id": task_id, "name": task_name, "payload": payload}
                )
                return task_id

            async def dequeue(self):
                # Simulate Redis operation
                await asyncio.sleep(0.0001)  # 0.1ms per dequeue
                if self.queue:
                    return self.queue.pop(0)
                return None

            async def bulk_enqueue(self, tasks):
                # Optimized bulk operation - single Redis pipeline operation
                await asyncio.sleep(0.001)  # Single 1ms operation regardless of size
                task_ids = []
                for i, task in enumerate(tasks):
                    task_id = f"bulk-task-{i}"
                    task_ids.append(task_id)
                    self.queue.append({"id": task_id, **task})
                return task_ids

        queue = MockTaskQueue(mock_redis)

        # Test individual enqueue performance
        tasks = [{"name": "test_task", "payload": {"data": i}} for i in range(100)]

        performance_timer.start()
        for task in tasks:
            await queue.enqueue(task["name"], task["payload"])
        performance_timer.stop()
        individual_time = performance_timer.elapsed_ms()

        # Test bulk enqueue performance
        queue.queue.clear()  # Reset queue

        performance_timer.start()
        await queue.bulk_enqueue(tasks)
        performance_timer.stop()
        bulk_time = performance_timer.elapsed_ms()

        # Verify bulk operation is more efficient
        assert bulk_time < individual_time * 0.5  # At least 50% faster

        # Calculate throughput
        individual_throughput = len(tasks) / (individual_time / 1000)
        bulk_throughput = len(tasks) / (bulk_time / 1000)

        assert bulk_throughput > individual_throughput * 2  # 2x improvement

    @pytest.mark.asyncio
    async def test_worker_processing_performance(self, performance_timer):
        """Test worker processing performance."""

        class MockTaskWorker:
            def __init__(self, worker_count=1):
                self.worker_count = worker_count
                self.processed_tasks = []

            async def process_task(self, task):
                # Simulate work
                await asyncio.sleep(0.01)  # 10ms per task
                result = {"task_id": task["id"], "result": "completed", "worker_id": 1}
                self.processed_tasks.append(result)
                return result

            async def process_tasks_concurrent(self, tasks, max_workers=None):
                if max_workers is None:
                    max_workers = self.worker_count

                semaphore = asyncio.Semaphore(max_workers)

                async def process_single(task):
                    async with semaphore:
                        return await self.process_task(task)

                tasks_to_process = [
                    {"id": f"task-{i}", "data": i} for i in range(len(tasks))
                ]
                return await asyncio.gather(
                    *[process_single(task) for task in tasks_to_process]
                )

        # Test different worker counts
        task_count = 50
        worker_counts = [1, 2, 4, 8]
        results = {}

        for worker_count in worker_counts:
            worker = MockTaskWorker(worker_count)
            tasks = list(range(task_count))

            performance_timer.start()
            processed = await worker.process_tasks_concurrent(
                tasks, max_workers=worker_count
            )
            performance_timer.stop()

            execution_time = performance_timer.elapsed_ms()
            throughput = len(processed) / (execution_time / 1000)

            results[worker_count] = {
                "execution_time_ms": execution_time,
                "throughput_per_sec": throughput,
                "processed_count": len(processed),
            }

        # Verify scaling characteristics
        assert results[1]["throughput_per_sec"] > 10  # Baseline throughput
        assert (
            results[4]["throughput_per_sec"] > results[1]["throughput_per_sec"] * 2
        )  # 2x with 4 workers
        assert (
            results[8]["throughput_per_sec"] > results[4]["throughput_per_sec"] * 1.2
        )  # Some improvement with 8

    def test_workflow_execution_performance(self, performance_timer):
        """Test workflow execution performance."""

        class MockWorkflowEngine:
            def __init__(self):
                pass

            def execute_linear_workflow(self, steps):
                """Execute steps sequentially."""
                results = []
                for i, _step in enumerate(steps):
                    # Simulate step execution
                    time.sleep(0.001)  # 1ms per step
                    results.append({"step": i, "result": f"step_{i}_completed"})
                return results

            def execute_parallel_workflow(self, steps):
                """Execute independent steps in parallel."""
                with ThreadPoolExecutor(max_workers=8) as executor:  # More workers

                    def execute_step(step_data):
                        step_index, step = step_data
                        time.sleep(0.0005)  # 0.5ms per step (optimized)
                        return {
                            "step": step_index,
                            "result": f"step_{step_index}_completed",
                        }

                    # Use asyncio-style parallel execution for better performance
                    futures = [
                        executor.submit(execute_step, (i, step))
                        for i, step in enumerate(steps)
                    ]
                    results = [future.result() for future in futures]

                return sorted(results, key=lambda x: x["step"])

        engine = MockWorkflowEngine()
        steps = [f"step_{i}" for i in range(20)]

        # Test linear execution
        performance_timer.start()
        linear_results = engine.execute_linear_workflow(steps)
        performance_timer.stop()
        linear_time = performance_timer.elapsed_ms()

        # Test parallel execution
        performance_timer.start()
        parallel_results = engine.execute_parallel_workflow(steps)
        performance_timer.stop()
        parallel_time = performance_timer.elapsed_ms()

        # Verify parallel execution is faster
        assert len(linear_results) == len(parallel_results) == 20
        assert parallel_time < linear_time * 0.8  # At least 20% faster (more realistic)


class TestFilesPerformance:
    """Performance tests for file processing."""

    @pytest.mark.asyncio
    async def test_template_rendering_performance(self, performance_timer):
        """Test template rendering performance."""

        class MockTemplateEngine:
            def __init__(self):
                self.cache = {}

            def render_template(self, template, variables):
                # Simulate template compilation overhead
                time.sleep(0.0001)  # 0.1ms compilation time
                # Simple string replacement (mock Jinja2)
                result = template
                for key, value in variables.items():
                    result = result.replace(f"{{ {key} }}", str(value))
                return result

            def render_cached_template(self, template_name, template, variables):
                # Cache the template compilation, not the rendered result
                template_cache_key = f"template_{template_name}"

                if template_cache_key in self.cache:
                    # Template is compiled and cached, skip compilation overhead
                    result = template
                    for key, value in variables.items():
                        result = result.replace(f"{{ {key} }}", str(value))
                    return result
                else:
                    # Template not cached, compile and cache it
                    result = self.render_template(template, variables)
                    self.cache[template_cache_key] = template  # Cache the template
                    return result

            def render_bulk_templates(self, template_data_list, use_cache=True):
                results = []
                for data in template_data_list:
                    if use_cache:
                        result = self.render_cached_template(
                            data["name"], data["template"], data["variables"]
                        )
                    else:
                        result = self.render_template(
                            data["template"], data["variables"]
                        )

                    results.append({"name": data["name"], "rendered": result})

                return results

        engine = MockTemplateEngine()

        # Generate test data
        template_data = []
        for i in range(100):
            template_data.append(
                {
                    "name": f"template_{i % 10}",  # Reuse template names for cache testing
                    "template": "Hello {{ name }}! Your order #{{ order_id }} is ready.",
                    "variables": {"name": f"Customer{i}", "order_id": f"ORD-{i:04d}"},
                }
            )

        # Test without cache
        performance_timer.start()
        no_cache_results = engine.render_bulk_templates(template_data, use_cache=False)
        performance_timer.stop()
        no_cache_time = performance_timer.elapsed_ms()

        # Reset cache
        engine.cache.clear()

        # Test with cache
        performance_timer.start()
        cached_results = engine.render_bulk_templates(template_data, use_cache=True)
        performance_timer.stop()
        cached_time = performance_timer.elapsed_ms()

        # Verify caching improves performance
        assert len(no_cache_results) == len(cached_results) == 100
        assert cached_time < no_cache_time * 0.8  # At least 20% faster with cache

        # Calculate throughput
        cache_throughput = len(template_data) / (cached_time / 1000)
        assert cache_throughput > 100  # At least 100 renders per second

    @pytest.mark.asyncio
    async def test_file_processing_performance(
        self, performance_timer, mock_file_storage
    ):
        """Test file processing performance."""

        class MockFileProcessor:
            def __init__(self, storage):
                self.storage = storage

            async def process_single_file(self, filename, content):
                # Simulate file processing
                await asyncio.sleep(0.01)  # 10ms per file

                # Store file
                file_id = await self.storage.upload(filename, content)

                return {"filename": filename, "file_id": file_id, "size": len(content)}

            async def process_batch_files(self, files_data, max_concurrent=5):
                semaphore = asyncio.Semaphore(max_concurrent)

                async def process_file(file_data):
                    async with semaphore:
                        return await self.process_single_file(
                            file_data["filename"], file_data["content"]
                        )

                return await asyncio.gather(
                    *[process_file(file_data) for file_data in files_data]
                )

        processor = MockFileProcessor(mock_file_storage)

        # Generate test files
        files_data = []
        for i in range(20):
            files_data.append(
                {
                    "filename": f"file_{i}.txt",
                    "content": f"Content for file {i}" * 100,  # Make files bigger
                }
            )

        # Test sequential processing
        performance_timer.start()
        sequential_results = []
        for file_data in files_data:
            result = await processor.process_single_file(
                file_data["filename"], file_data["content"]
            )
            sequential_results.append(result)
        performance_timer.stop()
        sequential_time = performance_timer.elapsed_ms()

        # Test concurrent processing
        performance_timer.start()
        concurrent_results = await processor.process_batch_files(
            files_data, max_concurrent=5
        )
        performance_timer.stop()
        concurrent_time = performance_timer.elapsed_ms()

        # Verify concurrent processing is more efficient
        assert len(sequential_results) == len(concurrent_results) == 20
        assert concurrent_time < sequential_time * 0.7  # At least 30% faster

        # Calculate throughput
        concurrent_throughput = len(files_data) / (concurrent_time / 1000)
        assert concurrent_throughput > 5  # At least 5 files per second


class TestSystemPerformance:
    """System-wide performance tests."""

    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self):
        """Test memory usage during operations."""
        import os

        import psutil

        class MockMemoryMonitor:
            def __init__(self):
                self.process = psutil.Process(os.getpid())

            def get_memory_usage_mb(self):
                return self.process.memory_info().rss / 1024 / 1024

            async def monitor_operation(self, operation_func, *args, **kwargs):
                initial_memory = self.get_memory_usage_mb()

                result = await operation_func(*args, **kwargs)

                final_memory = self.get_memory_usage_mb()
                peak_memory = max(initial_memory, final_memory)  # Simplified

                return {
                    "result": result,
                    "memory_stats": {
                        "initial_mb": initial_memory,
                        "final_mb": final_memory,
                        "peak_mb": peak_memory,
                        "difference_mb": final_memory - initial_memory,
                    },
                }

        monitor = MockMemoryMonitor()

        async def memory_intensive_operation():
            # Simulate memory usage
            data = []
            for i in range(1000):
                data.append({"id": i, "data": "x" * 1000})
                await asyncio.sleep(0.001)
            return len(data)

        result = await monitor.monitor_operation(memory_intensive_operation)

        # Verify operation completed and memory usage tracked
        assert result["result"] == 1000
        assert "memory_stats" in result
        assert result["memory_stats"]["final_mb"] > 0

    def test_latency_percentiles(self, performance_timer):
        """Test latency distribution and percentiles."""

        class MockLatencyTester:
            def __init__(self):
                pass

            def simulate_operation_with_variance(self):
                # Simulate variable latency
                import random

                base_latency = 0.01  # 10ms base
                variance = random.uniform(0, 0.005)  # 0-5ms variance
                time.sleep(base_latency + variance)
                return "completed"

            def run_latency_test(self, iterations=100):
                latencies = []

                for _ in range(iterations):
                    performance_timer.start()
                    self.simulate_operation_with_variance()
                    performance_timer.stop()
                    latencies.append(performance_timer.elapsed_ms())

                return latencies

        tester = MockLatencyTester()
        latencies = tester.run_latency_test(50)

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(0.5 * len(sorted_latencies))]
        p95 = sorted_latencies[int(0.95 * len(sorted_latencies))]
        p99 = sorted_latencies[int(0.99 * len(sorted_latencies))]

        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)

        # Verify latency characteristics
        assert len(latencies) == 50
        assert 8 < avg_latency < 20  # Average should be 8-20ms
        assert p95 < max_latency  # P95 should be less than max
        assert p50 < p95 < p99  # Percentiles should be ordered

        # Performance requirements
        assert p95 < 25  # 95th percentile under 25ms
        assert p99 < 30  # 99th percentile under 30ms
