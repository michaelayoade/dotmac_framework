"""
Organizations SDK - tenants/companies, billing owner link.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.exceptions import OrganizationError
from ..models.organizations import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationType,
)


class OrganizationService:
    """In-memory service for organization operations."""

    def __init__(self):
        self._organizations: Dict[UUID, Organization] = {}
        self._members: Dict[UUID, List[OrganizationMember]] = {}
        self._name_index: Dict[str, UUID] = {}

    async def create_organization(self, **kwargs) -> Organization:
        """Create organization."""
        organization = Organization(**kwargs)

        if organization.name in self._name_index:
            raise OrganizationError(f"Organization name already exists: {organization.name}")

        self._organizations[organization.id] = organization
        self._name_index[organization.name] = organization.id
        self._members[organization.id] = []

        return organization

    async def get_organization(self, org_id: UUID) -> Optional[Organization]:
        """Get organization by ID."""
        return self._organizations.get(org_id)

    async def add_member(self, org_id: UUID, **kwargs) -> OrganizationMember:
        """Add member to organization."""
        member = OrganizationMember(organization_id=org_id, **kwargs)

        if org_id not in self._members:
            self._members[org_id] = []

        self._members[org_id].append(member)
        return member

    async def list_members(self, org_id: UUID) -> List[OrganizationMember]:
        """List organization members."""
        return self._members.get(org_id, [])


class OrganizationsSDK:
    """Small, composable SDK for organizations/tenants/companies management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = OrganizationService()

    async def create_organization(
        self,
        name: str,
        display_name: str,
        organization_type: str = "company",
        billing_owner_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create organization/tenant/company."""
        organization = await self._service.create_organization(
            tenant_id=self.tenant_id,
            name=name,
            display_name=display_name,
            organization_type=OrganizationType(organization_type),
            billing_owner_id=UUID(billing_owner_id) if billing_owner_id else None,
            **kwargs
        )

        return {
            "organization_id": str(organization.id),
            "name": organization.name,
            "display_name": organization.display_name,
            "organization_type": organization.organization_type.value,
            "status": organization.status.value,
            "billing_owner_id": str(organization.billing_owner_id) if organization.billing_owner_id else None,
            "created_at": organization.created_at.isoformat(),
        }

    async def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get organization by ID."""
        organization = await self._service.get_organization(UUID(organization_id))
        if not organization or organization.tenant_id != self.tenant_id:
            return None

        return {
            "organization_id": str(organization.id),
            "name": organization.name,
            "display_name": organization.display_name,
            "description": organization.description,
            "organization_type": organization.organization_type.value,
            "status": organization.status.value,
            "parent_organization_id": str(organization.parent_organization_id) if organization.parent_organization_id else None,
            "primary_contact_id": str(organization.primary_contact_id) if organization.primary_contact_id else None,
            "billing_contact_id": str(organization.billing_contact_id) if organization.billing_contact_id else None,
            "billing_owner_id": str(organization.billing_owner_id) if organization.billing_owner_id else None,
            "billing_account_id": organization.billing_account_id,
            "settings": organization.settings,
            "created_at": organization.created_at.isoformat(),
            "updated_at": organization.updated_at.isoformat(),
        }

    async def add_member(
        self,
        organization_id: str,
        account_id: str,
        role: str = "member",
        permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Add member to organization."""
        member = await self._service.add_member(
            org_id=UUID(organization_id),
            account_id=UUID(account_id),
            tenant_id=self.tenant_id,
            role=MemberRole(role),
            permissions=permissions or []
        )

        return {
            "member_id": str(member.id),
            "organization_id": str(member.organization_id),
            "account_id": str(member.account_id),
            "role": member.role.value,
            "permissions": member.permissions,
            "status": member.status.value,
            "joined_at": member.joined_at.isoformat(),
        }

    async def list_members(self, organization_id: str) -> List[Dict[str, Any]]:
        """List organization members."""
        members = await self._service.list_members(UUID(organization_id))

        return [
            {
                "member_id": str(member.id),
                "account_id": str(member.account_id),
                "role": member.role.value,
                "permissions": member.permissions,
                "status": member.status.value,
                "joined_at": member.joined_at.isoformat(),
            }
            for member in members
            if member.tenant_id == self.tenant_id
        ]
