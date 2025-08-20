"""
Partition key enforcement and message ordering for events.
"""

import asyncio
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional

import structlog

from ..models.envelope import EventEnvelope

logger = structlog.get_logger(__name__)


class PartitionStrategy(str, Enum):
    """Partition key strategies."""

    HASH = "hash"
    ROUND_ROBIN = "round_robin"
    CUSTOM = "custom"


@dataclass
class PartitionInfo:
    """Partition information for a message."""

    partition_key: str
    partition_id: int
    total_partitions: int
    strategy: PartitionStrategy


class PartitionKeyExtractor:
    """Extract partition keys from event envelopes."""

    def __init__(self):
        # Priority order for partition key extraction
        self.partition_key_fields = [
            "partition_key",  # Explicit partition key
            "service_id",     # Service-based partitioning
            "device_id",      # Device-based partitioning
            "customer_id",    # Customer-based partitioning
            "site_id",        # Site-based partitioning
            "workflow_id",    # Workflow-based partitioning
            "user_id"         # User-based partitioning
        ]

        # Event types that don't require partition keys (system events)
        self.partition_exempt_patterns = [
            "system.",
            "admin.",
            "health.",
            "monitoring.",
            "audit."
        ]

    def extract_partition_key(self, envelope: EventEnvelope) -> Optional[str]:
        """
        Extract partition key from event envelope.

        Returns:
            Partition key string or None if not found/required
        """
        # Check if event type is exempt from partitioning
        if self._is_partition_exempt(envelope.type):
            return None

        # Try to extract from data fields in priority order
        for field in self.partition_key_fields:
            if field in envelope.data:
                value = envelope.data[field]
                if value:
                    return str(value)

        # Fallback to tenant_id for global ordering
        return envelope.tenant_id

    def _is_partition_exempt(self, event_type: str) -> bool:
        """Check if event type is exempt from partition key requirement."""
        return any(pattern in event_type for pattern in self.partition_exempt_patterns)

    def validate_partition_key(self, envelope: EventEnvelope) -> bool:
        """
        Validate that envelope has required partition key.

        Returns:
            True if valid, False if missing required partition key
        """
        if self._is_partition_exempt(envelope.type):
            return True

        partition_key = self.extract_partition_key(envelope)
        return partition_key is not None


class PartitionCalculator:
    """Calculate partition assignments for messages."""

    def __init__(self, total_partitions: int = 16):
        self.total_partitions = total_partitions

    def calculate_partition(
        self,
        partition_key: str,
        strategy: PartitionStrategy = PartitionStrategy.HASH
    ) -> PartitionInfo:
        """
        Calculate partition for a given key.

        Args:
            partition_key: Key to partition on
            strategy: Partitioning strategy

        Returns:
            PartitionInfo with assignment details
        """
        if strategy == PartitionStrategy.HASH:
            partition_id = self._hash_partition(partition_key)
        elif strategy == PartitionStrategy.ROUND_ROBIN:
            partition_id = self._round_robin_partition(partition_key)
        else:
            raise ValueError(f"Unsupported partition strategy: {strategy}")

        return PartitionInfo(
            partition_key=partition_key,
            partition_id=partition_id,
            total_partitions=self.total_partitions,
            strategy=strategy
        )

    def _hash_partition(self, partition_key: str) -> int:
        """Hash-based partitioning for consistent assignment."""
        hash_value = hashlib.md5(partition_key.encode()).hexdigest()
        return int(hash_value, 16) % self.total_partitions

    def _round_robin_partition(self, partition_key: str) -> int:
        """Round-robin partitioning (less consistent but balanced)."""
        # Simple hash for round-robin
        return hash(partition_key) % self.total_partitions


class OrderingEnforcer:
    """Enforce message ordering within partitions."""

    def __init__(self):
        self.partition_sequences: Dict[int, int] = {}
        self.partition_locks: Dict[int, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get_partition_lock(self, partition_id: int) -> asyncio.Lock:
        """Get or create lock for partition."""
        async with self._global_lock:
            if partition_id not in self.partition_locks:
                self.partition_locks[partition_id] = asyncio.Lock()
            return self.partition_locks[partition_id]

    async def assign_sequence(self, partition_id: int) -> int:
        """Assign sequence number for partition."""
        lock = await self.get_partition_lock(partition_id)

        async with lock:
            current_seq = self.partition_sequences.get(partition_id, 0)
            next_seq = current_seq + 1
            self.partition_sequences[partition_id] = next_seq
            return next_seq

    async def validate_sequence(self, partition_id: int, sequence: int) -> bool:
        """Validate sequence number for ordering."""
        lock = await self.get_partition_lock(partition_id)

        async with lock:
            expected_seq = self.partition_sequences.get(partition_id, 0) + 1
            return sequence == expected_seq

    def get_partition_stats(self) -> Dict[str, Any]:
        """Get partition statistics."""
        return {
            "total_partitions": len(self.partition_sequences),
            "sequences": dict(self.partition_sequences),
            "active_locks": len(self.partition_locks)
        }


class OrderedEventProcessor:
    """Process events with ordering guarantees."""

    def __init__(
        self,
        partition_calculator: PartitionCalculator,
        ordering_enforcer: OrderingEnforcer,
        partition_key_extractor: PartitionKeyExtractor
    ):
        self.partition_calculator = partition_calculator
        self.ordering_enforcer = ordering_enforcer
        self.partition_key_extractor = partition_key_extractor
        self.processing_queues: Dict[int, asyncio.Queue] = {}
        self.processing_tasks: Dict[int, asyncio.Task] = {}
        self.running = False

    async def start(self):
        """Start ordered processing."""
        if self.running:
            return

        self.running = True

        # Create processing queues and tasks for each partition
        for partition_id in range(self.partition_calculator.total_partitions):
            queue = asyncio.Queue()
            self.processing_queues[partition_id] = queue

            task = asyncio.create_task(
                self._partition_processor(partition_id, queue)
            )
            self.processing_tasks[partition_id] = task

        logger.info(
            "Ordered event processor started",
            partitions=self.partition_calculator.total_partitions
        )

    async def stop(self):
        """Stop ordered processing."""
        self.running = False

        # Cancel all processing tasks
        for task in self.processing_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)

        self.processing_tasks.clear()
        self.processing_queues.clear()

        logger.info("Ordered event processor stopped")

    async def submit_event(
        self,
        envelope: EventEnvelope,
        handler: Callable[[EventEnvelope], Any]
    ) -> PartitionInfo:
        """
        Submit event for ordered processing.

        Args:
            envelope: Event envelope
            handler: Processing function

        Returns:
            PartitionInfo for the assigned partition
        """
        if not self.running:
            raise RuntimeError("Ordered processor not started")

        # Validate partition key
        if not self.partition_key_extractor.validate_partition_key(envelope):
            raise ValueError(f"Event {envelope.type} missing required partition key")

        # Extract partition key
        partition_key = self.partition_key_extractor.extract_partition_key(envelope)

        if partition_key is None:
            # For exempt events, use round-robin
            partition_key = envelope.id

        # Calculate partition
        partition_info = self.partition_calculator.calculate_partition(partition_key)

        # Get sequence number
        sequence = await self.ordering_enforcer.assign_sequence(partition_info.partition_id)

        # Submit to partition queue
        queue = self.processing_queues[partition_info.partition_id]
        await queue.put({
            "envelope": envelope,
            "handler": handler,
            "sequence": sequence,
            "partition_info": partition_info
        })

        logger.debug(
            "Event submitted for ordered processing",
            envelope_id=envelope.id,
            partition_id=partition_info.partition_id,
            partition_key=partition_key,
            sequence=sequence
        )

        return partition_info

    async def _partition_processor(self, partition_id: int, queue: asyncio.Queue):
        """Process events for a specific partition."""
        logger.info("Partition processor started", partition_id=partition_id)

        try:
            while self.running:
                try:
                    # Get next event with timeout
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)

                    envelope = item["envelope"]
                    handler = item["handler"]
                    sequence = item["sequence"]
                    partition_info = item["partition_info"]

                    try:
                        # Process event
                        await handler(envelope)

                        logger.debug(
                            "Event processed in order",
                            envelope_id=envelope.id,
                            partition_id=partition_id,
                            sequence=sequence
                        )

                    except Exception as e:
                        logger.error(
                            "Error processing ordered event",
                            envelope_id=envelope.id,
                            partition_id=partition_id,
                            sequence=sequence,
                            error=str(e)
                        )
                        # Continue processing other events

                    finally:
                        queue.task_done()

                except asyncio.TimeoutError:
                    # Continue loop on timeout
                    continue

        except asyncio.CancelledError:
            logger.info("Partition processor cancelled", partition_id=partition_id)
        except Exception as e:
            logger.error(
                "Partition processor error",
                partition_id=partition_id,
                error=str(e)
            )
        finally:
            logger.info("Partition processor stopped", partition_id=partition_id)

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        queue_sizes = {
            pid: queue.qsize()
            for pid, queue in self.processing_queues.items()
        }

        return {
            "running": self.running,
            "total_partitions": len(self.processing_queues),
            "queue_sizes": queue_sizes,
            "total_queued": sum(queue_sizes.values()),
            "ordering_stats": self.ordering_enforcer.get_partition_stats()
        }


class OrderingMiddleware:
    """Middleware for automatic event ordering."""

    def __init__(self, ordered_processor: OrderedEventProcessor):
        self.ordered_processor = ordered_processor

    async def __call__(self, envelope: EventEnvelope, handler: Callable, next_middleware):
        """Process event with ordering."""
        # Check if event requires ordering
        partition_key = self.ordered_processor.partition_key_extractor.extract_partition_key(envelope)

        if partition_key is None:
            # No ordering required, process directly
            return await next_middleware(envelope, handler)

        # Submit for ordered processing
        partition_info = await self.ordered_processor.submit_event(envelope, handler)

        return {
            "status": "submitted_for_ordering",
            "partition_info": partition_info
        }


# Factory functions for common configurations
def create_service_ordered_processor(
    total_partitions: int = 16,
    strategy: PartitionStrategy = PartitionStrategy.HASH
) -> OrderedEventProcessor:
    """Create ordered processor for service-based partitioning."""

    partition_calculator = PartitionCalculator(total_partitions)
    ordering_enforcer = OrderingEnforcer()
    partition_key_extractor = PartitionKeyExtractor()

    return OrderedEventProcessor(
        partition_calculator=partition_calculator,
        ordering_enforcer=ordering_enforcer,
        partition_key_extractor=partition_key_extractor
    )


def create_customer_ordered_processor(
    total_partitions: int = 32,
    strategy: PartitionStrategy = PartitionStrategy.HASH
) -> OrderedEventProcessor:
    """Create ordered processor for customer-based partitioning."""

    partition_calculator = PartitionCalculator(total_partitions)
    ordering_enforcer = OrderingEnforcer()

    # Customize extractor for customer-first partitioning
    partition_key_extractor = PartitionKeyExtractor()
    partition_key_extractor.partition_key_fields = [
        "partition_key",
        "customer_id",    # Customer first
        "service_id",
        "device_id",
        "site_id",
        "workflow_id",
        "user_id"
    ]

    return OrderedEventProcessor(
        partition_calculator=partition_calculator,
        ordering_enforcer=ordering_enforcer,
        partition_key_extractor=partition_key_extractor
    )
