"""
Admin interface for reseller application management
Provides CLI and web interface tools for administrators
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from tabulate import tabulate

from .db_models import ApplicationStatus, ResellerStatus
from .services_complete import ResellerApplicationService, ResellerService


class ResellerAdminCLI:
    """Command-line interface for reseller administration"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.app_service = ResellerApplicationService(db, tenant_id)
        self.reseller_service = ResellerService(db, tenant_id)
    
    async def list_pending_applications(self) -> None:
        """List all pending applications"""
        applications = await self.app_service.get_pending_applications(limit=100)
        
        if not applications:
            print("📋 No pending applications found.")
            return
        
        # Prepare table data
        table_data = []
        for app in applications:
            table_data.append([
                app.application_id,
                app.company_name,
                app.contact_name,
                app.contact_email,
                app.status.value,
                app.submitted_at.strftime('%Y-%m-%d'),
                f"{app.estimated_monthly_customers or 0} customers/month"
            ])
        
        headers = ["Application ID", "Company", "Contact", "Email", "Status", "Submitted", "Est. Volume"]
        print("\n📋 Pending Reseller Applications:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    async def review_application(self, application_id: str, reviewer_id: str) -> None:
        """Review a specific application"""
        try:
            # Get application details
            application = await self.app_service.repo.get_by_id(application_id)
            if not application:
                print(f"❌ Application {application_id} not found.")
                return
            
            # Display application details
            print(f"\n📄 Application Details: {application_id}")
            print("=" * 60)
            print(f"Company: {application.company_name}")
            print(f"Contact: {application.contact_name} ({application.contact_email})")
            print(f"Phone: {application.contact_phone or 'Not provided'}")
            print(f"Business Type: {application.business_type or 'Not specified'}")
            print(f"Years in Business: {application.years_in_business or 'Not specified'}")
            print(f"Employee Count: {application.employee_count or 'Not specified'}")
            print(f"Telecom Experience: {application.telecom_experience_years or 0} years")
            print(f"Estimated Monthly Customers: {application.estimated_monthly_customers or 'Not specified'}")
            print(f"Target Segments: {application.target_customer_segments or 'Not specified'}")
            print(f"Desired Territories: {application.desired_territories or 'Not specified'}")
            print(f"Technical Capabilities: {application.technical_capabilities or 'Not specified'}")
            print(f"Business Description: {application.business_description or 'Not provided'}")
            print(f"Submitted: {application.submitted_at}")
            
            # Mark as under review
            await self.app_service.review_application(
                application_id, 
                reviewer_id, 
                f"Under review by {reviewer_id}"
            )
            
            print(f"\n✅ Application {application_id} marked as under review.")
            
        except Exception as e:
            print(f"❌ Error reviewing application: {e}")
    
    async def approve_application(
        self, 
        application_id: str, 
        reviewer_id: str,
        commission_rate: Optional[float] = None,
        notes: Optional[str] = None
    ) -> None:
        """Approve an application"""
        try:
            approval_data = {}
            if commission_rate:
                approval_data['base_commission_rate'] = commission_rate
            if notes:
                approval_data['notes'] = notes
            
            result = await self.app_service.approve_application(
                application_id, reviewer_id, approval_data
            )
            
            print(f"\n✅ Application {application_id} approved successfully!")
            print(f"   Reseller ID: {result['reseller'].reseller_id}")
            print(f"   Company: {result['reseller'].company_name}")
            print(f"   Status: {result['reseller'].status.value}")
            print(f"   Commission Rate: {result['reseller'].commission_rate_display}")
            
        except Exception as e:
            print(f"❌ Error approving application: {e}")
    
    async def reject_application(
        self, 
        application_id: str, 
        reviewer_id: str,
        reason: str
    ) -> None:
        """Reject an application"""
        try:
            application = await self.app_service.reject_application(
                application_id, reviewer_id, reason
            )
            
            print(f"\n❌ Application {application_id} rejected.")
            print(f"   Reason: {reason}")
            print(f"   Notification sent to: {application.contact_email}")
            
        except Exception as e:
            print(f"❌ Error rejecting application: {e}")
    
    async def list_active_resellers(self) -> None:
        """List all active resellers"""
        resellers = await self.reseller_service.list_active_resellers(limit=100)
        
        if not resellers:
            print("📋 No active resellers found.")
            return
        
        # Prepare table data
        table_data = []
        for reseller in resellers:
            table_data.append([
                reseller.reseller_id,
                reseller.company_name,
                reseller.status.value,
                reseller.total_customers,
                reseller.active_customers,
                f"${float(reseller.monthly_sales or 0):,.2f}",
                reseller.commission_rate_display,
                reseller.created_at.strftime('%Y-%m-%d')
            ])
        
        headers = ["Reseller ID", "Company", "Status", "Total", "Active", "Monthly Sales", "Commission", "Created"]
        print("\n📋 Active Resellers:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    async def get_reseller_dashboard(self, reseller_id: str) -> None:
        """Show reseller dashboard information"""
        try:
            dashboard = await self.reseller_service.get_dashboard_data(reseller_id)
            if not dashboard:
                print(f"❌ Reseller {reseller_id} not found.")
                return
            
            reseller_info = dashboard['reseller']
            print(f"\n📊 Reseller Dashboard: {reseller_id}")
            print("=" * 60)
            print(f"Company: {reseller_info['company_name']}")
            print(f"Status: {reseller_info['status']}")
            print(f"Total Customers: {reseller_info['total_customers']}")
            print(f"Active Customers: {reseller_info['active_customers']}")
            print(f"Monthly Sales: ${reseller_info['monthly_sales']:,.2f}")
            print(f"YTD Sales: ${reseller_info['ytd_sales']:,.2f}")
            print(f"Lifetime Sales: ${reseller_info['lifetime_sales']:,.2f}")
            print(f"Recent Customers: {dashboard['recent_customers']}")
            print(f"Active Opportunities: {dashboard['active_opportunities']}")
            print(f"Pending Commissions: {dashboard['pending_commissions']}")
            print(f"Commission Total: ${dashboard['commission_total_pending']:,.2f}")
            
        except Exception as e:
            print(f"❌ Error retrieving dashboard: {e}")


class ResellerAdminActions:
    """Administrative actions for reseller management"""
    
    @staticmethod
    async def bulk_approve_applications(
        db: AsyncSession,
        application_ids: List[str],
        reviewer_id: str,
        default_commission_rate: float = 10.0
    ) -> Dict[str, str]:
        """Bulk approve multiple applications"""
        service = ResellerApplicationService(db)
        results = {}
        
        for app_id in application_ids:
            try:
                await service.approve_application(
                    app_id, 
                    reviewer_id, 
                    {'base_commission_rate': default_commission_rate}
                )
                results[app_id] = "approved"
            except Exception as e:
                results[app_id] = f"failed: {str(e)}"
        
        return results
    
    @staticmethod
    async def generate_monthly_report(
        db: AsyncSession,
        tenant_id: Optional[str] = None
    ) -> Dict[str, any]:
        """Generate monthly reseller performance report"""
        app_service = ResellerApplicationService(db, tenant_id)
        reseller_service = ResellerService(db, tenant_id)
        
        # Get applications this month
        applications = await app_service.get_pending_applications(limit=1000)
        
        # Get active resellers
        resellers = await reseller_service.list_active_resellers(limit=1000)
        
        # Calculate metrics
        total_applications = len(applications)
        pending_applications = len([a for a in applications if a.status == ApplicationStatus.SUBMITTED])
        
        total_resellers = len(resellers)
        total_customers = sum(r.total_customers for r in resellers)
        total_monthly_sales = sum(float(r.monthly_sales or 0) for r in resellers)
        
        report = {
            'report_date': datetime.utcnow(),
            'applications': {
                'total': total_applications,
                'pending': pending_applications,
                'approved_this_month': len([a for a in applications if a.status == ApplicationStatus.APPROVED])
            },
            'resellers': {
                'total_active': total_resellers,
                'total_customers': total_customers,
                'total_monthly_sales': total_monthly_sales,
                'average_customers_per_reseller': total_customers / total_resellers if total_resellers > 0 else 0
            }
        }
        
        return report
    
    @staticmethod
    async def export_reseller_data(
        db: AsyncSession,
        tenant_id: Optional[str] = None,
        format: str = "csv"
    ) -> str:
        """Export reseller data for analysis"""
        reseller_service = ResellerService(db, tenant_id)
        resellers = await reseller_service.list_active_resellers(limit=10000)
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow([
                'Reseller ID', 'Company Name', 'Status', 'Contact Email',
                'Total Customers', 'Active Customers', 'Monthly Sales',
                'YTD Sales', 'Lifetime Sales', 'Commission Rate', 'Created Date'
            ])
            
            # Data rows
            for r in resellers:
                writer.writerow([
                    r.reseller_id, r.company_name, r.status.value, r.primary_contact_email,
                    r.total_customers, r.active_customers, float(r.monthly_sales or 0),
                    float(r.ytd_sales or 0), float(r.lifetime_sales or 0),
                    float(r.base_commission_rate or 0), r.created_at.strftime('%Y-%m-%d')
                ])
            
            return output.getvalue()
        
        return "Unsupported format"


# CLI command examples
async def main():
    """Example usage of admin CLI"""
    from dotmac_shared.database.session import get_async_db_session
    
    async with get_async_db_session() as db:
        admin_cli = ResellerAdminCLI(db)
        
        # List pending applications
        await admin_cli.list_pending_applications()
        
        # List active resellers
        await admin_cli.list_active_resellers()


if __name__ == "__main__":
    asyncio.run(main())


# Export classes
__all__ = [
    "ResellerAdminCLI",
    "ResellerAdminActions"
]