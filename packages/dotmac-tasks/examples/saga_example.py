"""
Saga workflow example for dotmac.tasks.

This example demonstrates:
- Creating saga workflows
- Registering operation and compensation handlers
- Executing workflows with compensation on failure
- Retry logic for failed steps
"""

import asyncio
import random
from dotmac.tasks import BackgroundOperationsManager, MemoryStorage


class UserOnboardingHandlers:
    """Example handlers for user onboarding saga."""
    
    def __init__(self):
        self.users = {}
        self.emails = {}
        self.services = {}
    
    async def create_user_handler(self, params):
        """Create user account."""
        username = params["username"]
        email = params["email"]
        
        print(f"Creating user: {username}")
        
        # Simulate potential failure
        if random.random() < 0.1:  # 10% failure rate
            raise Exception("Database connection failed")
        
        user_id = f"user_{username}"
        self.users[user_id] = {"username": username, "email": email}
        
        print(f"User created: {user_id}")
        return {"user_id": user_id, "status": "created"}
    
    async def send_welcome_email_handler(self, params):
        """Send welcome email."""
        email = params["to"]
        template = params["template"]
        
        print(f"Sending email to: {email}")
        
        # Simulate potential failure
        if random.random() < 0.1:  # 10% failure rate  
            raise Exception("SMTP server unavailable")
        
        message_id = f"email_{len(self.emails) + 1}"
        self.emails[message_id] = {"to": email, "template": template, "status": "sent"}
        
        print(f"Email sent: {message_id}")
        return {"message_id": message_id, "status": "sent"}
    
    async def provision_service_handler(self, params):
        """Provision service for user."""
        user_id = params["user_id"]
        service_type = params["service_type"]
        
        print(f"Provisioning {service_type} for {user_id}")
        
        # Simulate potential failure
        if random.random() < 0.2:  # 20% failure rate
            raise Exception("Service provisioning system overloaded")
        
        service_id = f"service_{len(self.services) + 1}"
        self.services[service_id] = {
            "user_id": user_id,
            "service_type": service_type,
            "status": "active"
        }
        
        print(f"Service provisioned: {service_id}")
        return {"service_id": service_id, "status": "provisioned"}
    
    # Compensation handlers
    async def delete_user_compensation(self, params):
        """Compensate user creation by deleting user."""
        user_id = params["user_id"]
        print(f"Compensating: Deleting user {user_id}")
        self.users.pop(user_id, None)
    
    async def cancel_email_compensation(self, params):
        """Compensate email by sending cancellation."""
        email = params["to"]
        print(f"Compensating: Sending cancellation email to {email}")
        # In real scenario, might send cancellation email
    
    async def deprovision_service_compensation(self, params):
        """Compensate service provisioning."""
        service_id = params.get("service_id")
        if service_id:
            print(f"Compensating: Deprovisioning service {service_id}")
            self.services.pop(service_id, None)


async def successful_saga_example():
    """Example of successful saga execution."""
    print("=== Successful Saga Example ===")
    
    storage = MemoryStorage()
    manager = BackgroundOperationsManager(storage=storage)
    await manager.start()
    
    handlers = UserOnboardingHandlers()
    
    # Register operation handlers
    manager.register_operation_handler("create_user", handlers.create_user_handler)
    manager.register_operation_handler("send_email", handlers.send_welcome_email_handler)
    manager.register_operation_handler("provision_service", handlers.provision_service_handler)
    
    # Register compensation handlers
    manager.register_compensation_handler("create_user", handlers.delete_user_compensation)
    manager.register_compensation_handler("send_email", handlers.cancel_email_compensation)
    manager.register_compensation_handler("provision_service", handlers.deprovision_service_compensation)
    
    try:
        # Define saga steps
        steps = [
            {
                "name": "Create User Account",
                "operation": "create_user",
                "parameters": {"username": "johndoe", "email": "john@example.com"},
                "compensation_parameters": {"user_id": "user_johndoe"},
                "max_retries": 2
            },
            {
                "name": "Send Welcome Email",
                "operation": "send_email", 
                "parameters": {"to": "john@example.com", "template": "welcome"},
                "compensation_parameters": {"to": "john@example.com"},
                "max_retries": 2
            },
            {
                "name": "Provision Basic Service",
                "operation": "provision_service",
                "parameters": {"user_id": "user_johndoe", "service_type": "basic"},
                "compensation_parameters": {"service_id": None},  # Will be updated after execution
                "max_retries": 1
            }
        ]
        
        # Create saga
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="user_onboarding",
            steps=steps
        )
        
        print(f"Created saga: {saga.saga_id}")
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        print(f"Saga execution result: {success}")
        
        # Get final saga state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        if final_saga_data:
            print(f"Final saga status: {final_saga_data['status']}")
            print(f"Completed steps: {final_saga_data['current_step']}")
            
            for i, step in enumerate(final_saga_data['steps']):
                print(f"Step {i+1}: {step['name']} - {step['status']}")
                if step.get('result'):
                    print(f"  Result: {step['result']}")
        
        print(f"Users created: {list(handlers.users.keys())}")
        print(f"Emails sent: {list(handlers.emails.keys())}")
        print(f"Services provisioned: {list(handlers.services.keys())}")
        
    finally:
        await manager.stop()


async def failing_saga_example():
    """Example of saga with failure and compensation."""
    print("\n=== Failing Saga with Compensation Example ===")
    
    storage = MemoryStorage()
    manager = BackgroundOperationsManager(storage=storage)
    await manager.start()
    
    handlers = UserOnboardingHandlers()
    
    # Add a handler that always fails
    async def failing_handler(params):
        print("Executing operation that always fails...")
        raise Exception("Simulated critical failure")
    
    # Register handlers
    manager.register_operation_handler("create_user", handlers.create_user_handler)
    manager.register_operation_handler("send_email", handlers.send_welcome_email_handler)
    manager.register_operation_handler("failing_operation", failing_handler)
    
    # Register compensations
    manager.register_compensation_handler("create_user", handlers.delete_user_compensation)
    manager.register_compensation_handler("send_email", handlers.cancel_email_compensation)
    
    try:
        # Define saga with failing step
        steps = [
            {
                "name": "Create User Account",
                "operation": "create_user",
                "parameters": {"username": "janedoe", "email": "jane@example.com"},
                "compensation_parameters": {"user_id": "user_janedoe"},
                "max_retries": 1
            },
            {
                "name": "Send Welcome Email",
                "operation": "send_email",
                "parameters": {"to": "jane@example.com", "template": "welcome"}, 
                "compensation_parameters": {"to": "jane@example.com"},
                "max_retries": 1
            },
            {
                "name": "Failing Operation",
                "operation": "failing_operation",
                "parameters": {"data": "test"},
                "max_retries": 1  # Will fail and trigger compensation
            }
        ]
        
        # Create saga
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="failing_workflow",
            steps=steps
        )
        
        print(f"Created saga: {saga.saga_id}")
        
        # Execute saga (will fail and compensate)
        success = await manager.execute_saga_workflow(saga.saga_id)
        print(f"Saga execution result: {success}")
        
        # Get final saga state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        if final_saga_data:
            print(f"Final saga status: {final_saga_data['status']}")
            
            for i, step in enumerate(final_saga_data['steps']):
                print(f"Step {i+1}: {step['name']} - {step['status']}")
                if step.get('error'):
                    print(f"  Error: {step['error']}")
        
        print(f"Users after compensation: {list(handlers.users.keys())}")
        print(f"Emails after compensation: {list(handlers.emails.keys())}")
        
    finally:
        await manager.stop()


async def retry_example():
    """Example of step retry logic."""
    print("\n=== Retry Logic Example ===")
    
    storage = MemoryStorage() 
    manager = BackgroundOperationsManager(storage=storage)
    await manager.start()
    
    # Handler that fails first few times then succeeds
    call_count = 0
    
    async def flaky_handler(params):
        nonlocal call_count
        call_count += 1
        
        print(f"Flaky handler called (attempt {call_count})")
        
        if call_count < 3:  # Fail first 2 attempts
            raise Exception(f"Attempt {call_count} failed")
        
        print("Flaky handler succeeded!")
        return {"result": f"success_on_attempt_{call_count}"}
    
    manager.register_operation_handler("flaky_operation", flaky_handler)
    
    try:
        steps = [
            {
                "name": "Flaky Operation",
                "operation": "flaky_operation",
                "parameters": {"data": "test"},
                "max_retries": 3  # Allow 3 retries (4 total attempts)
            }
        ]
        
        saga = await manager.create_saga_workflow(
            tenant_id="tenant1",
            workflow_type="retry_test",
            steps=steps
        )
        
        print(f"Created saga: {saga.saga_id}")
        
        # Execute saga
        success = await manager.execute_saga_workflow(saga.saga_id)
        print(f"Saga execution result: {success}")
        
        # Get final state
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        if final_saga_data:
            step = final_saga_data['steps'][0]
            print(f"Step status: {step['status']}")
            print(f"Retry count: {step['retry_count']}")
            print(f"Result: {step.get('result')}")
            print(f"Total handler calls: {call_count}")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Run examples
    asyncio.run(successful_saga_example())
    asyncio.run(failing_saga_example()) 
    asyncio.run(retry_example())