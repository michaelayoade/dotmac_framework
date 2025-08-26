"""
Example unit tests for async services and business logic.

This demonstrates best practices for testing:
- Async/await functions
- Mocking external dependencies
- Exception handling
- Service layer logic
- Dependency injection patterns
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response


# Example service interfaces and implementations
class DatabaseError(Exception):
    """Database operation error."""
    pass


class NotificationError(Exception):
    """Notification sending error."""
    pass


class CustomerRepository:
    """Customer repository interface."""
    
    async def get_by_id(self, customer_id: str) -> Optional[Dict]:
        """Get customer by ID."""
        raise NotImplementedError
    
    async def create(self, customer_data: Dict) -> Dict:
        """Create new customer."""
        raise NotImplementedError
    
    async def update(self, customer_id: str, update_data: Dict) -> Dict:
        """Update customer."""
        raise NotImplementedError
    
    async def delete(self, customer_id: str) -> bool:
        """Delete customer."""
        raise NotImplementedError


class NotificationService:
    """Notification service interface."""
    
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email notification."""
        raise NotImplementedError
    
    async def send_sms(self, phone: str, message: str) -> bool:
        """Send SMS notification."""
        raise NotImplementedError


class CustomerService:
    """Customer business logic service."""
    
    def __init__(self, repository: CustomerRepository, notification_service: NotificationService):
        self.repository = repository
        self.notification_service = notification_service
    
    async def create_customer(self, customer_data: Dict) -> Dict:
        """Create a new customer with validation and notifications."""
        # Validate required fields
        required_fields = ['email', 'first_name', 'last_name', 'tenant_id']
        for field in required_fields:
            if not customer_data.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        # Add metadata
        customer_data['id'] = str(uuid4())
        customer_data['created_at'] = datetime.now(timezone.utc).isoformat()
        customer_data['status'] = 'active'
        
        try:
            # Save to database
            customer = await self.repository.create(customer_data)
            
            # Send welcome email
            await self.notification_service.send_email(
                to=customer['email'],
                subject="Welcome to our service!",
                body=f"Hello {customer['first_name']}, welcome to our platform!"
            )
            
            return customer
            
        except Exception as e:
            # Log error and re-raise with context
            print(f"Failed to create customer: {e}")
            raise DatabaseError(f"Customer creation failed: {str(e)}")
    
    async def update_customer_status(self, customer_id: str, status: str) -> Dict:
        """Update customer status with notifications."""
        valid_statuses = {'active', 'suspended', 'cancelled'}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")
        
        # Get existing customer
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")
        
        # Update status
        update_data = {
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        updated_customer = await self.repository.update(customer_id, update_data)
        
        # Send status change notification
        if status == 'suspended':
            await self.notification_service.send_email(
                to=customer['email'],
                subject="Account Suspended",
                body="Your account has been suspended. Please contact support."
            )
        elif status == 'cancelled':
            await self.notification_service.send_email(
                to=customer['email'],
                subject="Account Cancelled", 
                body="Your account has been cancelled."
            )
        
        return updated_customer
    
    async def get_customer_with_metrics(self, customer_id: str) -> Dict:
        """Get customer with calculated metrics."""
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer not found: {customer_id}")
        
        # Add calculated fields
        customer['account_age_days'] = self._calculate_account_age(customer['created_at'])
        customer['is_new_customer'] = customer['account_age_days'] < 30
        
        return customer
    
    async def bulk_update_status(self, customer_ids: List[str], status: str) -> Dict:
        """Update status for multiple customers."""
        results = {'success': [], 'failed': []}
        
        for customer_id in customer_ids:
            try:
                await self.update_customer_status(customer_id, status)
                results['success'].append(customer_id)
            except Exception as e:
                results['failed'].append({'customer_id': customer_id, 'error': str(e)})
        
        return results
    
    def _calculate_account_age(self, created_at: str) -> int:
        """Calculate account age in days."""
        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')
        now = datetime.now(timezone.utc)
        return (now - created_date).days


# Test fixtures
@pytest_asyncio.fixture
async def mock_repository():
    """Mock customer repository."""
    repository = AsyncMock(spec=CustomerRepository)
    return repository


@pytest_asyncio.fixture
async def mock_notification_service():
    """Mock notification service."""
    service = AsyncMock(spec=NotificationService)
    service.send_email.return_value = True
    service.send_sms.return_value = True
    return service


@pytest_asyncio.fixture
async def customer_service(mock_repository, mock_notification_service):
    """Customer service with mocked dependencies."""
    return CustomerService(mock_repository, mock_notification_service)


@pytest.fixture
def valid_customer_data():
    """Valid customer data for testing."""
    return {
        'email': 'test@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'tenant_id': 'test-tenant'
    }


@pytest.fixture
def existing_customer():
    """Existing customer data."""
    return {
        'id': 'customer-123',
        'email': 'existing@example.com',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'tenant_id': 'test-tenant',
        'status': 'active',
        'created_at': '2023-01-01T00:00:00+00:00'
    }


# Unit tests
@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomerServiceCreation:
    """Test customer creation functionality."""
    
    async def test_create_customer_success(self, customer_service, mock_repository, mock_notification_service, valid_customer_data):
        """Test successful customer creation."""
        # Setup mocks
        created_customer = valid_customer_data.copy()
        created_customer['id'] = 'new-customer-id'
        created_customer['status'] = 'active'
        mock_repository.create.return_value = created_customer
        
        # Execute
        result = await customer_service.create_customer(valid_customer_data)
        
        # Verify
        assert result == created_customer
        mock_repository.create.assert_called_once()
        mock_notification_service.send_email.assert_called_once_with(
            to='test@example.com',
            subject='Welcome to our service!',
            body='Hello John, welcome to our platform!'
        )
    
    async def test_create_customer_missing_required_field(self, customer_service, valid_customer_data):
        """Test customer creation with missing required field."""
        del valid_customer_data['email']
        
        with pytest.raises(ValueError, match="Missing required field: email"):
            await customer_service.create_customer(valid_customer_data)
    
    async def test_create_customer_database_error(self, customer_service, mock_repository, valid_customer_data):
        """Test customer creation with database error."""
        mock_repository.create.side_effect = Exception("Database connection failed")
        
        with pytest.raises(DatabaseError, match="Customer creation failed"):
            await customer_service.create_customer(valid_customer_data)
    
    async def test_create_customer_notification_failure(self, customer_service, mock_repository, mock_notification_service, valid_customer_data):
        """Test customer creation when notification fails."""
        # Setup mocks
        created_customer = valid_customer_data.copy()
        created_customer['id'] = 'new-customer-id'
        mock_repository.create.return_value = created_customer
        mock_notification_service.send_email.side_effect = NotificationError("Email service down")
        
        # Should still succeed even if notification fails
        with pytest.raises(DatabaseError):  # Because we re-raise any exception
            await customer_service.create_customer(valid_customer_data)
    
    @pytest.mark.parametrize("missing_field", ['email', 'first_name', 'last_name', 'tenant_id'])
    async def test_create_customer_missing_fields(self, customer_service, valid_customer_data, missing_field):
        """Test creation fails with any missing required field."""
        del valid_customer_data[missing_field]
        
        with pytest.raises(ValueError, match=f"Missing required field: {missing_field}"):
            await customer_service.create_customer(valid_customer_data)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomerServiceStatusUpdate:
    """Test customer status update functionality."""
    
    async def test_update_status_success(self, customer_service, mock_repository, mock_notification_service, existing_customer):
        """Test successful status update."""
        mock_repository.get_by_id.return_value = existing_customer
        updated_customer = existing_customer.copy()
        updated_customer['status'] = 'suspended'
        mock_repository.update.return_value = updated_customer
        
        result = await customer_service.update_customer_status('customer-123', 'suspended')
        
        assert result['status'] == 'suspended'
        mock_repository.get_by_id.assert_called_once_with('customer-123')
        mock_repository.update.assert_called_once()
        mock_notification_service.send_email.assert_called_once_with(
            to='existing@example.com',
            subject='Account Suspended',
            body='Your account has been suspended. Please contact support.'
        )
    
    async def test_update_status_invalid_status(self, customer_service):
        """Test status update with invalid status."""
        with pytest.raises(ValueError, match="Invalid status: invalid"):
            await customer_service.update_customer_status('customer-123', 'invalid')
    
    async def test_update_status_customer_not_found(self, customer_service, mock_repository):
        """Test status update for non-existent customer."""
        mock_repository.get_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Customer not found: customer-123"):
            await customer_service.update_customer_status('customer-123', 'suspended')
    
    @pytest.mark.parametrize("status,expected_subject", [
        ('suspended', 'Account Suspended'),
        ('cancelled', 'Account Cancelled'),
        ('active', None)  # No notification for active status
    ])
    async def test_update_status_notifications(self, customer_service, mock_repository, mock_notification_service, existing_customer, status, expected_subject):
        """Test notifications for different status updates."""
        mock_repository.get_by_id.return_value = existing_customer
        updated_customer = existing_customer.copy()
        updated_customer['status'] = status
        mock_repository.update.return_value = updated_customer
        
        await customer_service.update_customer_status('customer-123', status)
        
        if expected_subject:
            mock_notification_service.send_email.assert_called_once()
            call_args = mock_notification_service.send_email.call_args
            assert call_args[1]['subject'] == expected_subject
        else:
            mock_notification_service.send_email.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomerServiceMetrics:
    """Test customer metrics functionality."""
    
    async def test_get_customer_with_metrics(self, customer_service, mock_repository, existing_customer):
        """Test getting customer with calculated metrics."""
        mock_repository.get_by_id.return_value = existing_customer
        
        result = await customer_service.get_customer_with_metrics('customer-123')
        
        assert 'account_age_days' in result
        assert 'is_new_customer' in result
        assert isinstance(result['account_age_days'], int)
        assert isinstance(result['is_new_customer'], bool)
    
    async def test_get_customer_not_found(self, customer_service, mock_repository):
        """Test getting metrics for non-existent customer."""
        mock_repository.get_by_id.return_value = None
        
        with pytest.raises(ValueError, match="Customer not found: customer-123"):
            await customer_service.get_customer_with_metrics('customer-123')
    
    def test_calculate_account_age(self, customer_service):
        """Test account age calculation."""
        # Test with specific date
        created_at = '2023-01-01T00:00:00+00:00'
        
        with patch('dotmac_services.customer.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 31, tzinfo=timezone.utc)
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            age = customer_service._calculate_account_age(created_at)
            assert age == 30


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomerServiceBulkOperations:
    """Test bulk operations functionality."""
    
    async def test_bulk_update_status_all_success(self, customer_service, mock_repository, existing_customer):
        """Test bulk status update with all successes."""
        customer_ids = ['customer-1', 'customer-2', 'customer-3']
        
        # Mock successful updates
        mock_repository.get_by_id.return_value = existing_customer
        mock_repository.update.return_value = existing_customer
        
        result = await customer_service.bulk_update_status(customer_ids, 'suspended')
        
        assert len(result['success']) == 3
        assert len(result['failed']) == 0
        assert result['success'] == customer_ids
    
    async def test_bulk_update_status_partial_failure(self, customer_service, mock_repository, existing_customer):
        """Test bulk status update with some failures."""
        customer_ids = ['customer-1', 'customer-2', 'customer-3']
        
        # Mock first call succeeds, second fails, third succeeds
        mock_repository.get_by_id.side_effect = [
            existing_customer,  # First customer found
            None,              # Second customer not found
            existing_customer   # Third customer found
        ]
        mock_repository.update.return_value = existing_customer
        
        result = await customer_service.bulk_update_status(customer_ids, 'suspended')
        
        assert len(result['success']) == 2
        assert len(result['failed']) == 1
        assert result['success'] == ['customer-1', 'customer-3']
        assert result['failed'][0]['customer_id'] == 'customer-2'


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncContextManagers:
    """Test async context managers and resource management."""
    
    async def test_async_context_manager_example(self):
        """Test async context manager pattern."""
        
        class AsyncResource:
            def __init__(self):
                self.is_open = False
            
            async def __aenter__(self):
                await asyncio.sleep(0.1)  # Simulate async setup
                self.is_open = True
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await asyncio.sleep(0.1)  # Simulate async cleanup
                self.is_open = False
        
        resource = None
        async with AsyncResource() as r:
            resource = r
            assert r.is_open is True
        
        assert resource.is_open is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncErrorHandling:
    """Test async error handling patterns."""
    
    async def test_async_timeout_handling(self):
        """Test timeout handling in async operations."""
        
        async def slow_operation():
            await asyncio.sleep(2.0)
            return "completed"
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_operation(), timeout=1.0)
    
    async def test_async_exception_propagation(self):
        """Test exception propagation in async functions."""
        
        async def failing_operation():
            await asyncio.sleep(0.1)
            raise ValueError("Operation failed")
        
        async def calling_operation():
            return await failing_operation()
        
        with pytest.raises(ValueError, match="Operation failed"):
            await calling_operation()
    
    async def test_async_concurrent_operations(self):
        """Test concurrent async operations."""
        
        async def async_task(task_id: int, delay: float):
            await asyncio.sleep(delay)
            return f"task-{task_id}"
        
        # Run tasks concurrently
        tasks = [
            async_task(1, 0.1),
            async_task(2, 0.2),
            async_task(3, 0.1)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert results == ["task-1", "task-2", "task-3"]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.slow
class TestAsyncPerformance:
    """Performance tests for async operations."""
    
    async def test_concurrent_vs_sequential(self, benchmark):
        """Compare concurrent vs sequential async operations."""
        
        async def mock_async_operation(delay: float):
            await asyncio.sleep(delay)
            return "completed"
        
        async def sequential_operations():
            results = []
            for i in range(5):
                result = await mock_async_operation(0.01)
                results.append(result)
            return results
        
        async def concurrent_operations():
            tasks = [mock_async_operation(0.01) for _ in range(5)]
            return await asyncio.gather(*tasks)
        
        # Benchmark concurrent operations (should be faster)
        concurrent_result = await benchmark(concurrent_operations)
        assert len(concurrent_result) == 5
        assert all(r == "completed" for r in concurrent_result)