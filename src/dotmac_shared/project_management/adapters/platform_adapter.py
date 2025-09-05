"""
Platform adapters for integrating project management with Management Platform and ISP Framework.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import (
    ProjectPriority,
    ProjectResponse,
    ProjectType,
)
from ..services.project_service import ProjectService

logger = logging.getLogger(__name__)


class BasePlatformAdapter(ABC):
    """Base adapter for platform-specific project integration."""

    def __init__(self, project_service: ProjectService):
        self.project_service = project_service

    @abstractmethod
    async def get_customer_info(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        """Get customer information from the platform."""
        pass

    @abstractmethod
    async def get_user_info(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """Get user/staff information from the platform."""
        pass

    @abstractmethod
    async def send_notification(
        self, notification_type: str, recipient: str, project: ProjectResponse, **kwargs
    ) -> bool:
        """Send notification about project events."""
        pass

    @abstractmethod
    async def create_calendar_event(
        self,
        project: ProjectResponse,
        event_type: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> bool:
        """Create calendar event for project milestone."""
        pass


class ISPProjectAdapter(BasePlatformAdapter):
    """Adapter for ISP Framework project integration."""

    def __init__(self, project_service: ProjectService, isp_client=None):
        super().__init__(project_service)
        self.isp_client = isp_client

    async def get_customer_info(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        """Get customer info from ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.get_customer(tenant_id, customer_id)
            return {"id": customer_id, "name": "Unknown Customer"}
        except Exception as e:
            logger.error(f"Error getting customer info: {e}")
            return {"id": customer_id, "name": "Unknown Customer"}

    async def get_user_info(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """Get technician info from ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.get_technician(tenant_id, user_id)
            return {"id": user_id, "name": "Unknown Technician"}
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"id": user_id, "name": "Unknown Technician"}

    async def send_notification(
        self, notification_type: str, recipient: str, project: ProjectResponse, **kwargs
    ) -> bool:
        """Send notification via ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.send_notification(
                    notification_type,
                    recipient,
                    {
                        "project_number": project.project_number,
                        "project_name": project.project_name,
                        "project_status": project.project_status,
                        "priority": project.priority,
                        **kwargs,
                    },
                )
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def create_calendar_event(
        self,
        project: ProjectResponse,
        event_type: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> bool:
        """Create calendar event in ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.create_calendar_event(
                    {
                        "title": f"{event_type}: {project.project_name}",
                        "project_id": str(project.id),
                        "start_date": start_date,
                        "end_date": end_date or start_date,
                        "type": event_type,
                    }
                )
            return True
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return False

    async def create_installation_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        service_id: str,
        installation_address: dict[str, Any],
        service_requirements: dict[str, Any],
        requested_date: Optional[date] = None,
    ) -> ProjectResponse:
        """Create an ISP customer installation project."""

        # Get customer info
        customer_info = await self.get_customer_info(tenant_id, customer_id)

        project = await self.project_service.create_customer_project(
            db=db,
            tenant_id=tenant_id,
            customer_id=customer_id,
            project_name=f"Installation for {customer_info.get('name', customer_id)}",
            project_type=ProjectType.NEW_INSTALLATION,
            description=f"New service installation at {installation_address.get('address_line1', 'customer location')}",
            priority=ProjectPriority.NORMAL,
            planned_start_date=requested_date,
            requirements=service_requirements,
            metadata={
                "service_id": service_id,
                "installation_address": installation_address,
                "source": "isp_framework",
                "platform": "isp",
            },
        )

        # Send customer notification
        await self.send_notification(
            "project_created",
            customer_info.get("email", ""),
            project,
            installation_address=installation_address,
        )

        return project

    async def create_network_expansion_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        expansion_details: dict[str, Any],
        project_manager: Optional[str] = None,
    ) -> ProjectResponse:
        """Create a network expansion project."""

        project = await self.project_service.create_customer_project(
            db=db,
            tenant_id=tenant_id,
            customer_id=None,  # Internal project
            project_name=f"Network Expansion - {expansion_details.get('area_name', 'Unknown Area')}",
            project_type=ProjectType.NETWORK_EXPANSION,
            description=expansion_details.get("description", "Network infrastructure expansion"),
            priority=ProjectPriority.HIGH,
            project_manager=project_manager,
            estimated_cost=expansion_details.get("estimated_cost"),
            requirements=expansion_details.get("technical_requirements", {}),
            metadata={
                "expansion_type": expansion_details.get("expansion_type"),
                "coverage_area": expansion_details.get("coverage_area"),
                "source": "network_planning",
                "platform": "isp",
            },
        )

        return project

    async def create_equipment_replacement_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        equipment_details: dict[str, Any],
        failure_reason: Optional[str] = None,
    ) -> ProjectResponse:
        """Create equipment replacement project."""

        priority = ProjectPriority.URGENT if failure_reason else ProjectPriority.HIGH

        project = await self.project_service.create_customer_project(
            db=db,
            tenant_id=tenant_id,
            customer_id=customer_id,
            project_name=f"Equipment Replacement - {equipment_details.get('equipment_type', 'Device')}",
            project_type=ProjectType.EQUIPMENT_REPLACEMENT,
            description=f"Replace {equipment_details.get('equipment_type')} due to {failure_reason or 'scheduled replacement'}",
            priority=priority,
            requirements=equipment_details,
            metadata={
                "old_equipment_id": equipment_details.get("equipment_id"),
                "failure_reason": failure_reason,
                "replacement_type": equipment_details.get("replacement_type"),
                "source": "field_operations",
                "platform": "isp",
            },
        )

        return project


class ManagementProjectAdapter(BasePlatformAdapter):
    """Adapter for Management Platform project integration."""

    def __init__(self, project_service: ProjectService, management_client=None):
        super().__init__(project_service)
        self.management_client = management_client

    async def get_customer_info(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        """Get customer info from Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.get_customer(tenant_id, customer_id)
            return {"id": customer_id, "name": "Unknown Customer"}
        except Exception as e:
            logger.error(f"Error getting customer info: {e}")
            return {"id": customer_id, "name": "Unknown Customer"}

    async def get_user_info(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """Get user info from Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.get_user(tenant_id, user_id)
            return {"id": user_id, "name": "Unknown User"}
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"id": user_id, "name": "Unknown User"}

    async def send_notification(
        self, notification_type: str, recipient: str, project: ProjectResponse, **kwargs
    ) -> bool:
        """Send notification via Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.send_notification(
                    notification_type,
                    recipient,
                    {
                        "project_number": project.project_number,
                        "project_name": project.project_name,
                        "project_status": project.project_status,
                        "priority": project.priority,
                        **kwargs,
                    },
                )
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def create_calendar_event(
        self,
        project: ProjectResponse,
        event_type: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> bool:
        """Create calendar event in Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.create_calendar_event(
                    {
                        "title": f"{event_type}: {project.project_name}",
                        "project_id": str(project.id),
                        "start_date": start_date,
                        "end_date": end_date or start_date,
                        "type": event_type,
                    }
                )
            return True
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return False

    async def create_tenant_deployment_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_tenant_id: str,
        deployment_config: dict[str, Any],
        project_manager: Optional[str] = None,
    ) -> ProjectResponse:
        """Create a tenant deployment project."""

        project = await self.project_service.create_customer_project(
            db=db,
            tenant_id=tenant_id,
            customer_id=customer_tenant_id,
            project_name=f"Tenant Deployment - {deployment_config.get('tenant_name', customer_tenant_id)}",
            project_type=ProjectType.DEPLOYMENT,
            description=f"Deploy ISP Framework instance for tenant {customer_tenant_id}",
            priority=ProjectPriority.HIGH,
            project_manager=project_manager,
            estimated_cost=deployment_config.get("deployment_cost"),
            requirements={
                "infrastructure_requirements": deployment_config.get("infrastructure"),
                "feature_requirements": deployment_config.get("features", []),
                "integration_requirements": deployment_config.get("integrations", []),
            },
            metadata={
                "tenant_id": customer_tenant_id,
                "deployment_type": deployment_config.get("deployment_type"),
                "region": deployment_config.get("region"),
                "plan_type": deployment_config.get("plan_type"),
                "source": "tenant_onboarding",
                "platform": "management",
            },
        )

        return project

    async def create_infrastructure_upgrade_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        upgrade_details: dict[str, Any],
        project_manager: Optional[str] = None,
    ) -> ProjectResponse:
        """Create infrastructure upgrade project."""

        project = await self.project_service.create_customer_project(
            db=db,
            tenant_id=tenant_id,
            customer_id=None,  # Internal project
            project_name=f"Infrastructure Upgrade - {upgrade_details.get('component_name')}",
            project_type=ProjectType.MIGRATION,
            description=upgrade_details.get("description", "Infrastructure component upgrade"),
            priority=ProjectPriority.HIGH,
            project_manager=project_manager,
            estimated_cost=upgrade_details.get("estimated_cost"),
            requirements={
                "current_version": upgrade_details.get("current_version"),
                "target_version": upgrade_details.get("target_version"),
                "affected_tenants": upgrade_details.get("affected_tenants", []),
                "downtime_requirements": upgrade_details.get("downtime_window"),
            },
            metadata={
                "component_type": upgrade_details.get("component_type"),
                "upgrade_type": upgrade_details.get("upgrade_type"),
                "criticality": upgrade_details.get("criticality"),
                "source": "infrastructure_management",
                "platform": "management",
            },
        )

        return project

    async def create_data_migration_project(
        self,
        db: AsyncSession,
        tenant_id: str,
        migration_details: dict[str, Any],
        project_manager: Optional[str] = None,
    ) -> ProjectResponse:
        """Create data migration project."""

        project = await self.project_service.create_customer_project(
            db=db,
            tenant_id=tenant_id,
            customer_id=migration_details.get("customer_id"),
            project_name=f"Data Migration - {migration_details.get('migration_name')}",
            project_type=ProjectType.DATA_MIGRATION,
            description=migration_details.get("description", "Data migration project"),
            priority=ProjectPriority.HIGH,
            project_manager=project_manager,
            requirements={
                "source_system": migration_details.get("source_system"),
                "target_system": migration_details.get("target_system"),
                "data_volume": migration_details.get("data_volume"),
                "validation_requirements": migration_details.get("validation_rules", []),
            },
            metadata={
                "migration_type": migration_details.get("migration_type"),
                "cutover_type": migration_details.get("cutover_type"),
                "rollback_plan": migration_details.get("rollback_plan"),
                "source": "data_operations",
                "platform": "management",
            },
        )

        return project


class ProjectPlatformAdapter:
    """Main adapter that routes to appropriate platform adapters."""

    def __init__(
        self,
        management_adapter: ManagementProjectAdapter = None,
        isp_adapter: ISPProjectAdapter = None,
    ):
        self.management_adapter = management_adapter
        self.isp_adapter = isp_adapter

    def get_adapter(self, platform: str) -> Optional[BasePlatformAdapter]:
        """Get adapter for specific platform."""
        if platform == "management":
            return self.management_adapter
        elif platform == "isp":
            return self.isp_adapter
        return None

    async def create_platform_project(
        self,
        platform: str,
        db: AsyncSession,
        tenant_id: str,
        project_type: str,
        **kwargs,
    ) -> Optional[ProjectResponse]:
        """Create project using platform-specific logic."""
        adapter = self.get_adapter(platform)
        if not adapter:
            return None

        if platform == "management":
            if project_type == "tenant_deployment":
                return await adapter.create_tenant_deployment_project(db, tenant_id, **kwargs)
            elif project_type == "infrastructure_upgrade":
                return await adapter.create_infrastructure_upgrade_project(db, tenant_id, **kwargs)
            elif project_type == "data_migration":
                return await adapter.create_data_migration_project(db, tenant_id, **kwargs)

        elif platform == "isp":
            if project_type == "installation":
                return await adapter.create_installation_project(db, tenant_id, **kwargs)
            elif project_type == "network_expansion":
                return await adapter.create_network_expansion_project(db, tenant_id, **kwargs)
            elif project_type == "equipment_replacement":
                return await adapter.create_equipment_replacement_project(db, tenant_id, **kwargs)

        # Fallback to generic project creation
        return await adapter.project_service.create_customer_project(db=db, tenant_id=tenant_id, **kwargs)

    async def send_project_notification(
        self,
        platform: str,
        notification_type: str,
        recipient: str,
        project: ProjectResponse,
        **kwargs,
    ) -> bool:
        """Send project notification through appropriate platform."""
        adapter = self.get_adapter(platform)
        if adapter:
            return await adapter.send_notification(notification_type, recipient, project, **kwargs)
        return False

    async def create_project_calendar_event(
        self,
        platform: str,
        project: ProjectResponse,
        event_type: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> bool:
        """Create calendar event through appropriate platform."""
        adapter = self.get_adapter(platform)
        if adapter:
            return await adapter.create_calendar_event(project, event_type, start_date, end_date)
        return False
