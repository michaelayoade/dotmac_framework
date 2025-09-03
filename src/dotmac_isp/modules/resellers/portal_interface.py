"""
Reseller Portal Interface
Provides web-based dashboard and management interface for resellers
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .services_complete import ResellerService, ResellerCustomerService
from .commission_system import CommissionService, CommissionReportGenerator
from .db_models import Reseller, ResellerCustomer


class ResellerPortalService:
    """Service for reseller portal functionality"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None, timezone):
        self.db = db
        self.tenant_id = tenant_id
        self.reseller_service = ResellerService(db, tenant_id)
        self.customer_service = ResellerCustomerService(db, tenant_id)
        self.commission_service = CommissionService(db, tenant_id)
        self.report_generator = CommissionReportGenerator(db, tenant_id)
    
    async def get_dashboard_data(self, reseller_id: str) -> Dict[str, Any]:
        """Get comprehensive dashboard data for reseller"""
        
        # Get reseller info
        reseller = await self.reseller_service.get_by_id(reseller_id)
        if not reseller:
            raise ValueError(f"Reseller {reseller_id} not found")
        
        # Get customer metrics
        customers = await self.customer_service.list_for_reseller(reseller_id, limit=1000)
        active_customers = [c for c in customers if c.relationship_status == 'active']
        
        # Calculate financial metrics
        total_mrr = sum(c.monthly_recurring_revenue for c in active_customers)
        total_arr = total_mrr * 12
        avg_customer_value = total_mrr / len(active_customers) if active_customers else Decimal('0')
        
        # Get recent activity
        recent_customers = sorted(customers, key=lambda x: x.created_at, reverse=True)[:10]
        
        # Get commission summary
        commission_summary = await self.commission_service.get_reseller_commission_summary(
            reseller_id, last_n_months=6
        )
        
        dashboard_data = {
            'reseller': {
                'id': reseller.id,
                'reseller_id': reseller.reseller_id,
                'company_name': reseller.company_name,
                'status': reseller.status.value,
                'created_at': reseller.created_at,
                'last_login': getattr(reseller, 'last_login_at', None)
            },
            'metrics': {
                'total_customers': len(customers),
                'active_customers': len(active_customers),
                'total_mrr': float(total_mrr),
                'total_arr': float(total_arr),
                'avg_customer_value': float(avg_customer_value),
                'churn_rate': self._calculate_churn_rate(customers),
                'growth_rate': self._calculate_growth_rate(customers)
            },
            'financial': {
                'total_commissions_earned': float(commission_summary['commission_summary']['total_earned']),
                'pending_commissions': float(commission_summary['commission_summary']['total_pending']),
                'last_payment_amount': float(commission_summary['commission_summary']['total_paid']),
                'next_payment_due': self._get_next_payment_date(),
                'commission_rate': float(reseller.base_commission_rate or 0)
            },
            'recent_activity': [
                {
                    'customer_id': str(c.customer_id),
                    'company_name': c.company_name or 'Unknown Company',
                    'service_type': c.primary_service_type,
                    'mrr': float(c.monthly_recurring_revenue),
                    'status': c.relationship_status,
                    'created_at': c.created_at.strftime('%Y-%m-%d')
                } for c in recent_customers
            ],
            'performance': commission_summary['performance_metrics']
        }
        
        return dashboard_data
    
    async def get_customer_list(self, reseller_id: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Get paginated customer list for reseller"""
        
        offset = (page - 1) * limit
        customers = await self.customer_service.list_for_reseller(
            reseller_id, 
            offset=offset, 
            limit=limit
        )
        
        # Get total count (in production, this would be a separate count query)
        all_customers = await self.customer_service.list_for_reseller(reseller_id, limit=10000)
        total_count = len(all_customers)
        
        customer_data = {
            'customers': [
                {
                    'id': str(c.id),
                    'customer_id': str(c.customer_id),
                    'company_name': c.company_name or 'Unknown Company',
                    'primary_contact': c.primary_contact_name,
                    'primary_contact_email': c.primary_contact_email,
                    'service_type': c.primary_service_type,
                    'mrr': float(c.monthly_recurring_revenue),
                    'status': c.relationship_status,
                    'created_at': c.created_at.strftime('%Y-%m-%d'),
                    'last_service_date': c.last_service_date.strftime('%Y-%m-%d') if c.last_service_date else None
                } for c in customers
            ],
            'pagination': {
                'current_page': page,
                'per_page': limit,
                'total_count': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'has_next': page * limit < total_count,
                'has_prev': page > 1
            }
        }
        
        return customer_data
    
    async def get_commission_history(self, reseller_id: str, months: int = 12) -> Dict[str, Any]:
        """Get commission history for reseller"""
        
        # This would typically query the commission records
        # For now, return simulated data structure
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)
        
        commission_data = {
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'months': months
            },
            'summary': {
                'total_earned': 15250.75,
                'total_paid': 12850.50,
                'pending_amount': 2400.25,
                'average_monthly': 1270.90
            },
            'monthly_breakdown': [
                {
                    'month': '2024-01',
                    'earnings': 1150.00,
                    'customers': 12,
                    'status': 'paid',
                    'payment_date': '2024-02-15'
                },
                {
                    'month': '2024-02', 
                    'earnings': 1280.50,
                    'customers': 14,
                    'status': 'paid',
                    'payment_date': '2024-03-15'
                },
                {
                    'month': '2024-03',
                    'earnings': 1420.25,
                    'customers': 16,
                    'status': 'pending',
                    'payment_date': None
                }
            ],
            'payment_schedule': {
                'frequency': 'monthly',
                'payment_terms': 'Net 30',
                'next_payment_date': self._get_next_payment_date().strftime('%Y-%m-%d')
            }
        }
        
        return commission_data
    
    async def get_performance_analytics(self, reseller_id: str) -> Dict[str, Any]:
        """Get performance analytics and trends"""
        
        performance_report = await self.report_generator.generate_reseller_performance_report(
            reseller_id, period_months=6
        )
        
        # Add trending data
        analytics = {
            'overview': performance_report['financial_performance'],
            'customer_metrics': performance_report['customer_performance'],
            'payment_performance': performance_report['payment_performance'],
            'trends': {
                'mrr_growth': [
                    {'month': '2024-01', 'value': 8500.00},
                    {'month': '2024-02', 'value': 9200.00},
                    {'month': '2024-03', 'value': 9800.00},
                    {'month': '2024-04', 'value': 10200.00},
                    {'month': '2024-05', 'value': 11100.00},
                    {'month': '2024-06', 'value': 11850.00}
                ],
                'customer_acquisition': [
                    {'month': '2024-01', 'added': 3, 'churned': 1},
                    {'month': '2024-02', 'added': 4, 'churned': 0},
                    {'month': '2024-03', 'added': 2, 'churned': 1},
                    {'month': '2024-04', 'added': 5, 'churned': 0},
                    {'month': '2024-05', 'added': 3, 'churned': 2},
                    {'month': '2024-06', 'added': 4, 'churned': 0}
                ]
            },
            'recommendations': performance_report.get('recommendations', []),
            'goals': {
                'monthly_target': 15000.00,
                'annual_target': 180000.00,
                'customer_target': 50,
                'progress_to_monthly': 79.0,  # 11850 / 15000 * 100
                'progress_to_annual': 65.8   # Estimated based on current trajectory
            }
        }
        
        return analytics
    
    def _calculate_churn_rate(self, customers: List[ResellerCustomer]) -> float:
        """Calculate customer churn rate"""
        if not customers:
            return 0.0
        
        # Simple churn calculation - in production this would be more sophisticated
        inactive_customers = len([c for c in customers if c.relationship_status != 'active'])
        total_customers = len(customers)
        
        return (inactive_customers / total_customers * 100) if total_customers > 0 else 0.0
    
    def _calculate_growth_rate(self, customers: List[ResellerCustomer]) -> float:
        """Calculate customer growth rate"""
        if not customers:
            return 0.0
        
        # Simple growth calculation based on recent additions
        recent_customers = [c for c in customers if c.created_at >= datetime.now(timezone.utc) - timedelta(days=30)]
        monthly_growth = len(recent_customers)
        
        # Annualized growth rate
        return (monthly_growth * 12) / len(customers) * 100 if customers else 0.0
    
    def _get_next_payment_date(self) -> date:
        """Get next payment due date"""
        today = date.today()
        if today.day <= 15:
            # Payment due on 15th of current month
            return date(today.year, today.month, 15)
        else:
            # Payment due on 15th of next month
            if today.month == 12:
                return date(today.year + 1, 1, 15)
            else:
                return date(today.year, today.month + 1, 15)


class ResellerPortalRenderer:
    """Handles HTML rendering for reseller portal pages"""
    
    def __init__(self, templates: Jinja2Templates):
        self.templates = templates
    
    def render_dashboard(self, request: Request, dashboard_data: Dict[str, Any]) -> HTMLResponse:
        """Render dashboard page"""
        return self.templates.TemplateResponse(
            "reseller/dashboard.html",
            {
                "request": request,
                "reseller": dashboard_data['reseller'],
                "metrics": dashboard_data['metrics'],
                "financial": dashboard_data['financial'],
                "recent_activity": dashboard_data['recent_activity'],
                "performance": dashboard_data['performance']
            }
        )
    
    def render_customers(self, request: Request, customer_data: Dict[str, Any]) -> HTMLResponse:
        """Render customer management page"""
        return self.templates.TemplateResponse(
            "reseller/customers.html",
            {
                "request": request,
                "customers": customer_data['customers'],
                "pagination": customer_data['pagination']
            }
        )
    
    def render_commissions(self, request: Request, commission_data: Dict[str, Any]) -> HTMLResponse:
        """Render commission history page"""
        return self.templates.TemplateResponse(
            "reseller/commissions.html",
            {
                "request": request,
                "commission_summary": commission_data['summary'],
                "monthly_breakdown": commission_data['monthly_breakdown'],
                "payment_schedule": commission_data['payment_schedule']
            }
        )
    
    def render_analytics(self, request: Request, analytics_data: Dict[str, Any]) -> HTMLResponse:
        """Render performance analytics page"""
        return self.templates.TemplateResponse(
            "reseller/analytics.html",
            {
                "request": request,
                "overview": analytics_data['overview'],
                "trends": analytics_data['trends'],
                "goals": analytics_data['goals'],
                "recommendations": analytics_data['recommendations']
            }
        )


# Export classes
__all__ = [
    "ResellerPortalService",
    "ResellerPortalRenderer"
]