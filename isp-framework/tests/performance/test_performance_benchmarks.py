"""Performance tests for DotMac ISP Framework.

Tests performance characteristics including:
- API response times
- Database query performance 
- Concurrent user handling
- Memory usage optimization
- Background job processing
- Network integration performance
- Large dataset handling
- Cache effectiveness
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import mean, median
from typing import List, Dict, Any, Callable
from uuid import uuid4
import psutil
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from dotmac_isp.modules.identity.models import Customer, CustomerType
from dotmac_isp.modules.billing.models import Invoice, InvoiceStatus, InvoiceLineItem
from dotmac_isp.modules.services.models import Service, ServiceType, ServiceStatus
from dotmac_isp.modules.support.models import Ticket, TicketStatus
from dotmac_isp.core.cache import CacheManager
from dotmac_isp.core.database import get_async_db


@pytest.mark.performance
@pytest.mark.api_response_times
class TestAPIResponseTimes:
    """Test API endpoint response time performance."""
    
    async def test_customer_crud_performance(self, async_client, auth_headers):
        """Test customer CRUD operation response times."""
        
        # Performance targets (in seconds)
        TARGET_CREATE_TIME = 0.5
        TARGET_READ_TIME = 0.2
        TARGET_UPDATE_TIME = 0.3
        TARGET_DELETE_TIME = 0.3
        
        customer_data = {
            "customer_number": "PERF_CUST001",
            "first_name": "Performance", 
            "last_name": "Test",
            "email_primary": "perf.test@example.com",
            "phone_primary": "555-PERF-001",
            "customer_type": "residential"
        }
        
        # Test CREATE performance
        start_time = time.time()
        create_response = await async_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=auth_headers
        )
        create_time = time.time() - start_time
        
        assert create_response.status_code == 201
        assert create_time <= TARGET_CREATE_TIME, f"Customer creation took {create_time:.3f}s (target: {TARGET_CREATE_TIME}s)"
        
        customer_id = create_response.json()["id"]
        
        # Test READ performance
        start_time = time.time()
        read_response = await async_client.get(
            f"/api/v1/customers/{customer_id}",
            headers=auth_headers
        )
        read_time = time.time() - start_time
        
        assert read_response.status_code == 200
        assert read_time <= TARGET_READ_TIME, f"Customer read took {read_time:.3f}s (target: {TARGET_READ_TIME}s)"
        
        # Test UPDATE performance
        update_data = {"phone_primary": "555-UPDATED"}
        start_time = time.time()
        update_response = await async_client.patch(
            f"/api/v1/customers/{customer_id}",
            json=update_data,
            headers=auth_headers
        )
        update_time = time.time() - start_time
        
        assert update_response.status_code == 200
        assert update_time <= TARGET_UPDATE_TIME, f"Customer update took {update_time:.3f}s (target: {TARGET_UPDATE_TIME}s)"
        
        # Test DELETE performance
        start_time = time.time()
        delete_response = await async_client.delete(
            f"/api/v1/customers/{customer_id}",
            headers=auth_headers
        )
        delete_time = time.time() - start_time
        
        assert delete_response.status_code == 204
        assert delete_time <= TARGET_DELETE_TIME, f"Customer delete took {delete_time:.3f}s (target: {TARGET_DELETE_TIME}s)"
    
    async def test_invoice_generation_performance(self, async_client, auth_headers, performance_test_data):
        """Test invoice generation performance with complex billing rules."""
        
        TARGET_GENERATION_TIME = 2.0  # 2 seconds for complex invoice
        
        # Create customer with multiple services
        customer_data = performance_test_data["customers"][0]
        services_data = performance_test_data["services"][:5]  # 5 services
        
        customer_response = await async_client.post(
            "/api/v1/customers",
            json=customer_data,
            headers=auth_headers
        )
        customer_id = customer_response.json()["id"]
        
        # Create multiple services for the customer
        service_ids = []
        for service_data in services_data:
            service_data["customer_id"] = customer_id
            service_response = await async_client.post(
                "/api/v1/services",
                json=service_data,
                headers=auth_headers
            )
            service_ids.append(service_response.json()["id"])
        
        # Test invoice generation performance
        invoice_request = {
            "customer_id": customer_id,
            "billing_period_start": "2024-01-01",
            "billing_period_end": "2024-01-31",
            "services": service_ids,
            "include_usage": True,
            "apply_discounts": True,
            "calculate_taxes": True
        }
        
        start_time = time.time()
        invoice_response = await async_client.post(
            "/api/v1/billing/invoices/generate",
            json=invoice_request,
            headers=auth_headers
        )
        generation_time = time.time() - start_time
        
        assert invoice_response.status_code == 201
        assert generation_time <= TARGET_GENERATION_TIME, \
            f"Invoice generation took {generation_time:.3f}s (target: {TARGET_GENERATION_TIME}s)"
        
        # Verify invoice complexity (multiple line items, taxes, etc.)
        invoice_data = invoice_response.json()
        assert len(invoice_data["line_items"]) >= 5  # At least one per service
        assert invoice_data["tax_amount"] > 0
        assert invoice_data["total_amount"] > 0
    
    async def test_search_api_performance(self, async_client, auth_headers, db_session):
        """Test search API performance with large datasets."""
        
        TARGET_SEARCH_TIME = 1.0  # 1 second for search
        DATASET_SIZE = 1000
        
        # Create large dataset for search performance testing
        tenant_id = str(uuid4())
        customers = []
        
        for i in range(DATASET_SIZE):
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"SEARCH_PERF_{i:04d}",
                first_name=f"SearchCustomer{i}",
                last_name="Performance",
                email_primary=f"search.perf.{i}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers.append(customer)
        
        # Batch insert for performance
        db_session.add_all(customers)
        await db_session.commit()
        
        # Test search performance
        search_queries = [
            "SearchCustomer500",  # Exact match
            "Performance",        # Common last name (many results)
            "search.perf.750",    # Email search
            "SEARCH_PERF_0100"    # Customer number search
        ]
        
        for query in search_queries:
            start_time = time.time()
            search_response = await async_client.get(
                f"/api/v1/customers/search",
                params={"q": query, "limit": 50},
                headers=auth_headers
            )
            search_time = time.time() - start_time
            
            assert search_response.status_code == 200
            assert search_time <= TARGET_SEARCH_TIME, \
                f"Search for '{query}' took {search_time:.3f}s (target: {TARGET_SEARCH_TIME}s)"
            
            # Verify search results are relevant
            results = search_response.json()["customers"]
            assert len(results) > 0, f"No results found for query: {query}"
    
    async def test_bulk_operations_performance(self, async_client, auth_headers):
        """Test bulk operation performance."""
        
        TARGET_BULK_CREATE_TIME = 5.0  # 5 seconds for 100 customers
        BULK_SIZE = 100
        
        # Generate bulk customer data
        bulk_customers = []
        for i in range(BULK_SIZE):
            customer_data = {
                "customer_number": f"BULK_PERF_{i:03d}",
                "first_name": f"BulkCustomer{i}",
                "last_name": "Performance",
                "email_primary": f"bulk.perf.{i}@example.com",
                "customer_type": "residential"
            }
            bulk_customers.append(customer_data)
        
        # Test bulk create performance
        start_time = time.time()
        bulk_response = await async_client.post(
            "/api/v1/customers/bulk",
            json={"customers": bulk_customers},
            headers=auth_headers
        )
        bulk_time = time.time() - start_time
        
        assert bulk_response.status_code == 201
        assert bulk_time <= TARGET_BULK_CREATE_TIME, \
            f"Bulk customer creation took {bulk_time:.3f}s (target: {TARGET_BULK_CREATE_TIME}s)"
        
        # Verify all customers were created
        result = bulk_response.json()
        assert result["created_count"] == BULK_SIZE
        assert len(result["failed_items"]) == 0


@pytest.mark.performance
@pytest.mark.database_performance
class TestDatabaseQueryPerformance:
    """Test database query performance optimization."""
    
    async def test_complex_join_query_performance(self, db_session):
        """Test performance of complex multi-table joins."""
        
        TARGET_QUERY_TIME = 1.0  # 1 second for complex join
        DATASET_SIZE = 500
        
        tenant_id = str(uuid4())
        
        # Create test dataset with relationships
        customers = []
        services = []
        invoices = []
        
        for i in range(DATASET_SIZE):
            customer_id = str(uuid4())
            
            # Customer
            customer = Customer(
                id=customer_id,
                customer_number=f"COMPLEX_CUST_{i:03d}",
                first_name=f"Complex{i}",
                last_name="QueryTest",
                email_primary=f"complex.{i}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers.append(customer)
            
            # Services for customer
            for j in range(2):  # 2 services per customer
                service_id = str(uuid4())
                service = Service(
                    id=service_id,
                    service_id=f"SVC_COMPLEX_{i}_{j}",
                    customer_id=customer_id,
                    service_type=ServiceType.INTERNET if j == 0 else ServiceType.VOIP,
                    plan_name=f"Plan {j}",
                    monthly_price=Decimal(f'{100 + j * 50}.00'),
                    status=ServiceStatus.ACTIVE,
                    tenant_id=tenant_id,
                    created_by=str(uuid4())
                )
                services.append(service)
            
            # Invoices for customer
            for k in range(3):  # 3 invoices per customer
                invoice_id = str(uuid4())
                invoice = Invoice(
                    id=invoice_id,
                    invoice_number=f"INV_COMPLEX_{i}_{k}",
                    customer_id=customer_id,
                    billing_period_start=datetime(2024, k+1, 1).date(),
                    billing_period_end=datetime(2024, k+1, 28).date(),
                    subtotal=Decimal(f'{150 + k * 25}.00'),
                    tax_amount=Decimal(f'{15 + k * 2.5}.00'),
                    total_amount=Decimal(f'{165 + k * 27.5}.00'),
                    status=InvoiceStatus.PAID if k < 2 else InvoiceStatus.PENDING,
                    tenant_id=tenant_id,
                    created_by=str(uuid4())
                )
                invoices.append(invoice)
        
        # Batch insert data
        db_session.add_all(customers + services + invoices)
        await db_session.commit()
        
        # Test complex join query performance
        complex_query = (
            select(
                Customer.customer_number,
                Customer.first_name,
                Customer.last_name,
                func.count(Service.id.distinct().label('service_count'),
                func.count(Invoice.id).label('invoice_count'),
                func.sum(Invoice.total_amount).label('total_billed'),
                func.sum(
                    case(
                        (Invoice.status == InvoiceStatus.PAID, Invoice.total_amount),
                        else_=0
                    )
                ).label('total_paid')
            )
            .select_from(Customer)
            .join(Service, Customer.id == Service.customer_id)
            .join(Invoice, Customer.id == Invoice.customer_id)
            .where(Customer.tenant_id == tenant_id)
            .group_by(Customer.id, Customer.customer_number, Customer.first_name, Customer.last_name)
            .having(func.count(Invoice.id) >= 2)
            .order_by(Customer.customer_number)
        )
        
        start_time = time.time()
        result = await db_session.execute(complex_query)
        rows = result.all()
        query_time = time.time() - start_time
        
        assert len(rows) == DATASET_SIZE  # All customers have >= 2 invoices
        assert query_time <= TARGET_QUERY_TIME, \
            f"Complex join query took {query_time:.3f}s (target: {TARGET_QUERY_TIME}s)"
        
        # Verify query results are correct
        first_row = rows[0]
        assert first_row.service_count == 2
        assert first_row.invoice_count == 3
        assert first_row.total_billed > Decimal('400.00')
    
    async def test_aggregation_query_performance(self, db_session):
        """Test performance of aggregation queries on large datasets."""
        
        TARGET_AGGREGATION_TIME = 2.0  # 2 seconds for aggregations
        DATASET_SIZE = 2000
        
        tenant_id = str(uuid4())
        
        # Create large invoice dataset
        invoices = []
        for i in range(DATASET_SIZE):
            invoice = Invoice(
                id=str(uuid4()),
                invoice_number=f"AGG_INV_{i:04d}",
                customer_id=str(uuid4()),
                billing_period_start=datetime(2024, (i % 12) + 1, 1).date(),
                billing_period_end=datetime(2024, (i % 12) + 1, 28).date(),
                subtotal=Decimal(f'{50 + (i % 500)}.00'),
                tax_amount=Decimal(f'{5 + (i % 50)}.00'),
                total_amount=Decimal(f'{55 + (i % 550)}.00'),
                status=InvoiceStatus.PAID if i % 3 == 0 else InvoiceStatus.PENDING,
                tenant_id=tenant_id,
                created_by=str(uuid4()),
                created_at=datetime(2024, (i % 12) + 1, (i % 28) + 1)
            )
            invoices.append(invoice)
        
        db_session.add_all(invoices)
        await db_session.commit()
        
        # Test monthly revenue aggregation
        monthly_revenue_query = (
            select(
                func.extract('month', Invoice.billing_period_start).label('month'),
                func.count(Invoice.id).label('invoice_count'),
                func.sum(Invoice.total_amount).label('total_revenue'),
                func.avg(Invoice.total_amount).label('avg_invoice'),
                func.max(Invoice.total_amount).label('max_invoice'),
                func.min(Invoice.total_amount).label('min_invoice')
            )
            .where(Invoice.tenant_id == tenant_id)
            .group_by(func.extract('month', Invoice.billing_period_start)
            .order_by('month')
        )
        
        start_time = time.time()
        result = await db_session.execute(monthly_revenue_query)
        monthly_stats = result.all()
        aggregation_time = time.time() - start_time
        
        assert len(monthly_stats) == 12  # 12 months
        assert aggregation_time <= TARGET_AGGREGATION_TIME, \
            f"Aggregation query took {aggregation_time:.3f}s (target: {TARGET_AGGREGATION_TIME}s)"
        
        # Verify aggregation correctness
        total_invoices = sum(month.invoice_count for month in monthly_stats)
        assert total_invoices == DATASET_SIZE
    
    async def test_pagination_performance(self, db_session):
        """Test pagination performance with large result sets."""
        
        TARGET_PAGE_TIME = 0.5  # 0.5 seconds per page
        DATASET_SIZE = 5000
        PAGE_SIZE = 50
        
        tenant_id = str(uuid4())
        
        # Create large customer dataset
        customers = []
        for i in range(DATASET_SIZE):
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"PAGE_CUST_{i:05d}",
                first_name=f"PageCustomer{i}",
                last_name="PaginationTest",
                email_primary=f"page.{i}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        await db_session.commit()
        
        # Test pagination performance for different pages
        test_pages = [0, 25, 50, 75, 99]  # Different positions in dataset
        
        for page_num in test_pages:
            offset = page_num * PAGE_SIZE
            
            paginated_query = (
                select(Customer)
                .where(Customer.tenant_id == tenant_id)
                .order_by(Customer.customer_number)
                .offset(offset)
                .limit(PAGE_SIZE)
            )
            
            start_time = time.time()
            result = await db_session.execute(paginated_query)
            page_customers = result.scalars().all()
            page_time = time.time() - start_time
            
            assert len(page_customers) == PAGE_SIZE
            assert page_time <= TARGET_PAGE_TIME, \
                f"Page {page_num} took {page_time:.3f}s (target: {TARGET_PAGE_TIME}s)"
            
            # Verify pagination correctness
            expected_start_num = f"PAGE_CUST_{offset:05d}"
            assert page_customers[0].customer_number == expected_start_num
    
    async def test_full_text_search_performance(self, db_session):
        """Test full-text search performance optimization."""
        
        TARGET_SEARCH_TIME = 0.8  # 0.8 seconds for search
        DATASET_SIZE = 3000
        
        tenant_id = str(uuid4())
        
        # Create dataset with varied searchable content
        customers = []
        search_terms = [
            "TechCorp", "MediaInc", "ConsultingGroup", "SolutionsLLC", "InnovationsCorp",
            "EngineeringFirm", "DesignStudio", "MarketingAgency", "SoftwareHouse", "DataSystems"
        ]
        
        for i in range(DATASET_SIZE):
            company_term = search_terms[i % len(search_terms)]
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"SEARCH_{i:04d}",
                first_name=f"SearchTest{i}",
                last_name="Customer",
                email_primary=f"search.{i}@{company_term.lower()}.com",
                company_name=f"{company_term} {i}",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        await db_session.commit()
        
        # Test search performance for different patterns
        search_patterns = [
            ("TechCorp", "Company name search"),
            ("search.150", "Email prefix search"), 
            ("Customer", "Last name search"),
            ("SearchTest2", "First name search")
        ]
        
        for search_term, description in search_patterns:
            search_query = (
                select(Customer)
                .where(
                    and_(
                        Customer.tenant_id == tenant_id,
                        or_(
                            Customer.first_name.ilike(f'%{search_term}%'),
                            Customer.last_name.ilike(f'%{search_term}%'),
                            Customer.email_primary.ilike(f'%{search_term}%'),
                            Customer.company_name.ilike(f'%{search_term}%')
                        )
                    )
                )
                .order_by(Customer.customer_number)
                .limit(100)
            )
            
            start_time = time.time()
            result = await db_session.execute(search_query)
            search_results = result.scalars().all()
            search_time = time.time() - start_time
            
            assert len(search_results) > 0, f"No results for search: {search_term}"
            assert search_time <= TARGET_SEARCH_TIME, \
                f"{description} took {search_time:.3f}s (target: {TARGET_SEARCH_TIME}s)"


@pytest.mark.performance
@pytest.mark.concurrent_users  
class TestConcurrentUserHandling:
    """Test system performance under concurrent user load."""
    
    async def test_concurrent_api_requests(self, async_client, auth_headers):
        """Test API performance under concurrent request load."""
        
        TARGET_CONCURRENT_RESPONSE_TIME = 2.0  # 2 seconds under load
        CONCURRENT_USERS = 50
        REQUESTS_PER_USER = 10
        
        async def simulate_user_session(user_id: int):
            """Simulate a user performing multiple API operations."""
            session_times = []
            
            for request_num in range(REQUESTS_PER_USER):
                # Mix of different API operations
                operations = [
                    ("GET", "/api/v1/customers", {}),
                    ("GET", "/api/v1/services", {}),
                    ("GET", "/api/v1/billing/invoices", {}),
                    ("POST", "/api/v1/customers/search", {"q": f"user{user_id}"}),
                ]
                
                method, endpoint, data = operations[request_num % len(operations)]
                
                start_time = time.time()
                
                if method == "GET":
                    response = await async_client.get(endpoint, headers=auth_headers)
                else:
                    response = await async_client.post(endpoint, json=data, headers=auth_headers)
                
                request_time = time.time() - start_time
                session_times.append(request_time)
                
                # Verify response is valid
                assert response.status_code in [200, 201, 404]  # 404 acceptable for searches with no results
            
            return session_times
        
        # Run concurrent user sessions
        start_time = time.time()
        
        tasks = []
        for user_id in range(CONCURRENT_USERS):
            task = asyncio.create_task(simulate_user_session(user_id)
            tasks.append(task)
        
        # Wait for all user sessions to complete
        all_session_times = await asyncio.gather(*tasks)
        
        total_test_time = time.time() - start_time
        
        # Analyze performance results
        all_request_times = [time for session in all_session_times for time in session]
        
        avg_response_time = mean(all_request_times)
        median_response_time = median(all_request_times)
        max_response_time = max(all_request_times)
        
        total_requests = CONCURRENT_USERS * REQUESTS_PER_USER
        requests_per_second = total_requests / total_test_time
        
        # Performance assertions
        assert avg_response_time <= TARGET_CONCURRENT_RESPONSE_TIME, \
            f"Average response time {avg_response_time:.3f}s exceeds target {TARGET_CONCURRENT_RESPONSE_TIME}s"
        
        assert requests_per_second >= 25, \
            f"Request throughput {requests_per_second:.1f} RPS is too low"
        
        # Verify no requests failed due to timeouts or errors
        assert max_response_time <= 10.0, \
            f"Maximum response time {max_response_time:.3f}s indicates system overload"
    
    async def test_concurrent_database_operations(self, db_session):
        """Test database performance under concurrent operation load."""
        
        TARGET_CONCURRENT_DB_TIME = 1.5  # 1.5 seconds per operation under load
        CONCURRENT_OPERATIONS = 20
        
        tenant_id = str(uuid4())
        
        async def concurrent_database_operation(operation_id: int):
            """Perform database operations concurrently."""
            operation_times = []
            
            # Create customer
            start_time = time.time()
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"CONCURRENT_{operation_id:03d}",
                first_name=f"Concurrent{operation_id}",
                last_name="DbTest",
                email_primary=f"concurrent.{operation_id}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            db_session.add(customer)
            await db_session.flush()
            create_time = time.time() - start_time
            operation_times.append(create_time)
            
            # Query customer
            start_time = time.time()
            query = select(Customer).where(Customer.id == customer.id)
            result = await db_session.execute(query)
            queried_customer = result.scalar_one()
            query_time = time.time() - start_time
            operation_times.append(query_time)
            
            # Update customer
            start_time = time.time()
            queried_customer.phone_primary = f"555-{operation_id:04d}"
            await db_session.flush()
            update_time = time.time() - start_time
            operation_times.append(update_time)
            
            return operation_times
        
        # Run concurrent database operations
        tasks = []
        for op_id in range(CONCURRENT_OPERATIONS):
            task = asyncio.create_task(concurrent_database_operation(op_id)
            tasks.append(task)
        
        all_operation_times = await asyncio.gather(*tasks)
        await db_session.commit()
        
        # Analyze database performance
        all_db_times = [time for operation in all_operation_times for time in operation]
        avg_db_time = mean(all_db_times)
        max_db_time = max(all_db_times)
        
        assert avg_db_time <= TARGET_CONCURRENT_DB_TIME, \
            f"Average DB operation time {avg_db_time:.3f}s exceeds target {TARGET_CONCURRENT_DB_TIME}s"
        
        assert max_db_time <= 5.0, \
            f"Maximum DB operation time {max_db_time:.3f}s indicates database overload"
        
        # Verify all operations completed successfully
        customer_count_query = select(func.count(Customer.id).where(Customer.tenant_id == tenant_id)
        result = await db_session.execute(customer_count_query)
        customer_count = result.scalar()
        
        assert customer_count == CONCURRENT_OPERATIONS
    
    async def test_memory_usage_under_load(self, async_client, auth_headers):
        """Test memory usage stability under concurrent load."""
        
        MAX_MEMORY_INCREASE_MB = 100  # Max 100MB increase during test
        LOAD_DURATION = 30  # 30 seconds of load testing
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory_mb = process.memory_info().rss / 1024 / 1024
        
        async def memory_stress_operation():
            """Operation designed to test memory usage."""
            # Create customer with multiple related records
            customer_data = {
                "customer_number": f"MEM_TEST_{uuid4().hex[:8]}",
                "first_name": "MemoryTest",
                "last_name": "Customer",
                "email_primary": f"memory.test.{uuid4().hex[:8]}@example.com"
            }
            
            response = await async_client.post(
                "/api/v1/customers",
                json=customer_data,
                headers=auth_headers
            )
            
            if response.status_code == 201:
                # Perform additional operations that use memory
                customer_id = response.json()["id"]
                
                # Create services
                for i in range(3):
                    service_data = {
                        "customer_id": customer_id,
                        "service_type": "internet",
                        "plan_name": f"MemoryTest Plan {i}",
                        "monthly_price": 100.00
                    }
                    await async_client.post(
                        "/api/v1/services",
                        json=service_data,
                        headers=auth_headers
                    )
                
                # Query customer data (loads related records into memory)
                await async_client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
                await async_client.get(f"/api/v1/customers/{customer_id}/services", headers=auth_headers)
        
        # Run memory stress test
        start_time = time.time()
        stress_tasks = []
        
        while time.time() - start_time < LOAD_DURATION:
            # Start new operations every 0.1 seconds
            task = asyncio.create_task(memory_stress_operation()
            stress_tasks.append(task)
            
            await asyncio.sleep(0.1)
            
            # Clean up completed tasks to prevent memory accumulation
            completed_tasks = [task for task in stress_tasks if task.done()]
            for task in completed_tasks:
                stress_tasks.remove(task)
                await task  # Ensure exceptions are handled
        
        # Wait for remaining tasks to complete
        if stress_tasks:
            await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        # Check final memory usage
        final_memory_mb = process.memory_info().rss / 1024 / 1024
        memory_increase_mb = final_memory_mb - initial_memory_mb
        
        assert memory_increase_mb <= MAX_MEMORY_INCREASE_MB, \
            f"Memory increased by {memory_increase_mb:.1f}MB (max allowed: {MAX_MEMORY_INCREASE_MB}MB)"
        
        # Force garbage collection to verify no memory leaks
        import gc
        gc.collect()
        
        post_gc_memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Memory should not significantly increase after garbage collection
        assert post_gc_memory_mb <= final_memory_mb + 10, \
            "Potential memory leak detected - memory did not decrease after garbage collection"


@pytest.mark.performance
@pytest.mark.cache_effectiveness
class TestCachePerformance:
    """Test cache performance and effectiveness."""
    
    async def test_database_query_caching(self, db_session):
        """Test database query result caching performance."""
        
        cache_manager = CacheManager()
        tenant_id = str(uuid4())
        
        # Create test data
        customers = []
        for i in range(100):
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"CACHE_CUST_{i:03d}",
                first_name=f"CacheCustomer{i}",
                last_name="CacheTest",
                email_primary=f"cache.{i}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers.append(customer)
        
        db_session.add_all(customers)
        await db_session.commit()
        
        # Test query without cache (cold)
        query = select(Customer).where(Customer.tenant_id == tenant_id).order_by(Customer.customer_number)
        cache_key = f"customers:tenant:{tenant_id}"
        
        start_time = time.time()
        result = await db_session.execute(query)
        customers_cold = result.scalars().all()
        cold_query_time = time.time() - start_time
        
        # Cache the results
        await cache_manager.set(cache_key, customers_cold, ttl=300)  # 5 minute TTL
        
        # Test query with cache (warm)
        start_time = time.time()
        customers_cached = await cache_manager.get(cache_key)
        cache_hit_time = time.time() - start_time
        
        assert customers_cached is not None
        assert len(customers_cached) == 100
        
        # Cache should be significantly faster
        cache_speedup = cold_query_time / cache_hit_time
        assert cache_speedup >= 10, \
            f"Cache speedup {cache_speedup:.1f}x is too low (should be >=10x)"
        
        # Verify cache hit time is very fast
        assert cache_hit_time <= 0.01, \
            f"Cache hit time {cache_hit_time:.4f}s is too slow"
    
    async def test_api_response_caching(self, async_client, auth_headers):
        """Test API response caching effectiveness."""
        
        # Make initial API request (cache miss)
        start_time = time.time()
        first_response = await async_client.get(
            "/api/v1/customers",
            params={"limit": 50, "page": 1},
            headers=auth_headers
        )
        first_request_time = time.time() - start_time
        
        assert first_response.status_code == 200
        
        # Make same request again (should be cached)
        start_time = time.time()
        second_response = await async_client.get(
            "/api/v1/customers", 
            params={"limit": 50, "page": 1},
            headers=auth_headers
        )
        second_request_time = time.time() - start_time
        
        assert second_response.status_code == 200
        assert second_response.json() == first_response.json()
        
        # Second request should be faster due to caching
        if second_request_time > 0:  # Avoid division by zero
            speedup = first_request_time / second_request_time
            assert speedup >= 2, \
                f"Cache speedup {speedup:.1f}x is too low (should be >=2x)"
        
        # Verify cached response has cache headers
        cache_headers = second_response.headers
        assert 'cache-control' in cache_headers or 'etag' in cache_headers
    
    async def test_cache_invalidation_performance(self, db_session):
        """Test cache invalidation performance and correctness."""
        
        cache_manager = CacheManager()
        tenant_id = str(uuid4())
        
        # Create and cache customer data
        customer = Customer(
            id=str(uuid4()),
            customer_number="CACHE_INVALIDATE_001",
            first_name="CacheInvalidation",
            last_name="Test",
            email_primary="cache.invalidate@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(customer)
        await db_session.commit()
        
        # Cache customer data
        cache_key = f"customer:{customer.id}"
        await cache_manager.set(cache_key, customer, ttl=300)
        
        # Verify data is cached
        cached_customer = await cache_manager.get(cache_key)
        assert cached_customer is not None
        assert cached_customer.first_name == "CacheInvalidation"
        
        # Update customer (should trigger cache invalidation)
        customer.first_name = "UpdatedCacheInvalidation"
        await db_session.commit()
        
        # Test cache invalidation performance
        start_time = time.time()
        await cache_manager.delete(cache_key)
        invalidation_time = time.time() - start_time
        
        assert invalidation_time <= 0.1, \
            f"Cache invalidation took {invalidation_time:.3f}s (should be <=0.1s)"
        
        # Verify cache was invalidated
        invalidated_customer = await cache_manager.get(cache_key)
        assert invalidated_customer is None
        
        # Test pattern-based cache invalidation
        pattern_keys = [
            f"customer:{customer.id}:services",
            f"customer:{customer.id}:invoices", 
            f"customer:{customer.id}:profile"
        ]
        
        # Set multiple cache entries
        for key in pattern_keys:
            await cache_manager.set(key, {"test": "data"}, ttl=300)
        
        # Test pattern invalidation performance
        start_time = time.time()
        await cache_manager.delete_pattern(f"customer:{customer.id}:*")
        pattern_invalidation_time = time.time() - start_time
        
        assert pattern_invalidation_time <= 0.2, \
            f"Pattern cache invalidation took {pattern_invalidation_time:.3f}s (should be <=0.2s)"
        
        # Verify all pattern-matched keys were invalidated
        for key in pattern_keys:
            cached_data = await cache_manager.get(key)
            assert cached_data is None, f"Cache key {key} was not invalidated"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])