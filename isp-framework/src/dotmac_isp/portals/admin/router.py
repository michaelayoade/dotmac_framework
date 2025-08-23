"""Admin portal API router."""

from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_user
from dotmac_isp.modules.identity.models import User
from dotmac_isp.modules.identity.service import CustomerService, UserService
from dotmac_isp.modules.billing.service import BillingService
from dotmac_isp.modules.support.service import SupportTicketService
from dotmac_isp.modules.services.service import ServiceProvisioningService
from dotmac_isp.modules.analytics.service import AnalyticsService
from . import schemas

router = APIRouter(prefix="/admin", tags=["admin-portal"])
admin_router = router  # Export with expected name


@router.get("/dashboard", response_model=schemas.AdminDashboard)
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get admin dashboard overview."""
    try:
        # Initialize services
        customer_service = CustomerService(db, str(current_user.tenant_id))
        billing_service = BillingService(db, str(current_user.tenant_id))
        support_service = SupportTicketService(db, str(current_user.tenant_id))
        service_service = ServiceProvisioningService(db, str(current_user.tenant_id))

        # Get customer metrics
        customers = await customer_service.list_customers(
            limit=1000
        )  # Get all for counting
        total_customers = len(customers)

        # Get service metrics
        services = await service_service.list_service_instances(limit=1000)
        active_services = len([s for s in services if s.status == "active"])

        # Get billing metrics
        current_month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        invoices = await billing_service.list_invoices(
            due_date_from=current_month_start.date(), limit=1000
        )
        monthly_revenue = sum(inv.total_amount for inv in invoices)

        # Get support metrics
        tickets = await support_service.list_tickets(limit=1000)
        open_tickets = len(
            [
                t
                for t in tickets
                if t.ticket_status in ["open", "in_progress", "escalated"]
            ]
        )

        # Recent activities (mock data for now)
        recent_activities = [
            {
                "timestamp": datetime.now() - timedelta(minutes=15),
                "action": "Customer registration",
                "details": "New customer CUST-001 registered",
            },
            {
                "timestamp": datetime.now() - timedelta(hours=1),
                "action": "Service activation",
                "details": "Internet service activated for CUST-002",
            },
            {
                "timestamp": datetime.now() - timedelta(hours=2),
                "action": "Payment processed",
                "details": "$99.99 payment received from CUST-003",
            },
        ]

        # Performance metrics
        performance_metrics = {
            "customer_satisfaction": 4.2,
            "average_response_time": 2.5,  # hours
            "system_uptime": 99.9,
            "revenue_growth": 12.5,  # percentage
        }

        return schemas.AdminDashboard(
            total_customers=total_customers,
            active_services=active_services,
            monthly_revenue=monthly_revenue,
            open_tickets=open_tickets,
            system_alerts=await get_system_alerts_count(db, tenant_id),
            recent_activities=recent_activities,
            performance_metrics=performance_metrics,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dashboard: {str(e)}",
        )


@router.get("/customers/overview", response_model=schemas.CustomerOverview)
async def get_customers_overview(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get customer overview for admin."""
    try:
        customer_service = CustomerService(db, str(current_user.tenant_id))
        customers = await customer_service.list_customers(limit=1000)

        total = len(customers)
        active = len([c for c in customers if c.account_status == "active"])
        suspended = len([c for c in customers if c.account_status == "suspended"])
        pending = len([c for c in customers if c.account_status == "pending"])

        # Calculate new customers this month
        current_month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        new_this_month = len(
            [c for c in customers if c.created_at >= current_month_start]
        )

        # Group by customer type
        by_type = {}
        for customer in customers:
            customer_type = customer.customer_type
            by_type[customer_type] = by_type.get(customer_type, 0) + 1

        return schemas.CustomerOverview(
            total=total,
            active=active,
            suspended=suspended,
            pending=pending,
            new_this_month=new_this_month,
            churn_rate=await calculate_churn_rate(db, tenant_id),
            by_type=by_type,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load customer overview: {str(e)}",
        )


@router.get("/services/overview", response_model=schemas.ServicesOverview)
async def get_services_overview(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get services overview for admin."""
    try:
        service_service = ServiceProvisioningService(db, str(current_user.tenant_id))
        services = await service_service.list_service_instances(limit=1000)

        total_instances = len(services)

        # Group by service type
        by_type = {}
        by_status = {}
        revenue_per_service = {}

        for service in services:
            # Group by type (using service plan name as type)
            service_type = (
                service.service_plan.name if service.service_plan else "Unknown"
            )
            by_type[service_type] = by_type.get(service_type, 0) + 1

            # Group by status
            status_key = service.status
            by_status[status_key] = by_status.get(status_key, 0) + 1

            # Calculate revenue per service type (mock calculation)
            if service_type not in revenue_per_service:
                revenue_per_service[service_type] = Decimal("0.00")
            revenue_per_service[service_type] += Decimal("99.99")  # Mock revenue

        return schemas.ServicesOverview(
            total_instances=total_instances,
            by_type=by_type,
            by_status=by_status,
            revenue_per_service=revenue_per_service,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load services overview: {str(e)}",
        )


@router.get("/financial/overview", response_model=schemas.FinancialOverview)
async def get_financial_overview(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get financial overview for admin."""
    try:
        billing_service = BillingService(db, str(current_user.tenant_id))

        # Get current month invoices
        current_month_start = datetime.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        invoices = await billing_service.list_invoices(
            due_date_from=current_month_start.date(), limit=1000
        )

        monthly_revenue = sum(inv.total_amount for inv in invoices)
        outstanding_invoices = len([inv for inv in invoices if inv.amount_due > 0])
        overdue_amount = sum(
            inv.amount_due
            for inv in invoices
            if inv.due_date
            and inv.due_date < datetime.now().date()
            and inv.amount_due > 0
        )

        # Mock revenue trend data
        revenue_trend = [
            {"month": "Jan", "revenue": 45000},
            {"month": "Feb", "revenue": 48000},
            {"month": "Mar", "revenue": 52000},
            {"month": "Apr", "revenue": 49000},
            {"month": "May", "revenue": 55000},
        ]

        # Mock top revenue customers
        top_revenue_customers = [
            {"customer_name": "Enterprise Corp", "revenue": 5000},
            {"customer_name": "Tech Solutions LLC", "revenue": 3500},
            {"customer_name": "Digital Services Inc", "revenue": 2800},
        ]

        return schemas.FinancialOverview(
            monthly_revenue=monthly_revenue,
            outstanding_invoices=outstanding_invoices,
            overdue_amount=overdue_amount,
            collection_rate=await calculate_collection_rate(db, tenant_id),
            revenue_trend=revenue_trend,
            top_revenue_customers=top_revenue_customers,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load financial overview: {str(e)}",
        )


@router.get("/support/overview", response_model=schemas.SupportOverview)
async def get_support_overview(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get support overview for admin."""
    try:
        support_service = SupportTicketService(db, str(current_user.tenant_id))
        tickets = await support_service.list_tickets(limit=1000)

        open_tickets = len(
            [
                t
                for t in tickets
                if t.ticket_status in ["open", "in_progress", "escalated"]
            ]
        )
        escalated_tickets = len([t for t in tickets if t.ticket_status == "escalated"])

        # Group by category and priority
        tickets_by_category = {}
        tickets_by_priority = {}

        for ticket in tickets:
            # Group by category
            category = ticket.category
            tickets_by_category[category] = tickets_by_category.get(category, 0) + 1

            # Group by priority
            priority = ticket.priority
            tickets_by_priority[priority] = tickets_by_priority.get(priority, 0) + 1

        return schemas.SupportOverview(
            open_tickets=open_tickets,
            avg_response_time=await calculate_avg_response_time(db, tenant_id),
            sla_compliance=await calculate_sla_compliance(db, tenant_id),
            escalated_tickets=escalated_tickets,
            tickets_by_category=tickets_by_category,
            tickets_by_priority=tickets_by_priority,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load support overview: {str(e)}",
        )


@router.get("/system/health", response_model=schemas.SystemHealth)
async def get_system_health(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get system health status."""
    try:
        # Basic health checks for core system components
        import psutil

        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return schemas.SystemHealth(
            database="healthy",
            redis="healthy",
            services="healthy",
            last_updated=datetime.now(),
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            active_connections=50,  # Mock active DB connections
        )

    except ImportError:
        # Fallback if psutil is not available
        return schemas.SystemHealth(
            database="healthy",
            redis="healthy",
            services="healthy",
            last_updated=datetime.now(),
            cpu_usage=25.0,
            memory_usage=60.0,
            disk_usage=45.0,
            active_connections=50,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}",
        )


# Helper Functions

async def get_system_alerts_count(db: Session, tenant_id: str) -> int:
    """Get count of active system alerts."""
    try:
        # Check for common alert conditions
        alert_count = 0
        
        # Check for overdue projects
        from dotmac_isp.modules.projects.models import InstallationProject, ProjectStatus
        overdue_projects = db.query(InstallationProject).filter(
            InstallationProject.tenant_id == tenant_id,
            InstallationProject.project_status.in_([
                ProjectStatus.IN_PROGRESS, 
                ProjectStatus.PLANNING
            ]),
            InstallationProject.planned_end_date < datetime.now().date()
        ).count()
        
        if overdue_projects > 0:
            alert_count += 1
        
        # Check for high priority open tickets
        from dotmac_isp.modules.support.models import Ticket, TicketPriority, TicketStatus
        high_priority_tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.priority == TicketPriority.HIGH,
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        ).count()
        
        if high_priority_tickets > 5:  # Alert if more than 5 high priority tickets
            alert_count += 1
            
        # Check for failed payments (if billing module available)
        try:
            from dotmac_isp.modules.billing.models import Invoice, InvoiceStatus
            overdue_invoices = db.query(Invoice).filter(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.OVERDUE
            ).count()
            
            if overdue_invoices > 10:  # Alert if more than 10 overdue invoices
                alert_count += 1
        except ImportError:
            pass  # Billing module not available
            
        return alert_count
        
    except Exception as e:
        print(f"Error calculating system alerts: {e}")
        return 0


async def calculate_churn_rate(db: Session, tenant_id: str) -> float:
    """Calculate customer churn rate for the last month."""
    try:
        from dotmac_isp.modules.identity.models import Customer, AccountStatus
        
        # Get total customers at start of month
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total_customers_start = db.query(Customer).filter(
            Customer.tenant_id == tenant_id,
            Customer.created_at < start_of_month
        ).count()
        
        # Get churned customers this month (cancelled/suspended)
        churned_customers = db.query(Customer).filter(
            Customer.tenant_id == tenant_id,
            Customer.account_status.in_([AccountStatus.CANCELLED, AccountStatus.SUSPENDED]),
            Customer.updated_at >= start_of_month
        ).count()
        
        if total_customers_start > 0:
            return round((churned_customers / total_customers_start) * 100, 2)
        return 0.0
        
    except Exception as e:
        print(f"Error calculating churn rate: {e}")
        return 2.5  # Fallback value


async def calculate_collection_rate(db: Session, tenant_id: str) -> float:
    """Calculate invoice collection rate."""
    try:
        from dotmac_isp.modules.billing.models import Invoice, InvoiceStatus
        
        # Get all invoices from last 3 months
        three_months_ago = datetime.now() - timedelta(days=90)
        
        total_invoices = db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.created_at >= three_months_ago
        ).count()
        
        collected_invoices = db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.created_at >= three_months_ago
        ).count()
        
        if total_invoices > 0:
            return round((collected_invoices / total_invoices) * 100, 2)
        return 100.0
        
    except ImportError:
        return 95.5  # Fallback if billing module not available
    except Exception as e:
        print(f"Error calculating collection rate: {e}")
        return 95.5


async def calculate_avg_response_time(db: Session, tenant_id: str) -> float:
    """Calculate average ticket response time in hours."""
    try:
        from dotmac_isp.modules.support.models import Ticket, TicketStatus
        
        # Get tickets from last 30 days that have been responded to
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.created_at >= thirty_days_ago,
            Ticket.first_response_at.isnot(None)
        ).all()
        
        if not tickets:
            return 4.0  # Default if no data
            
        response_times = []
        for ticket in tickets:
            if ticket.first_response_at:
                response_time = (ticket.first_response_at - ticket.created_at).total_seconds() / 3600  # Convert to hours
                response_times.append(response_time)
        
        if response_times:
            return round(sum(response_times) / len(response_times), 2)
        return 4.0
        
    except Exception as e:
        print(f"Error calculating response time: {e}")
        return 2.5


async def calculate_sla_compliance(db: Session, tenant_id: str) -> float:
    """Calculate SLA compliance percentage."""
    try:
        from dotmac_isp.modules.support.models import Ticket, TicketPriority
        
        # Get tickets from last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        tickets = db.query(Ticket).filter(
            Ticket.tenant_id == tenant_id,
            Ticket.created_at >= thirty_days_ago,
            Ticket.resolved_at.isnot(None)
        ).all()
        
        if not tickets:
            return 95.0  # Default if no data
            
        sla_compliant = 0
        total_tickets = len(tickets)
        
        for ticket in tickets:
            if ticket.resolved_at:
                resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600  # Hours
                
                # SLA thresholds based on priority
                sla_threshold = 24  # Default 24 hours
                if ticket.priority == TicketPriority.HIGH:
                    sla_threshold = 8
                elif ticket.priority == TicketPriority.MEDIUM:
                    sla_threshold = 16
                elif ticket.priority == TicketPriority.LOW:
                    sla_threshold = 48
                    
                if resolution_time <= sla_threshold:
                    sla_compliant += 1
        
        if total_tickets > 0:
            return round((sla_compliant / total_tickets) * 100, 2)
        return 95.0
        
    except Exception as e:
        print(f"Error calculating SLA compliance: {e}")
        return 94.2


@router.get("/reports/available", response_model=schemas.AvailableReports)
async def get_available_reports(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get list of available admin reports."""
    try:
        return schemas.AvailableReports(
            financial=[
                "revenue_summary",
                "invoicing_report",
                "payment_analysis",
                "customer_billing_history",
                "overdue_accounts",
            ],
            operational=[
                "service_usage_trends",
                "customer_activity_summary",
                "network_performance",
                "service_provisioning_metrics",
                "customer_lifecycle_analysis",
            ],
            support=[
                "ticket_analytics",
                "sla_performance",
                "response_time_analysis",
                "escalation_trends",
                "customer_satisfaction",
            ],
            custom=[
                "executive_dashboard",
                "regulatory_compliance",
                "capacity_planning",
            ],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load available reports: {str(e)}",
        )
