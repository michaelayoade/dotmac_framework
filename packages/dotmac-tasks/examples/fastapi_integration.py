"""
FastAPI integration example for dotmac.tasks.

This example demonstrates:
- Adding background operations middleware to FastAPI
- Using idempotency headers in API endpoints
- Automatic caching of completed operations
- Handling in-progress operations
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncio

from dotmac.tasks import (
    add_background_operations_middleware,
    get_idempotency_key,
    set_operation_result,
    is_idempotent_request
)


# Pydantic models for API requests
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    template: Optional[str] = None


class UserRegistrationRequest(BaseModel):
    username: str
    email: str
    full_name: str
    send_welcome_email: bool = True


# Create FastAPI app
app = FastAPI(title="Background Operations API Example")

# Add background operations middleware
manager = add_background_operations_middleware(app)

# Simulated databases
users_db = {}
emails_db = {}


@app.on_event("startup")
async def startup_event():
    """Start background operations manager."""
    await manager.start()
    
    # Register operation handlers for saga workflows
    manager.register_operation_handler("create_user", create_user_operation)
    manager.register_operation_handler("send_email", send_email_operation)
    manager.register_compensation_handler("create_user", delete_user_compensation)


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background operations manager."""
    await manager.stop()


async def create_user_operation(params):
    """Operation handler for user creation."""
    username = params["username"]
    email = params["email"]
    full_name = params["full_name"]
    
    # Simulate user creation
    await asyncio.sleep(0.1)
    
    user_id = f"user_{len(users_db) + 1}"
    users_db[user_id] = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "created_at": "2024-09-03T12:00:00Z"
    }
    
    return {"user_id": user_id, "username": username}


async def send_email_operation(params):
    """Operation handler for email sending."""
    to = params["to"]
    subject = params["subject"]
    body = params["body"]
    
    # Simulate email sending
    await asyncio.sleep(0.2)
    
    email_id = f"email_{len(emails_db) + 1}"
    emails_db[email_id] = {
        "to": to,
        "subject": subject,
        "body": body,
        "sent_at": "2024-09-03T12:00:00Z",
        "status": "sent"
    }
    
    return {"email_id": email_id, "status": "sent"}


async def delete_user_compensation(params):
    """Compensation handler for user deletion."""
    user_id = params.get("user_id")
    if user_id and user_id in users_db:
        del users_db[user_id]


@app.post("/api/send-email")
async def send_email_endpoint(email_request: EmailRequest, request: Request):
    """
    Send email endpoint with automatic idempotency.
    
    Include 'Idempotency-Key' header to ensure operation runs only once.
    """
    # Check if this is an idempotent request
    if is_idempotent_request(request):
        idempotency_key = get_idempotency_key(request)
        print(f"Processing idempotent email request: {idempotency_key}")
    
    # Simulate email sending
    await asyncio.sleep(0.2)
    
    email_id = f"email_{len(emails_db) + 1}"
    emails_db[email_id] = {
        "to": email_request.to,
        "subject": email_request.subject,
        "body": email_request.body,
        "sent_at": "2024-09-03T12:00:00Z",
        "status": "sent"
    }
    
    result = {
        "email_id": email_id,
        "status": "sent",
        "to": email_request.to,
        "subject": email_request.subject
    }
    
    # Cache result for future requests with same idempotency key
    if is_idempotent_request(request):
        set_operation_result(request, result)
    
    return result


@app.post("/api/register-user")
async def register_user_endpoint(user_request: UserRegistrationRequest, request: Request):
    """
    User registration endpoint with saga workflow.
    
    This endpoint creates a user and optionally sends a welcome email.
    Uses saga pattern for rollback if email sending fails.
    """
    if not is_idempotent_request(request):
        raise HTTPException(
            status_code=400,
            detail="User registration requires Idempotency-Key header"
        )
    
    idempotency_key = get_idempotency_key(request)
    
    # Define saga steps
    steps = [
        {
            "name": "Create User Account",
            "operation": "create_user",
            "parameters": {
                "username": user_request.username,
                "email": user_request.email,
                "full_name": user_request.full_name
            },
            "compensation_parameters": {"user_id": None},  # Will be filled after execution
            "max_retries": 2
        }
    ]
    
    # Add email step if requested
    if user_request.send_welcome_email:
        steps.append({
            "name": "Send Welcome Email",
            "operation": "send_email", 
            "parameters": {
                "to": user_request.email,
                "subject": f"Welcome {user_request.full_name}!",
                "body": f"Welcome to our platform, {user_request.full_name}!"
            },
            "max_retries": 1
        })
    
    # Create and execute saga
    saga = await manager.create_saga_workflow(
        tenant_id="default",  # In real app, extract from JWT or context
        workflow_type="user_registration",
        steps=steps,
        idempotency_key=idempotency_key
    )
    
    # Execute saga workflow
    success = await manager.execute_saga_workflow(saga.saga_id)
    
    if not success:
        # Get saga final state for error details
        final_saga_data = await manager.storage.get_saga(saga.saga_id)
        error_details = "User registration failed"
        
        if final_saga_data and final_saga_data.get('steps'):
            failed_step = None
            for step in final_saga_data['steps']:
                if step.get('status') == 'failed':
                    failed_step = step
                    break
            
            if failed_step:
                error_details = f"Step '{failed_step['name']}' failed: {failed_step.get('error', 'Unknown error')}"
        
        result = {
            "status": "failed",
            "error": error_details,
            "saga_id": saga.saga_id
        }
        
        set_operation_result(request, result)
        raise HTTPException(status_code=500, detail=error_details)
    
    # Get results from successful saga execution
    final_saga_data = await manager.storage.get_saga(saga.saga_id)
    user_result = None
    email_result = None
    
    if final_saga_data and final_saga_data.get('steps'):
        for step in final_saga_data['steps']:
            if step['operation'] == 'create_user' and step.get('result'):
                user_result = step['result']
            elif step['operation'] == 'send_email' and step.get('result'):
                email_result = step['result']
    
    result = {
        "status": "success",
        "user": user_result,
        "email": email_result if user_request.send_welcome_email else None,
        "saga_id": saga.saga_id
    }
    
    # Cache successful result
    set_operation_result(request, result)
    
    return result


@app.get("/api/status/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get status of a background operation by ID."""
    # Check if it's an idempotency key
    key_obj = await manager.check_idempotency(operation_id)
    if key_obj:
        return {
            "type": "idempotency_key",
            "key": key_obj.key,
            "status": key_obj.status,
            "result": key_obj.result,
            "error": key_obj.error,
            "created_at": key_obj.created_at.isoformat(),
            "expires_at": key_obj.expires_at.isoformat()
        }
    
    # Check if it's a saga ID
    saga_data = await manager.storage.get_saga(operation_id)
    if saga_data:
        return {
            "type": "saga_workflow",
            "saga_id": saga_data["saga_id"],
            "status": saga_data["status"],
            "workflow_type": saga_data["workflow_type"],
            "current_step": saga_data["current_step"],
            "total_steps": len(saga_data["steps"]),
            "created_at": saga_data["created_at"],
            "updated_at": saga_data["updated_at"],
            "steps": [
                {
                    "name": step["name"],
                    "status": step["status"],
                    "error": step.get("error")
                }
                for step in saga_data["steps"]
            ]
        }
    
    raise HTTPException(status_code=404, detail="Operation not found")


@app.get("/api/debug/storage-stats")
async def get_storage_stats():
    """Get storage statistics for debugging."""
    if hasattr(manager.storage, 'get_stats'):
        stats = await manager.storage.get_stats()
        return {
            "storage_type": type(manager.storage).__name__,
            "stats": stats,
            "local_db_stats": {
                "users_count": len(users_db),
                "emails_count": len(emails_db)
            }
        }
    
    return {
        "storage_type": type(manager.storage).__name__,
        "local_db_stats": {
            "users_count": len(users_db),
            "emails_count": len(emails_db)
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint (exempt from background operations)."""
    storage_health = await manager.storage.health_check()
    return {
        "status": "healthy",
        "storage": storage_health,
        "database": {
            "users": len(users_db),
            "emails": len(emails_db)
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI server with background operations...")
    print("\nExample requests:")
    print("1. Send email with idempotency:")
    print("   curl -X POST 'http://localhost:8000/api/send-email' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -H 'Idempotency-Key: email-test-123' \\")
    print("     -d '{\"to\":\"user@example.com\",\"subject\":\"Test\",\"body\":\"Hello!\"}'")
    print("\n2. Register user with saga:")
    print("   curl -X POST 'http://localhost:8000/api/register-user' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -H 'Idempotency-Key: user-reg-456' \\")
    print("     -d '{\"username\":\"johndoe\",\"email\":\"john@example.com\",\"full_name\":\"John Doe\",\"send_welcome_email\":true}'")
    print("\n3. Check operation status:")
    print("   curl 'http://localhost:8000/api/status/email-test-123'")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)