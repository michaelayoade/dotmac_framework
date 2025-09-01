"""
Complete service layer for reseller management
Implements business logic, validation, and email notifications
"""

import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import (
    ResellerApplication, Reseller, ResellerCustomer,
    ApplicationStatus, ResellerStatus, ResellerType, CommissionStructure
)
from .repositories import (
    ResellerApplicationRepository, ResellerRepository,
    ResellerCustomerRepository, ResellerOpportunityRepository,
    ResellerCommissionRepository
)


# Import enhanced email service
from .email_templates import EnhancedEmailService

# Use enhanced email service as the default
EmailService = EnhancedEmailService


class ResellerApplicationService:
    """Service for managing reseller applications"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = ResellerApplicationRepository(db, tenant_id)
        self.email_service = EmailService()
    
    async def submit_application(self, application_data: Dict[str, Any]) -> ResellerApplication:
        """Submit new reseller application with validation and notifications"""
        
        # Generate unique application ID
        application_id = f"APP-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        # Validate application data
        self._validate_application_data(application_data)
        
        # Check for duplicate applications
        existing = await self.repo.get_by_email(application_data['contact_email'])
        if existing and existing.status in [ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW]:
            raise ValueError(f"Active application already exists for {application_data['contact_email']}")
        
        # Prepare application data
        application_data.update({
            'application_id': application_id,
            'status': ApplicationStatus.SUBMITTED,
            'submitted_at': datetime.utcnow(),
            'communication_log': []
        })
        
        # Create application
        application = await self.repo.create(application_data)
        await self.repo.commit()
        
        # Send confirmation email
        await self.email_service.send_application_confirmation(application)
        
        # Log communication
        await self.repo.add_communication_log(
            application.application_id,
            {
                'type': 'email',
                'action': 'application_confirmation_sent',
                'recipient': application.contact_email,
                'status': 'sent'
            }
        )
        
        return application
    
    async def review_application(
        self, 
        application_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> ResellerApplication:
        """Mark application as under review"""
        application = await self.repo.update_status(
            application_id, 
            ApplicationStatus.UNDER_REVIEW,
            reviewer_id,
            notes
        )
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        await self.repo.commit()
        return application
    
    async def approve_application(
        self, 
        application_id: str,
        reviewer_id: str,
        approval_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Approve application and create reseller account"""
        
        # Get application
        application = await self.repo.get_by_id(application_id)
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        if not application.can_be_approved:
            raise ValueError(f"Application {application_id} cannot be approved in current status")
        
        # Update application status
        await self.repo.update_status(
            application_id,
            ApplicationStatus.APPROVED,
            reviewer_id,
            approval_data.get('notes') if approval_data else None
        )
        
        # Create reseller account
        reseller_service = ResellerService(self.db, self.tenant_id)
        reseller = await reseller_service.create_from_application(application, approval_data)
        
        # Link application to reseller
        application.approved_reseller_id = reseller.id
        
        await self.repo.commit()
        
        # Send approval notifications
        await self.email_service.send_application_approved(application, reseller)
        await self.email_service.send_welcome_package(reseller)
        
        # Log communications
        await self.repo.add_communication_log(
            application_id,
            {
                'type': 'email',
                'action': 'application_approved',
                'recipient': application.contact_email,
                'reseller_id': reseller.reseller_id,
                'status': 'sent'
            }
        )
        
        return {
            'application': application,
            'reseller': reseller,
            'message': 'Application approved and reseller account created successfully'
        }
    
    async def reject_application(
        self, 
        application_id: str,
        reviewer_id: str,
        rejection_reason: str
    ) -> ResellerApplication:
        """Reject application with notification"""
        
        application = await self.repo.update_status(
            application_id,
            ApplicationStatus.REJECTED,
            reviewer_id,
            rejection_reason
        )
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        application.decision_reason = rejection_reason
        await self.repo.commit()
        
        # Send rejection notification
        await self.email_service.send_application_rejected(application, rejection_reason)
        
        # Log communication
        await self.repo.add_communication_log(
            application_id,
            {
                'type': 'email',
                'action': 'application_rejected',
                'recipient': application.contact_email,
                'reason': rejection_reason,
                'status': 'sent'
            }
        )
        
        return application
    
    async def get_pending_applications(
        self, 
        limit: int = 50,
        offset: int = 0
    ) -> List[ResellerApplication]:
        """Get applications pending review"""
        return await self.repo.list_pending_review(limit, offset)
    
    async def search_applications(
        self,
        search_term: str,
        status: Optional[ApplicationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ResellerApplication]:
        """Search applications"""
        return await self.repo.search(search_term, status, limit, offset)
    
    def _validate_application_data(self, data: Dict[str, Any]) -> None:
        """Validate application data"""
        required_fields = ['company_name', 'contact_name', 'contact_email']
        
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Required field '{field}' is missing")
        
        # Email format validation (basic)
        email = data.get('contact_email', '')
        if '@' not in email or '.' not in email.split('@')[1]:
            raise ValueError("Invalid email format")
        
        # Phone validation (if provided)
        phone = data.get('contact_phone')
        if phone and len(phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) < 10:
            raise ValueError("Invalid phone number format")


class ResellerService:
    """Service for managing active resellers"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = ResellerRepository(db, tenant_id)
    
    async def create_from_application(
        self, 
        application: ResellerApplication,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Reseller:
        """Create reseller account from approved application"""
        
        # Generate reseller ID
        reseller_id = f"RES-{date.today().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        # Map application data to reseller fields
        reseller_data = {
            'reseller_id': reseller_id,
            'company_name': application.company_name,
            'legal_name': application.legal_company_name,
            'reseller_type': ResellerType.AUTHORIZED_DEALER,  # Default
            'status': ResellerStatus.ACTIVE,
            
            # Contact information
            'primary_contact_name': application.contact_name,
            'primary_contact_email': application.contact_email,
            'primary_contact_phone': application.contact_phone,
            
            # Business details
            'website_url': application.website_url,
            'tax_id': application.tax_id,
            'business_license': application.business_license_number,
            
            # Service capabilities from application
            'service_territories': application.desired_territories,
            'target_customer_segments': application.target_customer_segments,
            
            # Partnership terms
            'agreement_start_date': date.today(),
            'agreement_type': 'standard',
            
            # Default commission structure
            'commission_structure': CommissionStructure.PERCENTAGE,
            'base_commission_rate': Decimal('10.00'),  # 10% default
            
            # Portal access
            'portal_enabled': True,
            
            # Performance metrics (initialized to zero)
            'total_customers': 0,
            'active_customers': 0,
            'lifetime_sales': Decimal('0.00'),
            'ytd_sales': Decimal('0.00'),
            'monthly_sales': Decimal('0.00'),
            
            # Metadata
            'custom_fields': {
                'application_id': application.application_id,
                'telecom_experience_years': application.telecom_experience_years,
                'business_description': application.business_description,
                'employee_count': application.employee_count,
                'annual_revenue_range': application.annual_revenue_range
            },
            'created_by': 'system',
        }
        
        # Apply any additional data
        if additional_data:
            reseller_data.update(additional_data)
        
        # Create reseller
        reseller = await self.repo.create(reseller_data)
        
        return reseller
    
    async def get_reseller(self, reseller_id: str) -> Optional[Reseller]:
        """Get reseller by ID"""
        return await self.repo.get_by_id(reseller_id)
    
    async def list_active_resellers(
        self, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Reseller]:
        """List active resellers"""
        return await self.repo.list_active(limit, offset)
    
    async def get_dashboard_data(self, reseller_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive dashboard data for reseller"""
        return await self.repo.get_dashboard_data(reseller_id)
    
    async def update_metrics(
        self, 
        reseller_id: str,
        metrics_update: Dict[str, Any]
    ) -> Optional[Reseller]:
        """Update reseller performance metrics"""
        
        # Validate metrics data
        allowed_metrics = [
            'total_customers', 'active_customers', 'lifetime_sales',
            'ytd_sales', 'monthly_sales', 'customer_churn_rate',
            'average_install_time_days', 'customer_satisfaction_score'
        ]
        
        filtered_metrics = {
            k: v for k, v in metrics_update.items() 
            if k in allowed_metrics
        }
        
        if not filtered_metrics:
            raise ValueError("No valid metrics provided for update")
        
        reseller = await self.repo.update_metrics(reseller_id, filtered_metrics)
        if reseller:
            await self.repo.commit()
        
        return reseller
    
    async def suspend_reseller(
        self, 
        reseller_id: str,
        reason: str,
        suspended_by: str
    ) -> Optional[Reseller]:
        """Suspend reseller account"""
        reseller = await self.repo.get_by_id(reseller_id)
        if not reseller:
            return None
        
        reseller.status = ResellerStatus.SUSPENDED
        reseller.internal_notes = f"Suspended by {suspended_by}: {reason}"
        
        await self.repo.commit()
        return reseller
    
    async def reactivate_reseller(
        self, 
        reseller_id: str,
        reactivated_by: str
    ) -> Optional[Reseller]:
        """Reactivate suspended reseller"""
        reseller = await self.repo.get_by_id(reseller_id)
        if not reseller:
            return None
        
        reseller.status = ResellerStatus.ACTIVE
        reseller.internal_notes += f"\nReactivated by {reactivated_by} on {date.today()}"
        
        await self.repo.commit()
        return reseller


class ResellerCustomerService:
    """Service for managing reseller-customer relationships"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = ResellerCustomerRepository(db, tenant_id)
    
    async def assign_customer_to_reseller(
        self,
        customer_id: UUID,
        reseller_id: UUID,
        assignment_type: str = "direct",
        service_details: Optional[Dict[str, Any]] = None
    ) -> ResellerCustomer:
        """Assign a customer to a reseller"""
        
        # Check for existing assignment
        existing = await self.repo.get_by_customer(customer_id)
        if existing:
            raise ValueError(f"Customer {customer_id} is already assigned to a reseller")
        
        # Prepare assignment data
        assignment_data = {
            'assignment_type': assignment_type,
            'relationship_start_date': date.today(),
            'relationship_status': 'active'
        }
        
        # Add service details if provided
        if service_details:
            assignment_data.update(service_details)
        
        # Create assignment
        assignment = await self.repo.assign_customer(reseller_id, customer_id, assignment_data)
        await self.repo.commit()
        
        return assignment
    
    async def get_reseller_customers(
        self,
        reseller_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ResellerCustomer]:
        """Get customers assigned to a reseller"""
        return await self.repo.list_for_reseller(reseller_id, limit, offset)
    
    async def transfer_customer(
        self,
        customer_id: UUID,
        new_reseller_id: UUID,
        transfer_reason: str,
        transferred_by: str
    ) -> ResellerCustomer:
        """Transfer customer to a different reseller"""
        
        # Get current assignment
        current_assignment = await self.repo.get_by_customer(customer_id)
        if not current_assignment:
            raise ValueError(f"Customer {customer_id} is not currently assigned to any reseller")
        
        # Deactivate current assignment
        current_assignment.relationship_status = 'transferred'
        current_assignment.notes = f"Transferred to new reseller by {transferred_by}: {transfer_reason}"
        
        # Create new assignment
        new_assignment_data = {
            'assignment_type': 'transfer',
            'relationship_start_date': date.today(),
            'relationship_status': 'active',
            'notes': f"Transferred from previous reseller: {transfer_reason}"
        }
        
        new_assignment = await self.repo.assign_customer(
            new_reseller_id, 
            customer_id, 
            new_assignment_data
        )
        
        await self.repo.commit()
        return new_assignment


class ResellerOnboardingService:
    """Service for managing reseller onboarding workflow"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.reseller_service = ResellerService(db, tenant_id)
        self.email_service = EmailService()
        # Import here to avoid circular imports
        from .onboarding_workflow import OnboardingWorkflowEngine
        self.workflow_engine = OnboardingWorkflowEngine(db, tenant_id)
    
    async def create_onboarding_checklist(self, reseller_id: str) -> Dict[str, Any]:
        """Create comprehensive onboarding checklist for new reseller"""
        return await self.workflow_engine.create_onboarding_checklist(reseller_id)
    
    async def get_onboarding_progress(self, reseller_id: str) -> Dict[str, Any]:
        """Get detailed onboarding progress"""
        return await self.workflow_engine.get_onboarding_progress(reseller_id)
    
    async def update_onboarding_task(
        self,
        reseller_id: str,
        task_id: str,
        status: str,
        notes: Optional[str] = None,
        completion_percentage: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update onboarding task status with full workflow integration"""
        
        return await self.workflow_engine.update_task_status(
            reseller_id=reseller_id,
            task_id=task_id,
            new_status=status,
            completion_notes=notes,
            completion_percentage=completion_percentage
        )
    
    async def get_task_details(self, reseller_id: str, task_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific onboarding task"""
        return await self.workflow_engine.get_task_details(reseller_id, task_id)


# Export all services
__all__ = [
    "EmailService",
    "ResellerApplicationService",
    "ResellerService",
    "ResellerCustomerService",
    "ResellerOnboardingService"
]