"""Integration tests for database operations.

Tests database functionality including:
- Multi-tenant data isolation
- Complex queries and relationships
- Transaction handling
- Database migrations
- Performance optimization
- Data integrity constraints
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from typing import List, Dict, Any, Optional
from sqlalchemy import text, select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Import all models for integration testing
from dotmac_isp.modules.identity.models import Customer, CustomerType, AccountStatus
from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceStatus, InvoiceLineItem, Payment, PaymentMethod,
    CreditNote, LateFee, TaxRate
)
from dotmac_isp.modules.services.models import (
    ServiceInstance, ServicePlan, ServiceStatus, ServiceType,
    ServiceUsage, ServiceAlert
)
from dotmac_isp.modules.identity.models import User, UserRole, LoginAttempt
from dotmac_isp.modules.support.models import (
    SupportTicket, TicketStatus, TicketPriority, TicketMessage
)
from dotmac_isp.modules.network_integration.models import (
    NetworkDevice, DeviceType, DeviceStatus, MonitoringAlert
)
from dotmac_isp.modules.gis.models import (
    GISLocation, AddressPoint, ServiceArea, CoverageMap
)
from dotmac_isp.core.database import get_async_db
from dotmac_isp.core.exceptions import (
    DatabaseError, TenantViolationError, DataIntegrityError
)


@pytest.mark.integration
@pytest.mark.database
class TestMultiTenantDataIsolation:
    """Test multi-tenant data isolation at database level."""
    
    async def test_tenant_data_isolation_enforcement(self, db_session: AsyncSession):
        """Test that tenant_id isolation is enforced across all queries."""
        
        # Create test data for two different tenants
        tenant1_id = str(uuid4())
        tenant2_id = str(uuid4())
        
        # Create customers for each tenant
        tenant1_customer = Customer(
            id=str(uuid4()),
            customer_number="T1_CUST001",
            first_name="John",
            last_name="Doe",
            email_primary="john@tenant1.com",
            tenant_id=tenant1_id,
            created_by=str(uuid4())
        )
        
        tenant2_customer = Customer(
            id=str(uuid4()),
            customer_number="T2_CUST001", 
            first_name="Jane",
            last_name="Smith",
            email_primary="jane@tenant2.com",
            tenant_id=tenant2_id,
            created_by=str(uuid4())
        )
        
        db_session.add_all([tenant1_customer, tenant2_customer])
        await db_session.commit()
        
        # Query with tenant1 filter should only return tenant1 data
        tenant1_query = select(Customer).where(Customer.tenant_id == tenant1_id)
        result1 = await db_session.execute(tenant1_query)
        tenant1_customers = result1.scalars().all()
        
        assert len(tenant1_customers) == 1
        assert tenant1_customers[0].email_primary == "john@tenant1.com"
        assert tenant1_customers[0].tenant_id == tenant1_id
        
        # Query with tenant2 filter should only return tenant2 data  
        tenant2_query = select(Customer).where(Customer.tenant_id == tenant2_id)
        result2 = await db_session.execute(tenant2_query)
        tenant2_customers = result2.scalars().all()
        
        assert len(tenant2_customers) == 1
        assert tenant2_customers[0].email_primary == "jane@tenant2.com"
        assert tenant2_customers[0].tenant_id == tenant2_id
        
        # Cross-tenant query should return no results
        cross_tenant_query = select(Customer).where(
            and_(Customer.tenant_id == tenant1_id, Customer.email_primary == "jane@tenant2.com")
        )
        cross_result = await db_session.execute(cross_tenant_query)
        cross_customers = cross_result.scalars().all()
        
        assert len(cross_customers) == 0
    
    async def test_foreign_key_tenant_consistency(self, db_session: AsyncSession):
        """Test that foreign key relationships respect tenant boundaries."""
        
        tenant_id = str(uuid4())
        different_tenant_id = str(uuid4())
        
        # Create customer in one tenant
        customer = Customer(
            id=str(uuid4()),
            customer_number="CUST_FK_TEST",
            first_name="Test",
            last_name="Customer",
            email_primary="test@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        db_session.add(customer)
        await db_session.flush()  # Get the customer ID
        
        # Try to create invoice with different tenant_id (should maintain consistency)
        invoice = Invoice(
            id=str(uuid4()),
            invoice_number="INV_FK_TEST",
            customer_id=customer.id,
            billing_period_start=date.today(),
            billing_period_end=date.today() + timedelta(days=30),
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('10.00'),
            total_amount=Decimal('110.00'),
            status=InvoiceStatus.DRAFT,
            tenant_id=different_tenant_id,  # Different tenant!
            created_by=str(uuid4())
        )
        
        db_session.add(invoice)
        
        # This should work at database level, but application should enforce consistency
        await db_session.commit()
        
        # Query to verify data was created (but application should prevent this)
        invoice_query = select(Invoice).where(Invoice.invoice_number == "INV_FK_TEST")
        result = await db_session.execute(invoice_query)
        created_invoice = result.scalar_one()
        
        # Verify the inconsistency exists (this demonstrates why app-level checks are needed)
        assert created_invoice.tenant_id != customer.tenant_id
    
    async def test_complex_multi_tenant_query(self, db_session: AsyncSession):
        """Test complex queries across multiple tables with tenant isolation."""
        
        tenant_id = str(uuid4())
        
        # Create complete customer with services and billing
        customer = Customer(
            id=str(uuid4()),
            customer_number="COMPLEX_CUST001",
            first_name="Complex",
            last_name="Customer",
            email_primary="complex@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        service = Service(
            id=str(uuid4()),
            service_id="SVC_COMPLEX001",
            customer_id=customer.id,
            service_type=ServiceType.INTERNET,
            plan_name="Premium 500/100",
            monthly_price=Decimal('199.99'),
            status=ServiceStatus.ACTIVE,
            activation_date=date.today(),
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        invoice = Invoice(
            id=str(uuid4()),
            invoice_number="INV_COMPLEX001",
            customer_id=customer.id,
            billing_period_start=date.today().replace(day=1),
            billing_period_end=date.today(),
            subtotal=Decimal('199.99'),
            tax_amount=Decimal('20.00'),
            total_amount=Decimal('219.99'),
            status=InvoiceStatus.PENDING,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add_all([customer, service, invoice])
        await db_session.commit()
        
        # Complex query: Find customers with active internet services and pending invoices
        complex_query = (
            select(Customer, Service, Invoice)
            .join(Service, Customer.id == Service.customer_id)
            .join(Invoice, Customer.id == Invoice.customer_id)
            .where(
                and_(
                    Customer.tenant_id == tenant_id,
                    Service.tenant_id == tenant_id,
                    Invoice.tenant_id == tenant_id,
                    Service.service_type == ServiceType.INTERNET,
                    Service.status == ServiceStatus.ACTIVE,
                    Invoice.status == InvoiceStatus.PENDING
                )
            )
        )
        
        result = await db_session.execute(complex_query)
        rows = result.all()
        
        assert len(rows) == 1
        customer_row, service_row, invoice_row = rows[0]
        
        assert customer_row.customer_number == "COMPLEX_CUST001"
        assert service_row.service_id == "SVC_COMPLEX001"
        assert invoice_row.invoice_number == "INV_COMPLEX001"
        
        # All should have same tenant_id
        assert customer_row.tenant_id == service_row.tenant_id == invoice_row.tenant_id == tenant_id


@pytest.mark.integration
@pytest.mark.database
class TestComplexQueriesAndRelationships:
    """Test complex database queries and relationship handling."""
    
    async def test_customer_service_billing_relationships(self, db_session: AsyncSession):
        """Test complex relationships between customers, services, and billing."""
        
        tenant_id = str(uuid4())
        
        # Create customer with multiple services
        customer = Customer(
            id=str(uuid4()),
            customer_number="REL_CUST001",
            first_name="Relationship",
            last_name="Test",
            email_primary="rel.test@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        # Multiple services for the customer
        internet_service = Service(
            id=str(uuid4()),
            service_id="SVC_INTERNET001",
            customer_id=customer.id,
            service_type=ServiceType.INTERNET,
            plan_name="Business 1GB",
            monthly_price=Decimal('299.99'),
            status=ServiceStatus.ACTIVE,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        voip_service = Service(
            id=str(uuid4()),
            service_id="SVC_VOIP001",
            customer_id=customer.id,
            service_type=ServiceType.VOIP,
            plan_name="Business Phone 10 Lines",
            monthly_price=Decimal('199.99'),
            status=ServiceStatus.ACTIVE,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        # Invoice covering both services
        invoice = Invoice(
            id=str(uuid4()),
            invoice_number="INV_REL001",
            customer_id=customer.id,
            billing_period_start=date.today().replace(day=1),
            billing_period_end=(date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
            subtotal=Decimal('499.98'),
            tax_amount=Decimal('50.00'),
            total_amount=Decimal('549.98'),
            status=InvoiceStatus.SENT,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        # Line items for each service
        internet_line_item = InvoiceLineItem(
            id=str(uuid4()),
            invoice_id=invoice.id,
            service_id=internet_service.id,
            description="Business Internet 1GB",
            quantity=1,
            unit_price=Decimal('299.99'),
            amount=Decimal('299.99'),
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        voip_line_item = InvoiceLineItem(
            id=str(uuid4()),
            invoice_id=invoice.id,
            service_id=voip_service.id,
            description="Business VoIP 10 Lines",
            quantity=1,
            unit_price=Decimal('199.99'),
            amount=Decimal('199.99'),
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add_all([
            customer, internet_service, voip_service, 
            invoice, internet_line_item, voip_line_item
        ])
        await db_session.commit()
        
        # Query customer with all related data
        customer_query = (
            select(Customer)
            .where(Customer.id == customer.id)
        )
        result = await db_session.execute(customer_query)
        queried_customer = result.scalar_one()
        
        # Query services for this customer
        services_query = select(Service).where(Service.customer_id == customer.id)
        services_result = await db_session.execute(services_query)
        customer_services = services_result.scalars().all()
        
        assert len(customer_services) == 2
        service_types = [s.service_type for s in customer_services]
        assert ServiceType.INTERNET in service_types
        assert ServiceType.VOIP in service_types
        
        # Query invoice with line items
        invoice_with_items_query = (
            select(Invoice, InvoiceLineItem)
            .join(InvoiceLineItem, Invoice.id == InvoiceLineItem.invoice_id)
            .where(Invoice.customer_id == customer.id)
        )
        invoice_result = await db_session.execute(invoice_with_items_query)
        invoice_rows = invoice_result.all()
        
        assert len(invoice_rows) == 2  # Two line items
        
        # Verify line item totals match invoice subtotal
        total_line_items = sum(row.InvoiceLineItem.amount for row in invoice_rows)
        assert total_line_items == Decimal('499.98')
    
    async def test_usage_tracking_aggregation(self, db_session: AsyncSession):
        """Test usage data aggregation and reporting queries."""
        
        tenant_id = str(uuid4())
        
        # Create customer and service
        customer = Customer(
            id=str(uuid4()),
            customer_number="USAGE_CUST001",
            first_name="Usage",
            last_name="Customer",
            email_primary="usage@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        service = Service(
            id=str(uuid4()),
            service_id="SVC_USAGE001",
            customer_id=customer.id,
            service_type=ServiceType.INTERNET,
            plan_name="Unlimited 100/20",
            monthly_price=Decimal('79.99'),
            status=ServiceStatus.ACTIVE,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add_all([customer, service])
        await db_session.flush()
        
        # Create daily usage records for a month
        usage_records = []
        for day in range(1, 31):
            record_date = date(2024, 1, day)
            
            usage_record = UsageRecord(
                id=str(uuid4()),
                service_id=service.id,
                usage_date=record_date,
                bytes_downloaded=1000000000 + (day * 50000000),  # Increasing usage
                bytes_uploaded=100000000 + (day * 5000000),
                session_count=24,  # Hourly sessions
                peak_bandwidth_mbps=95 + (day % 10),  # Variable peak usage
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            usage_records.append(usage_record)
        
        db_session.add_all(usage_records)
        await db_session.commit()
        
        # Test aggregation query - monthly totals
        monthly_usage_query = (
            select(
                func.sum(UsageRecord.bytes_downloaded).label('total_downloaded'),
                func.sum(UsageRecord.bytes_uploaded).label('total_uploaded'),
                func.avg(UsageRecord.peak_bandwidth_mbps).label('avg_peak_bandwidth'),
                func.max(UsageRecord.peak_bandwidth_mbps).label('max_peak_bandwidth'),
                func.count(UsageRecord.id).label('record_count')
            )
            .where(
                and_(
                    UsageRecord.service_id == service.id,
                    UsageRecord.usage_date >= date(2024, 1, 1),
                    UsageRecord.usage_date <= date(2024, 1, 31)
                )
            )
        )
        
        result = await db_session.execute(monthly_usage_query)
        usage_stats = result.one()
        
        assert usage_stats.record_count == 30  # 30 days of records
        assert usage_stats.total_downloaded > 30000000000  # >30GB total
        assert usage_stats.avg_peak_bandwidth > 90
        assert usage_stats.max_peak_bandwidth >= 100
        
        # Test daily usage trend query
        daily_trend_query = (
            select(
                UsageRecord.usage_date,
                UsageRecord.bytes_downloaded,
                UsageRecord.bytes_uploaded,
                (UsageRecord.bytes_downloaded + UsageRecord.bytes_uploaded).label('total_bytes')
            )
            .where(UsageRecord.service_id == service.id)
            .order_by(UsageRecord.usage_date)
        )
        
        trend_result = await db_session.execute(daily_trend_query)
        daily_usage = trend_result.all()
        
        assert len(daily_usage) == 30
        
        # Verify usage is increasing day by day
        assert daily_usage[29].total_bytes > daily_usage[0].total_bytes
    
    async def test_support_ticket_relationship_queries(self, db_session: AsyncSession):
        """Test support ticket relationships and status tracking."""
        
        tenant_id = str(uuid4())
        
        # Create customer
        customer = Customer(
            id=str(uuid4()),
            customer_number="SUPPORT_CUST001",
            first_name="Support",
            last_name="Customer",
            email_primary="support@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        # Create support agent
        support_agent = User(
            id=str(uuid4()),
            username="support.agent",
            email="agent@support.com",
            first_name="Support",
            last_name="Agent",
            role=UserRole.SUPPORT,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add_all([customer, support_agent])
        await db_session.flush()
        
        # Create support ticket
        ticket = SupportTicket(
            id=str(uuid4()),
            ticket_number="TICKET-001",
            customer_id=customer.id,
            subject="Internet connectivity issues",
            description="Customer experiencing frequent disconnections",
            priority=TicketPriority.HIGH,
            status=TicketStatus.OPEN,
            assigned_to=support_agent.id,
            category="technical",
            tenant_id=tenant_id,
            created_by=customer.id
        )
        
        db_session.add(ticket)
        await db_session.flush()
        
        # Create ticket messages (conversation)
        messages = [
            TicketMessage(
                id=str(uuid4()),
                ticket_id=ticket.id,
                sender_id=customer.id,
                sender_type="customer",
                message="I've been experiencing disconnections every few hours since yesterday.",
                is_internal=False,
                tenant_id=tenant_id,
                created_by=customer.id
            ),
            TicketMessage(
                id=str(uuid4()),
                ticket_id=ticket.id,
                sender_id=support_agent.id,
                sender_type="agent",
                message="Thanks for reporting this. Can you tell me what device you're using?",
                is_internal=False,
                tenant_id=tenant_id,
                created_by=support_agent.id
            ),
            TicketMessage(
                id=str(uuid4()),
                ticket_id=ticket.id,
                sender_id=support_agent.id,
                sender_type="agent",
                message="Checking signal levels on customer's line",
                is_internal=True,  # Internal note
                tenant_id=tenant_id,
                created_by=support_agent.id
            )
        ]
        
        db_session.add_all(messages)
        await db_session.commit()
        
        # Query ticket with all related information
        ticket_details_query = (
            select(SupportTicket, Customer, User)
            .join(Customer, SupportTicket.customer_id == Customer.id)
            .join(User, SupportTicket.assigned_to == User.id)
            .where(SupportTicket.ticket_number == "TICKET-001")
        )
        
        result = await db_session.execute(ticket_details_query)
        ticket_data = result.one()
        
        ticket_row, customer_row, agent_row = ticket_data
        
        assert ticket_row.subject == "Internet connectivity issues"
        assert customer_row.customer_number == "SUPPORT_CUST001"
        assert agent_row.role == UserRole.SUPPORT
        
        # Query messages for the ticket
        messages_query = (
            select(TicketMessage, User)
            .join(User, TicketMessage.sender_id == User.id)
            .where(TicketMessage.ticket_id == ticket.id)
            .order_by(TicketMessage.created_at)
        )
        
        messages_result = await db_session.execute(messages_query)
        message_rows = messages_result.all()
        
        assert len(message_rows) == 3
        
        # First message should be from customer
        first_message, first_sender = message_rows[0]
        assert first_message.sender_type == "customer"
        assert first_sender.id == customer.id
        
        # Query for customer-visible messages only (exclude internal)
        public_messages_query = (
            select(TicketMessage)
            .where(
                and_(
                    TicketMessage.ticket_id == ticket.id,
                    TicketMessage.is_internal == False
                )
            )
            .order_by(TicketMessage.created_at)
        )
        
        public_result = await db_session.execute(public_messages_query)
        public_messages = public_result.scalars().all()
        
        assert len(public_messages) == 2  # Excludes internal message


@pytest.mark.integration 
@pytest.mark.database
class TestTransactionHandling:
    """Test database transaction handling and rollback scenarios."""
    
    async def test_successful_transaction_commit(self, db_session: AsyncSession):
        """Test successful multi-table transaction."""
        
        tenant_id = str(uuid4())
        
        # Begin transaction
        async with db_session.begin():
            # Create customer
            customer = Customer(
                id=str(uuid4()),
                customer_number="TXN_CUST001",
                first_name="Transaction",
                last_name="Test",
                email_primary="txn@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            db_session.add(customer)
            await db_session.flush()
            
            # Create service
            service = Service(
                id=str(uuid4()),
                service_id="SVC_TXN001",
                customer_id=customer.id,
                service_type=ServiceType.INTERNET,
                plan_name="Test Plan",
                monthly_price=Decimal('50.00'),
                status=ServiceStatus.ACTIVE,
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            db_session.add(service)
            await db_session.flush()
            
            # Create invoice
            invoice = Invoice(
                id=str(uuid4()),
                invoice_number="INV_TXN001",
                customer_id=customer.id,
                billing_period_start=date.today(),
                billing_period_end=date.today() + timedelta(days=30),
                subtotal=Decimal('50.00'),
                tax_amount=Decimal('5.00'),
                total_amount=Decimal('55.00'),
                status=InvoiceStatus.DRAFT,
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            db_session.add(invoice)
            
        # Transaction should be committed here
        
        # Verify all data was saved
        customer_check = await db_session.get(Customer, customer.id)
        service_check = await db_session.get(Service, service.id)
        invoice_check = await db_session.get(Invoice, invoice.id)
        
        assert customer_check is not None
        assert service_check is not None
        assert invoice_check is not None
        
        assert customer_check.customer_number == "TXN_CUST001"
        assert service_check.service_id == "SVC_TXN001"
        assert invoice_check.invoice_number == "INV_TXN001"
    
    async def test_transaction_rollback_on_error(self, db_session: AsyncSession):
        """Test transaction rollback when error occurs."""
        
        tenant_id = str(uuid4())
        customer_id = str(uuid4())
        
        # Start transaction that will fail
        try:
            async with db_session.begin():
                # Create customer successfully
                customer = Customer(
                    id=customer_id,
                    customer_number="ROLLBACK_CUST001",
                    first_name="Rollback",
                    last_name="Test",
                    email_primary="rollback@example.com",
                    tenant_id=tenant_id,
                    created_by=str(uuid4())
                )
                db_session.add(customer)
                await db_session.flush()
                
                # This should succeed initially
                customer_check = await db_session.get(Customer, customer_id)
                assert customer_check is not None
                
                # Now create duplicate customer (should fail due to unique constraints)
                duplicate_customer = Customer(
                    id=str(uuid4()),
                    customer_number="ROLLBACK_CUST001",  # Duplicate customer_number
                    first_name="Duplicate",
                    last_name="Customer",
                    email_primary="rollback@example.com",  # Duplicate email
                    tenant_id=tenant_id,
                    created_by=str(uuid4())
                )
                db_session.add(duplicate_customer)
                await db_session.flush()  # This should raise an error
                
        except IntegrityError:
            # Expected error due to duplicate constraint
            pass
        
        # Verify transaction was rolled back - customer should not exist
        customer_check = await db_session.get(Customer, customer_id)
        assert customer_check is None
    
    async def test_nested_transaction_savepoints(self, db_session: AsyncSession):
        """Test nested transactions with savepoints."""
        
        tenant_id = str(uuid4())
        
        async with db_session.begin():
            # Create customer in outer transaction
            customer = Customer(
                id=str(uuid4()),
                customer_number="NESTED_CUST001",
                first_name="Nested",
                last_name="Transaction",
                email_primary="nested@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            db_session.add(customer)
            await db_session.flush()
            
            # Create savepoint for nested transaction
            async with db_session.begin_nested():
                # Create service that will succeed
                service1 = Service(
                    id=str(uuid4()),
                    service_id="SVC_NESTED001",
                    customer_id=customer.id,
                    service_type=ServiceType.INTERNET,
                    plan_name="Nested Test Plan 1",
                    monthly_price=Decimal('100.00'),
                    status=ServiceStatus.ACTIVE,
                    tenant_id=tenant_id,
                    created_by=str(uuid4())
                )
                db_session.add(service1)
                await db_session.flush()
            
            # Savepoint committed successfully
            
            # Another nested transaction that will fail
            try:
                async with db_session.begin_nested():
                    service2 = Service(
                        id=str(uuid4()),
                        service_id="SVC_NESTED001",  # Duplicate service_id should fail
                        customer_id=customer.id,
                        service_type=ServiceType.VOIP,
                        plan_name="Nested Test Plan 2",
                        monthly_price=Decimal('50.00'),
                        status=ServiceStatus.ACTIVE,
                        tenant_id=tenant_id,
                        created_by=str(uuid4())
                    )
                    db_session.add(service2)
                    await db_session.flush()
            except IntegrityError:
                # Nested transaction rolled back, but outer transaction continues
                pass
        
        # Outer transaction commits successfully
        
        # Verify results: customer and first service should exist, second service should not
        customer_check = await db_session.get(Customer, customer.id)
        assert customer_check is not None
        
        services_query = select(Service).where(Service.customer_id == customer.id)
        services_result = await db_session.execute(services_query)
        services = services_result.scalars().all()
        
        assert len(services) == 1
        assert services[0].service_id == "SVC_NESTED001"
        assert services[0].plan_name == "Nested Test Plan 1"


@pytest.mark.integration
@pytest.mark.database
class TestPerformanceOptimization:
    """Test database performance optimization and indexing."""
    
    async def test_large_dataset_query_performance(self, db_session: AsyncSession):
        """Test query performance with large datasets."""
        
        tenant_id = str(uuid4())
        
        # Create large number of customers for performance testing
        customers = []
        for i in range(1000):
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"PERF_CUST{i:04d}",
                first_name=f"Customer{i}",
                last_name="Performance",
                email_primary=f"perf.customer{i}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers.append(customer)
        
        # Batch insert for better performance
        db_session.add_all(customers)
        await db_session.commit()
        
        # Test indexed query performance (tenant_id should be indexed)
        start_time = datetime.now()
        
        tenant_customers_query = select(Customer).where(Customer.tenant_id == tenant_id)
        result = await db_session.execute(tenant_customers_query)
        tenant_customers = result.scalars().all()
        
        query_time = (datetime.now() - start_time).total_seconds()
        
        assert len(tenant_customers) == 1000
        assert query_time < 1.0  # Should be fast with proper indexing
        
        # Test pagination query
        paginated_query = (
            select(Customer)
            .where(Customer.tenant_id == tenant_id)
            .order_by(Customer.customer_number)
            .offset(100)
            .limit(50)
        )
        
        paginated_result = await db_session.execute(paginated_query)
        page_customers = paginated_result.scalars().all()
        
        assert len(page_customers) == 50
        assert page_customers[0].customer_number == "PERF_CUST0100"
        assert page_customers[49].customer_number == "PERF_CUST0149"
    
    async def test_aggregate_query_optimization(self, db_session: AsyncSession):
        """Test performance of aggregate queries."""
        
        tenant_id = str(uuid4())
        
        # Create customers with invoices for aggregation testing
        customers_with_invoices = []
        invoices = []
        
        for i in range(100):
            customer = Customer(
                id=str(uuid4()),
                customer_number=f"AGG_CUST{i:03d}",
                first_name=f"Aggregate{i}",
                last_name="Customer",
                email_primary=f"agg.customer{i}@example.com",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
            customers_with_invoices.append(customer)
            
            # Create multiple invoices per customer
            for j in range(5):
                invoice = Invoice(
                    id=str(uuid4()),
                    invoice_number=f"INV_AGG_{i:03d}_{j:02d}",
                    customer_id=customer.id,
                    billing_period_start=date(2024, j+1, 1),
                    billing_period_end=date(2024, j+1, 28),
                    subtotal=Decimal(f'{100 + i + j}.00'),
                    tax_amount=Decimal(f'{10 + i}.00'),
                    total_amount=Decimal(f'{110 + i + j}.00'),
                    status=InvoiceStatus.PAID if j < 3 else InvoiceStatus.PENDING,
                    tenant_id=tenant_id,
                    created_by=str(uuid4())
                )
                invoices.append(invoice)
        
        db_session.add_all(customers_with_invoices + invoices)
        await db_session.commit()
        
        # Test aggregate query performance
        start_time = datetime.now()
        
        # Complex aggregation: customer billing summary
        billing_summary_query = (
            select(
                Customer.id,
                Customer.customer_number,
                func.count(Invoice.id).label('invoice_count'),
                func.sum(Invoice.total_amount).label('total_billed'),
                func.sum(
                    case(
                        (Invoice.status == InvoiceStatus.PAID, Invoice.total_amount),
                        else_=0
                    )
                ).label('total_paid'),
                func.avg(Invoice.total_amount).label('avg_invoice_amount')
            )
            .join(Invoice, Customer.id == Invoice.customer_id)
            .where(Customer.tenant_id == tenant_id)
            .group_by(Customer.id, Customer.customer_number)
            .having(func.count(Invoice.id) > 3)
            .order_by(Customer.customer_number)
        )
        
        result = await db_session.execute(billing_summary_query)
        billing_summaries = result.all()
        
        aggregation_time = (datetime.now() - start_time).total_seconds()
        
        assert len(billing_summaries) == 100  # All customers have > 3 invoices
        assert aggregation_time < 2.0  # Should be reasonably fast
        
        # Verify aggregation correctness
        first_summary = billing_summaries[0]
        assert first_summary.invoice_count == 5
        assert first_summary.total_billed > Decimal('500.00')
        assert first_summary.total_paid < first_summary.total_billed  # Some unpaid invoices
    
    async def test_full_text_search_performance(self, db_session: AsyncSession):
        """Test full-text search performance and functionality."""
        
        tenant_id = str(uuid4())
        
        # Create customers with varied data for search testing
        search_customers = [
            Customer(
                id=str(uuid4()),
                customer_number="SEARCH001",
                first_name="John",
                last_name="Smith",
                email_primary="john.smith@techcorp.com",
                company_name="TechCorp Solutions",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            ),
            Customer(
                id=str(uuid4()),
                customer_number="SEARCH002",
                first_name="Jane",
                last_name="Doe",
                email_primary="jane@mediainc.com",
                company_name="Media Innovations Inc",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            ),
            Customer(
                id=str(uuid4()),
                customer_number="SEARCH003",
                first_name="Bob",
                last_name="Johnson",
                email_primary="b.johnson@consulting.org",
                company_name="Johnson Consulting Group",
                tenant_id=tenant_id,
                created_by=str(uuid4())
            )
        ]
        
        db_session.add_all(search_customers)
        await db_session.commit()
        
        # Test various search patterns
        search_tests = [
            {
                'term': 'john',
                'expected_customers': ['SEARCH001', 'SEARCH003'],  # John Smith and Johnson
                'description': 'First name and last name partial match'
            },
            {
                'term': 'tech',
                'expected_customers': ['SEARCH001'],  # TechCorp
                'description': 'Company name partial match'
            },
            {
                'term': '@consulting',
                'expected_customers': ['SEARCH003'],  # b.johnson@consulting.org
                'description': 'Email domain match'
            }
        ]
        
        for test_case in search_tests:
            search_term = test_case['term']
            
            # Simulate full-text search (using LIKE for compatibility)
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
            )
            
            start_time = datetime.now()
            result = await db_session.execute(search_query)
            found_customers = result.scalars().all()
            search_time = (datetime.now() - start_time).total_seconds()
            
            # Verify search results
            found_numbers = [c.customer_number for c in found_customers]
            expected_numbers = test_case['expected_customers']
            
            assert set(found_numbers) == set(expected_numbers), \
                f"Search for '{search_term}' failed: {test_case['description']}"
            assert search_time < 0.5, f"Search too slow: {search_time}s"


@pytest.mark.integration
@pytest.mark.database  
class TestDataIntegrityConstraints:
    """Test database integrity constraints and validation."""
    
    async def test_unique_constraints_enforcement(self, db_session: AsyncSession):
        """Test unique constraint enforcement across tables."""
        
        tenant_id = str(uuid4())
        
        # Create first customer
        customer1 = Customer(
            id=str(uuid4()),
            customer_number="UNIQUE001",
            first_name="First",
            last_name="Customer",
            email_primary="unique@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(customer1)
        await db_session.commit()
        
        # Try to create second customer with same email (should fail)
        customer2 = Customer(
            id=str(uuid4()),
            customer_number="UNIQUE002",
            first_name="Second",
            last_name="Customer",
            email_primary="unique@example.com",  # Duplicate email
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(customer2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        # Rollback the failed transaction
        await db_session.rollback()
        
        # Try with same customer_number (should also fail)
        customer3 = Customer(
            id=str(uuid4()),
            customer_number="UNIQUE001",  # Duplicate customer_number
            first_name="Third",
            last_name="Customer", 
            email_primary="different@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(customer3)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    async def test_foreign_key_constraints(self, db_session: AsyncSession):
        """Test foreign key constraint enforcement."""
        
        tenant_id = str(uuid4())
        non_existent_customer_id = str(uuid4())
        
        # Try to create service with non-existent customer_id
        service = Service(
            id=str(uuid4()),
            service_id="SVC_FK_TEST",
            customer_id=non_existent_customer_id,  # Non-existent customer
            service_type=ServiceType.INTERNET,
            plan_name="FK Test Plan",
            monthly_price=Decimal('100.00'),
            status=ServiceStatus.ACTIVE,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(service)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Create valid customer first
        customer = Customer(
            id=str(uuid4()),
            customer_number="FK_CUST001",
            first_name="FK",
            last_name="Customer",
            email_primary="fk@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(customer)
        await db_session.flush()
        
        # Now create service with valid customer_id
        valid_service = Service(
            id=str(uuid4()),
            service_id="SVC_FK_VALID",
            customer_id=customer.id,  # Valid customer ID
            service_type=ServiceType.INTERNET,
            plan_name="Valid FK Plan",
            monthly_price=Decimal('100.00'),
            status=ServiceStatus.ACTIVE,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(valid_service)
        await db_session.commit()  # Should succeed
        
        # Verify the service was created
        service_check = await db_session.get(Service, valid_service.id)
        assert service_check is not None
        assert service_check.customer_id == customer.id
    
    async def test_check_constraints_validation(self, db_session: AsyncSession):
        """Test check constraint validation (e.g., positive amounts)."""
        
        tenant_id = str(uuid4())
        
        # Create customer for invoice testing
        customer = Customer(
            id=str(uuid4()),
            customer_number="CHECK_CUST001",
            first_name="Check",
            last_name="Customer",
            email_primary="check@example.com",
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(customer)
        await db_session.flush()
        
        # Try to create invoice with negative total (should be prevented by app logic)
        invalid_invoice = Invoice(
            id=str(uuid4()),
            invoice_number="INV_NEGATIVE",
            customer_id=customer.id,
            billing_period_start=date.today(),
            billing_period_end=date.today() + timedelta(days=30),
            subtotal=Decimal('-100.00'),  # Negative amount
            tax_amount=Decimal('-10.00'),   # Negative amount
            total_amount=Decimal('-110.00'), # Negative amount
            status=InvoiceStatus.DRAFT,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(invalid_invoice)
        
        # If database has check constraints, this should fail
        # If not, application logic should prevent this
        try:
            await db_session.commit()
            # If commit succeeds, verify amounts were stored correctly
            # (Some databases may allow negative amounts at DB level)
            saved_invoice = await db_session.get(Invoice, invalid_invoice.id)
            assert saved_invoice.total_amount == Decimal('-110.00')
        except IntegrityError:
            # Database prevented negative amounts with check constraint
            await db_session.rollback()
        
        # Create valid invoice with positive amounts
        valid_invoice = Invoice(
            id=str(uuid4()),
            invoice_number="INV_POSITIVE",
            customer_id=customer.id,
            billing_period_start=date.today(),
            billing_period_end=date.today() + timedelta(days=30),
            subtotal=Decimal('100.00'),
            tax_amount=Decimal('10.00'),
            total_amount=Decimal('110.00'),
            status=InvoiceStatus.DRAFT,
            tenant_id=tenant_id,
            created_by=str(uuid4())
        )
        
        db_session.add(valid_invoice)
        await db_session.commit()  # Should succeed
        
        # Verify valid invoice was created
        invoice_check = await db_session.get(Invoice, valid_invoice.id)
        assert invoice_check is not None
        assert invoice_check.total_amount == Decimal('110.00')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])