#!/usr/bin/env python3
"""
Basic usage example for dotmac-events package.

This example demonstrates:
- Creating different event bus adapters
- Publishing and consuming events
- Using structured Event objects
- Consumer groups and retry logic
- Dead Letter Queue handling
- Observability integration
"""

import asyncio
import logging
from dotmac.events import (
    # Core components
    Event,
    create_memory_bus,
    
    # Consumer and retry
    ConsumerOptions,
    run_consumer,
    create_exponential_retry_options,
    
    # DLQ
    create_dlq_consumer,
    log_dlq_entry,
    
    # Observability
    create_default_hooks,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    print("🚌 DotMac Events - Basic Usage Example")
    print("=" * 50)
    
    # 1. Create an event bus (memory adapter for this example)
    print("\n1. Creating memory event bus...")
    bus = create_memory_bus()
    print("   ✅ Event bus created")
    
    # 2. Set up observability hooks
    print("\n2. Setting up observability...")
    hooks = create_default_hooks()
    print("   ✅ Observability hooks configured")
    
    # 3. Define event handlers
    print("\n3. Defining event handlers...")
    
    processed_orders = []
    
    async def handle_order_created(event: Event) -> None:
        """Handle order created events."""
        order_data = event.payload
        logger.info(f"Processing order: {order_data['order_id']}")
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        # Sometimes fail to demonstrate retry logic
        if order_data.get("should_fail"):
            raise ValueError("Simulated processing error")
        
        processed_orders.append(order_data)
        print(f"   ✅ Processed order {order_data['order_id']}")
    
    async def handle_user_registered(event: Event) -> None:
        """Handle user registration events."""
        user_data = event.payload
        logger.info(f"Welcome new user: {user_data['username']}")
        print(f"   👋 Welcome user: {user_data['username']}")
    
    # 4. Set up DLQ handler
    async def handle_failed_events(dlq_entry) -> None:
        """Handle events that failed processing."""
        print(f"   🚨 DLQ Event - Topic: {dlq_entry.original_topic}, Error: {dlq_entry.error}")
        await log_dlq_entry(dlq_entry)
    
    print("   ✅ Event handlers defined")
    
    # 5. Subscribe to events with retry options
    print("\n4. Setting up event subscriptions...")
    
    # Order processing with retry
    order_options = create_exponential_retry_options(
        max_retries=3,
        base_delay_ms=100,
    )
    
    await run_consumer(
        bus, 
        "order.created", 
        handle_order_created, 
        order_options,
        group="order-processor"
    )
    
    # User registration (simple)
    user_options = ConsumerOptions(max_retries=1)
    await run_consumer(
        bus,
        "user.registered",
        handle_user_registered,
        user_options,
        group="user-processor"
    )
    
    # DLQ processing
    await create_dlq_consumer(
        bus,
        "order.created.DLQ",
        handle_failed_events,
        group="dlq-processor"
    )
    
    print("   ✅ Event subscriptions configured")
    
    # 6. Publish some events
    print("\n5. Publishing events...")
    
    # Successful orders
    successful_orders = [
        {"order_id": "ORD-001", "customer_id": "CUST-123", "amount": 99.99},
        {"order_id": "ORD-002", "customer_id": "CUST-456", "amount": 149.50},
        {"order_id": "ORD-003", "customer_id": "CUST-789", "amount": 75.00},
    ]
    
    for order in successful_orders:
        event = Event(
            topic="order.created",
            payload=order,
            key=order["customer_id"],
            tenant_id="acme-corp",
            headers={"source": "order-service", "version": "1.0"},
        )
        await bus.publish(event)
        print(f"   📤 Published order event: {order['order_id']}")
    
    # Failing order (to demonstrate DLQ)
    failing_order = {
        "order_id": "ORD-FAIL",
        "customer_id": "CUST-999",
        "amount": 199.99,
        "should_fail": True,
    }
    
    fail_event = Event(
        topic="order.created",
        payload=failing_order,
        key=failing_order["customer_id"],
        tenant_id="acme-corp",
    )
    await bus.publish(fail_event)
    print(f"   📤 Published failing order event: {failing_order['order_id']}")
    
    # User registrations
    users = [
        {"username": "john_doe", "email": "john@example.com", "plan": "premium"},
        {"username": "jane_smith", "email": "jane@example.com", "plan": "basic"},
    ]
    
    for user in users:
        event = Event(
            topic="user.registered",
            payload=user,
            key=user["username"],
            tenant_id="acme-corp",
        )
        await bus.publish(event)
        print(f"   📤 Published user event: {user['username']}")
    
    # 7. Wait for processing
    print("\n6. Processing events...")
    await asyncio.sleep(2.0)  # Wait for all events to be processed
    
    # 8. Show results
    print("\n7. Results:")
    print(f"   📊 Successfully processed orders: {len(processed_orders)}")
    for order in processed_orders:
        print(f"      - Order {order['order_id']}: ${order['amount']}")
    
    # Check DLQ
    dlq_size = bus.get_queue_size("order.created.DLQ")
    print(f"   🚨 Events in DLQ: {dlq_size}")
    
    # Show bus statistics
    stats = bus.get_stats()
    print(f"   📈 Bus Stats:")
    print(f"      - Published: {stats['published_count']}")
    print(f"      - Consumed: {stats['consumed_count']}")
    print(f"      - Active topics: {stats['active_topics']}")
    print(f"      - Active subscriptions: {stats['active_subscriptions']}")
    
    # 9. Cleanup
    print("\n8. Cleaning up...")
    await bus.close()
    print("   ✅ Event bus closed")
    
    print("\n🎉 Example completed successfully!")
    print("\nNext steps:")
    print("- Try Redis adapter: create_redis_bus(RedisConfig(host='localhost'))")
    print("- Try Kafka adapter: create_kafka_bus(KafkaConfig(bootstrap_servers='localhost:9092'))")
    print("- Add observability: create_dotmac_observability_hooks()")
    print("- Explore advanced retry and DLQ options")


if __name__ == "__main__":
    asyncio.run(main())