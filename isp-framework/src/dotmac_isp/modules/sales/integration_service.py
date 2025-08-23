"""Sales Integration Service - Handles sales to customer to project workflow."""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy.orm import Session
from fastapi import HTTPException

from .models import Opportunity, OpportunityStage, OpportunityStatus
from .service import SalesMainService
from ..identity.models import Customer, CustomerType, AccountStatus
from ..projects.service import ProjectWorkflowService
from ..projects.models import ProjectType
from ..notifications.models import (
    NotificationType, 
    Notification, 
    NotificationPriority,
    NotificationStatus,
    NotificationChannel
)


class SalesIntegrationService:
    """Service for integrating sales, customer creation, and project management."""

    def __init__(self, db: Session):
        self.db = db
        self.sales_service = SalesMainService(db)
        self.project_workflow_service = ProjectWorkflowService(db)

    async def convert_opportunity_to_customer_and_project(
        self, opportunity_id: UUID, conversion_data: Dict[str, Any], sales_owner: str
    ) -> Dict[str, Any]:
        """Complete workflow: Won Opportunity → Customer → Installation Project."""

        # 1. Get and validate opportunity
        opportunity = (
            self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        )
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        if opportunity.opportunity_status == OpportunityStatus.WON:
            raise HTTPException(
                status_code=400, detail="Opportunity already won and converted"
            )

        # 2. Close opportunity as won
        close_data = {
            "close_reason": conversion_data.get("close_reason", "Customer converted"),
            "notes": conversion_data.get(
                "conversion_notes", "Converted to customer and installation project"
            ),
        }

        opportunity = await self.sales_service.close_opportunity(
            opportunity_id=opportunity_id,
            is_won=True,
            close_reason=close_data["close_reason"],
            notes=close_data["notes"],
        )

        # 3. Create or link customer
        customer_id = conversion_data.get("customer_id")
        if not customer_id:
            customer = await self._create_customer_from_opportunity(
                opportunity, conversion_data, sales_owner
            )
            customer_id = customer.id
        else:
            customer = (
                self.db.query(Customer).filter(Customer.id == customer_id).first()
            )
            if not customer:
                raise HTTPException(
                    status_code=404, detail="Specified customer not found"
                )

        # 4. Create installation project
        project_data = await self._build_project_data_from_opportunity(
            opportunity, customer_id, conversion_data, sales_owner
        )

        project = await self.project_workflow_service.convert_opportunity_to_project(
            opportunity_id=opportunity_id,
            customer_id=customer_id,
            project_data=project_data,
            sales_owner=sales_owner,
        )

        # 5. Update opportunity with customer and project references
        opportunity.customer_id = customer_id
        # Note: Add project_id field to Opportunity model if needed
        self.db.commit()

        # 6. Trigger notifications
        await self._trigger_conversion_notifications(
            opportunity, customer, project, sales_owner
        )

        return {
            "opportunity_id": opportunity_id,
            "customer_id": customer_id,
            "project_id": project.id,
            "project_number": project.project_number,
            "conversion_status": "success",
            "next_steps": self._get_next_steps(project),
        }

    async def _create_customer_from_opportunity(
        self, opportunity: Opportunity, conversion_data: Dict[str, Any], created_by: str
    ) -> Customer:
        """Create customer from opportunity data."""

        # Generate customer number
        customer_number = await self._generate_customer_number()

        # Map opportunity customer type to Customer model
        customer_type_mapping = {
            "residential": CustomerType.RESIDENTIAL,
            "business": CustomerType.BUSINESS,
            "enterprise": CustomerType.ENTERPRISE,
        }

        customer_type = customer_type_mapping.get(
            (
                opportunity.customer_type.value
                if opportunity.customer_type
                else "residential"
            ),
            CustomerType.RESIDENTIAL,
        )

        # Prepare customer data
        customer_data = {
            "id": uuid4(),
            "tenant_id": opportunity.tenant_id,
            "customer_number": customer_number,
            "display_name": conversion_data.get(
                "customer_name", opportunity.account_name
            ),
            "customer_type": customer_type.value,
            "account_status": AccountStatus.ACTIVE.value,
            # Contact information from opportunity or conversion data
            "first_name": conversion_data.get(
                "first_name",
                (
                    opportunity.contact_name.split()[0]
                    if opportunity.contact_name
                    else None
                ),
            ),
            "last_name": conversion_data.get(
                "last_name",
                (
                    " ".join(opportunity.contact_name.split()[1:])
                    if opportunity.contact_name
                    else None
                ),
            ),
            "company_name": conversion_data.get(
                "company_name",
                (
                    opportunity.account_name
                    if customer_type != CustomerType.RESIDENTIAL
                    else None
                ),
            ),
            "email": conversion_data.get("email", opportunity.contact_email),
            "phone": conversion_data.get("phone", opportunity.contact_phone),
            # Address information
            "street_address": conversion_data.get(
                "street_address", opportunity.street_address
            ),
            "city": conversion_data.get("city", opportunity.city),
            "state_province": conversion_data.get(
                "state_province", opportunity.state_province
            ),
            "postal_code": conversion_data.get("postal_code", opportunity.postal_code),
            "country": conversion_data.get("country", "US"),
            # Business information
            "credit_limit": conversion_data.get("credit_limit", "5000.00"),
            "payment_terms": conversion_data.get("payment_terms", "net_30"),
            "installation_date": conversion_data.get("requested_install_date"),
            "notes": f"Converted from sales opportunity {opportunity.opportunity_id} by {created_by}",
            # Set creation metadata
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        customer = Customer(**customer_data)
        self.db.add(customer)
        self.db.flush()

        return customer

    async def _build_project_data_from_opportunity(
        self,
        opportunity: Opportunity,
        customer_id: UUID,
        conversion_data: Dict[str, Any],
        sales_owner: str,
    ) -> Dict[str, Any]:
        """Build project data from opportunity information."""

        # Determine project type from opportunity data
        project_type = ProjectType.NEW_INSTALLATION
        if conversion_data.get("project_type"):
            project_type = ProjectType(conversion_data["project_type"])
        elif "upgrade" in opportunity.opportunity_name.lower():
            project_type = ProjectType.SERVICE_UPGRADE
        elif (
            "relocation" in opportunity.opportunity_name.lower()
            or "move" in opportunity.opportunity_name.lower()
        ):
            project_type = ProjectType.RELOCATION

        # Calculate planned dates
        planned_start_date = conversion_data.get("planned_start_date")
        if not planned_start_date:
            # Default to 2 weeks from today
            planned_start_date = date.today() + timedelta(days=14)

        planned_end_date = conversion_data.get("planned_end_date")
        if not planned_end_date:
            # Default timeline based on project type
            timeline_days = {
                ProjectType.NEW_INSTALLATION: 21,  # 3 weeks
                ProjectType.SERVICE_UPGRADE: 7,  # 1 week
                ProjectType.RELOCATION: 14,  # 2 weeks
                ProjectType.EQUIPMENT_REPLACEMENT: 3,  # 3 days
                ProjectType.NETWORK_EXPANSION: 30,  # 1 month
            }
            days_to_add = timeline_days.get(project_type, 21)
            planned_end_date = planned_start_date + timedelta(days=days_to_add)

        return {
            "tenant_id": opportunity.tenant_id,
            "project_name": conversion_data.get(
                "project_name",
                f"{project_type.value.replace('_', ' ').title()} - {opportunity.account_name}",
            ),
            "description": conversion_data.get(
                "project_description",
                f"Installation project created from opportunity {opportunity.opportunity_id}",
            ),
            "project_type": project_type.value,
            "priority": conversion_data.get("priority", "normal"),
            "customer_id": customer_id,
            "opportunity_id": opportunity.id,
            "service_id": conversion_data.get("service_id"),
            "sales_owner": sales_owner,
            "project_manager": conversion_data.get("project_manager"),
            "lead_technician": conversion_data.get("lead_technician"),
            # Timeline
            "requested_date": conversion_data.get("requested_install_date"),
            "planned_start_date": planned_start_date,
            "planned_end_date": planned_end_date,
            # Financial
            "estimated_cost": conversion_data.get(
                "estimated_cost", opportunity.estimated_value
            ),
            # Requirements
            "service_requirements": {
                "opportunity_products": opportunity.products,
                "opportunity_services": opportunity.services,
                "solution_summary": opportunity.solution_summary,
                "custom_requirements": conversion_data.get("service_requirements", {}),
            },
            "technical_specifications": conversion_data.get(
                "technical_specifications", {}
            ),
            "equipment_list": conversion_data.get("equipment_list", []),
            "special_requirements": conversion_data.get("special_requirements"),
            # Customer contact
            "customer_contact_name": conversion_data.get(
                "contact_name", opportunity.contact_name
            ),
            "customer_contact_phone": conversion_data.get(
                "contact_phone", opportunity.contact_phone
            ),
            "customer_contact_email": conversion_data.get(
                "contact_email", opportunity.contact_email
            ),
            "preferred_contact_method": conversion_data.get(
                "preferred_contact_method", "phone"
            ),
            # Installation location
            "street_address": conversion_data.get(
                "install_address", opportunity.street_address
            ),
            "city": conversion_data.get("install_city", opportunity.city),
            "state_province": conversion_data.get(
                "install_state", opportunity.state_province
            ),
            "postal_code": conversion_data.get(
                "install_postal_code", opportunity.postal_code
            ),
            "country_code": conversion_data.get("install_country", "US"),
            "installation_address_same_as_service": conversion_data.get(
                "same_address", True
            ),
            "site_access_instructions": conversion_data.get("site_access_instructions"),
            "permits_required": conversion_data.get("permits_required", []),
        }

    async def _generate_customer_number(self) -> str:
        """Generate unique customer number."""
        # Get count of existing customers for sequential numbering
        customer_count = self.db.query(Customer).count()
        return f"CUST-{customer_count + 1:06d}"

    async def _trigger_conversion_notifications(
        self,
        opportunity: Opportunity,
        customer: Customer,
        project,  # InstallationProject
        sales_owner: str,
    ):
        """Trigger notifications for opportunity conversion."""

        # Integrate with notification service - create notifications in database
        notifications_to_send = [
            {
                "type": "opportunity_won",
                "recipients": [sales_owner, opportunity.sales_team],
                "template": "sales_opportunity_won",
                "data": {
                    "opportunity_name": opportunity.opportunity_name,
                    "customer_name": customer.display_name,
                    "project_number": project.project_number,
                    "estimated_value": str(opportunity.estimated_value),
                },
            },
            {
                "type": "customer_onboarded",
                "recipients": ["customer_success", "billing", "technical"],
                "template": "new_customer_onboarded",
                "data": {
                    "customer_number": customer.customer_number,
                    "customer_name": customer.display_name,
                    "customer_type": customer.customer_type,
                    "sales_owner": sales_owner,
                },
            },
            {
                "type": "project_created",
                "recipients": [project.project_manager, "field_ops", "scheduling"],
                "template": "installation_project_created",
                "data": {
                    "project_number": project.project_number,
                    "project_name": project.project_name,
                    "customer_name": customer.display_name,
                    "planned_start_date": str(project.planned_start_date),
                    "project_type": project.project_type.value,
                },
            },
            {
                "type": "customer_welcome",
                "recipients": [customer.email] if customer.email else [],
                "template": "customer_welcome_email",
                "data": {
                    "customer_name": customer.display_name,
                    "customer_number": customer.customer_number,
                    "project_number": project.project_number,
                    "installation_timeline": str(project.planned_start_date),
                    "contact_info": {
                        "sales_owner": sales_owner,
                        "project_manager": project.project_manager,
                    },
                },
            },
        ]

        # Create notifications in database for processing
        try:
            for notification_data in notifications_to_send:
                for recipient in notification_data['recipients']:
                    notification = Notification(
                        id=uuid4(),
                        tenant_id=customer.tenant_id,
                        notification_type=NotificationType.SALES_OPPORTUNITY,
                        channel=NotificationChannel.EMAIL,
                        priority=NotificationPriority.MEDIUM,
                        recipient_type="user",
                        recipient_identifier=recipient,
                        subject=f"Sales Update: {notification_data['type']}",
                        content=f"Notification for {notification_data['type']}",
                        template_data=notification_data['data'],
                        status=NotificationStatus.PENDING,
                        scheduled_for=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    )
                    self.db.add(notification)
            
            self.db.commit()
            print(f"[NOTIFICATION] Created {len(notifications_to_send)} notifications for conversion")
            
        except Exception as e:
            print(f"[NOTIFICATION ERROR] Failed to create notifications: {e}")
            self.db.rollback()

    def _get_next_steps(self, project) -> List[str]:
        """Get next steps after conversion."""
        return [
            f"Project {project.project_number} created and scheduled",
            "Customer onboarding email will be sent",
            "Project manager will be notified for scheduling",
            "Site survey will be scheduled within 3 business days",
            "Customer will receive installation timeline confirmation",
        ]

    async def get_conversion_summary(self, opportunity_id: UUID) -> Dict[str, Any]:
        """Get summary of conversion results."""

        opportunity = (
            self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        )
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # Get linked customer
        customer = None
        if opportunity.customer_id:
            customer = (
                self.db.query(Customer)
                .filter(Customer.id == opportunity.customer_id)
                .first()
            )

        # Get linked project
        # Note: Would need to add project_id to Opportunity model or query by opportunity_id
        # For now, we'll query projects by opportunity_id
        from ..projects.models import InstallationProject

        project = (
            self.db.query(InstallationProject)
            .filter(InstallationProject.opportunity_id == opportunity_id)
            .first()
        )

        return {
            "opportunity": {
                "id": str(opportunity.id),
                "name": opportunity.opportunity_name,
                "status": opportunity.opportunity_status.value,
                "stage": opportunity.opportunity_stage.value,
                "value": str(opportunity.estimated_value),
                "close_date": (
                    str(opportunity.actual_close_date)
                    if opportunity.actual_close_date
                    else None
                ),
            },
            "customer": (
                {
                    "id": str(customer.id) if customer else None,
                    "number": customer.customer_number if customer else None,
                    "name": customer.display_name if customer else None,
                    "type": customer.customer_type if customer else None,
                    "status": customer.account_status if customer else None,
                }
                if customer
                else None
            ),
            "project": (
                {
                    "id": str(project.id) if project else None,
                    "number": project.project_number if project else None,
                    "name": project.project_name if project else None,
                    "type": project.project_type.value if project else None,
                    "status": project.project_status.value if project else None,
                    "completion": project.completion_percentage if project else None,
                    "start_date": (
                        str(project.planned_start_date)
                        if project and project.planned_start_date
                        else None
                    ),
                    "end_date": (
                        str(project.planned_end_date)
                        if project and project.planned_end_date
                        else None
                    ),
                }
                if project
                else None
            ),
            "conversion_complete": bool(customer and project),
            "timeline": {
                "opportunity_created": str(opportunity.created_at),
                "opportunity_closed": (
                    str(opportunity.actual_close_date)
                    if opportunity.actual_close_date
                    else None
                ),
                "customer_created": str(customer.created_at) if customer else None,
                "project_created": str(project.created_at) if project else None,
            },
        }
