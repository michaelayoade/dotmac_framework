"""
Basic usage example for dotmac.tasks.

This example demonstrates:
- Creating an idempotency key
- Checking for existing operations
- Completing operations with results
"""

import asyncio
from dotmac.tasks import BackgroundOperationsManager, MemoryStorage


async def basic_idempotency_example():
    """Example of basic idempotency usage."""
    print("=== Basic Idempotency Example ===")
    
    # Create manager with in-memory storage
    storage = MemoryStorage()
    manager = BackgroundOperationsManager(storage=storage)
    await manager.start()
    
    try:
        # Create an idempotency key for a send email operation
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user123",
            operation_type="send_email",
            parameters={"to": "user@example.com", "subject": "Welcome!"}
        )
        
        print(f"Created idempotency key: {key_obj.key}")
        print(f"Status: {key_obj.status}")
        
        # Check if operation already exists (should find the one we just created)
        existing = await manager.check_idempotency(key_obj.key)
        if existing:
            print(f"Found existing operation: {existing.key}")
            print(f"Status: {existing.status}")
        
        # Simulate performing the operation
        print("Performing email send operation...")
        await asyncio.sleep(0.1)  # Simulate work
        
        # Complete the operation with results
        result = {
            "message_id": "email_123456",
            "status": "sent",
            "timestamp": "2024-09-03T12:00:00Z"
        }
        
        success = await manager.complete_idempotent_operation(
            key_obj.key, result
        )
        print(f"Operation completed: {success}")
        
        # Check the updated status
        completed = await manager.check_idempotency(key_obj.key)
        print(f"Final status: {completed.status}")
        print(f"Result: {completed.result}")
        
        # Demonstrate duplicate detection
        print("\n--- Testing Duplicate Detection ---")
        duplicate_key = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user123", 
            operation_type="send_email",
            parameters={"to": "user@example.com", "subject": "Welcome!"}  # Same params
        )
        
        # Should be the same key due to deterministic generation
        print(f"Original key:  {key_obj.key}")
        print(f"Duplicate key: {duplicate_key.key}")
        print(f"Keys match: {key_obj.key == duplicate_key.key}")
        
    finally:
        await manager.stop()


async def custom_key_example():
    """Example using custom idempotency keys."""
    print("\n=== Custom Idempotency Key Example ===")
    
    storage = MemoryStorage()
    manager = BackgroundOperationsManager(storage=storage)
    await manager.start()
    
    try:
        # Use a custom key instead of generated one
        custom_key = "user-registration-user123-2024-09-03"
        
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user123",
            operation_type="user_registration",
            key=custom_key
        )
        
        print(f"Created custom key: {key_obj.key}")
        
        # Complete the operation
        result = {"user_id": "user123", "registration_time": "2024-09-03T12:00:00Z"}
        await manager.complete_idempotent_operation(custom_key, result)
        
        # Verify completion
        completed = await manager.check_idempotency(custom_key)
        print(f"Custom key result: {completed.result}")
        
    finally:
        await manager.stop()


async def error_handling_example():
    """Example of error handling in operations."""
    print("\n=== Error Handling Example ===")
    
    storage = MemoryStorage()
    manager = BackgroundOperationsManager(storage=storage)
    await manager.start()
    
    try:
        # Create key for operation that will fail
        key_obj = await manager.create_idempotency_key(
            tenant_id="tenant1",
            user_id="user456",
            operation_type="send_sms", 
            parameters={"to": "+1234567890", "message": "Hello!"}
        )
        
        print(f"Created key for SMS operation: {key_obj.key}")
        
        # Simulate operation failure
        error_message = "SMS gateway timeout"
        success = await manager.complete_idempotent_operation(
            key_obj.key, {}, error=error_message
        )
        print(f"Operation failed as expected: {success}")
        
        # Check the error status
        failed = await manager.check_idempotency(key_obj.key)
        print(f"Final status: {failed.status}")
        print(f"Error message: {failed.error}")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(basic_idempotency_example())
    asyncio.run(custom_key_example())
    asyncio.run(error_handling_example())