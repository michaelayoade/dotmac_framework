"""
Base class for integration testing with common fixtures and utilities
"""
import asyncio
import pytest
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class IntegrationTestBase:
    """
    Base class for integration tests providing common fixtures and utilities
    """
    
    def __init__(self):
        self._test_data_cleanup = []
        self._service_connections = {}
        self._test_databases = {}
        
    @pytest.fixture(autouse=True)
    async def base_setup(self):
        """Base setup for all integration tests"""
        logger.info("Setting up integration test base")
        
        # Initialize test environment
        await self._setup_test_environment()
        
        yield
        
        # Cleanup
        await self._cleanup_test_environment()
        
    async def _setup_test_environment(self):
        """Setup test environment with necessary services"""
        # Initialize database connections, message queues, etc.
        logger.info("Initializing test environment")
        
    async def _cleanup_test_environment(self):
        """Cleanup test environment and test data"""
        logger.info("Cleaning up test environment")
        
        # Clean up test data
        for cleanup_func in reversed(self._test_data_cleanup):
            try:
                await cleanup_func()
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        
        # Close service connections
        for service_name, connection in self._service_connections.items():
            try:
                if hasattr(connection, 'close'):
                    await connection.close()
                elif hasattr(connection, 'disconnect'):
                    await connection.disconnect()
            except Exception as e:
                logger.warning(f"Failed to close {service_name} connection: {e}")
                
    def register_cleanup(self, cleanup_func):
        """Register a cleanup function to be called after test"""
        self._test_data_cleanup.append(cleanup_func)
        
    async def create_test_customer(self, **kwargs) -> Dict[str, Any]:
        """Create a test customer for integration testing"""
        import uuid
        from datetime import datetime
        
        customer_data = {
            "id": str(uuid.uuid4()),
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Test",
            "last_name": "Customer",
            "created_at": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        # Register cleanup for this test data
        self.register_cleanup(lambda: self._cleanup_customer(customer_data["id"]))
        
        return customer_data
        
    async def _cleanup_customer(self, customer_id: str):
        """Clean up test customer data"""
        logger.info(f"Cleaning up test customer: {customer_id}")
        
    async def wait_for_event(self, event_type: str, correlation_id: str, timeout: int = 30) -> Optional[Dict]:
        """Wait for a specific event to occur"""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check for event (implementation would query event store/message bus)
            await asyncio.sleep(0.1)
            
        return None
        
    async def assert_event_sequence(self, expected_events: list, correlation_id: str, timeout: int = 30):
        """Assert that events occurred in the expected sequence"""
        events = []
        start_time = asyncio.get_event_loop().time()
        
        while len(events) < len(expected_events) and (asyncio.get_event_loop().time() - start_time) < timeout:
            # Poll for events
            await asyncio.sleep(0.1)
            
        assert len(events) == len(expected_events), f"Expected {len(expected_events)} events, got {len(events)}"
        
    @asynccontextmanager
    async def temporary_service_failure(self, service_name: str):
        """Context manager to simulate temporary service failure"""
        logger.info(f"Simulating failure for {service_name}")
        # Implementation would inject failure
        try:
            yield
        finally:
            logger.info(f"Restoring {service_name}")
            # Implementation would restore service