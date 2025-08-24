"""
Contacts SDK - people (name, emails, phones) used across CRM, orders, support.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..models.contacts import (
    Contact,
    ContactEmail,
    ContactPhone,
    ContactType,
    EmailType,
    PhoneType,
)


class ContactService:
    """In-memory service for contact operations."""

    def __init__(self):
        """  Init   operation."""
        self._contacts: Dict[UUID, Contact] = {}
        self._emails: Dict[UUID, List[ContactEmail]] = {}
        self._phones: Dict[UUID, List[ContactPhone]] = {}
        self._email_index: Dict[str, UUID] = {}

    async def create_contact(self, **kwargs) -> Contact:
        """Create contact."""
        contact = Contact(**kwargs)
        self._contacts[contact.id] = contact
        self._emails[contact.id] = []
        self._phones[contact.id] = []
        return contact

    async def get_contact(self, contact_id: UUID) -> Optional[Contact]:
        """Get contact by ID."""
        return self._contacts.get(contact_id)

    async def add_email(self, contact_id: UUID, **kwargs) -> ContactEmail:
        """Add email to contact."""
        email = ContactEmail(contact_id=contact_id, **kwargs)

        if contact_id not in self._emails:
            self._emails[contact_id] = []

        self._emails[contact_id].append(email)
        self._email_index[email.email] = contact_id
        return email

    async def add_phone(self, contact_id: UUID, **kwargs) -> ContactPhone:
        """Add phone to contact."""
        phone = ContactPhone(contact_id=contact_id, **kwargs)

        if contact_id not in self._phones:
            self._phones[contact_id] = []

        self._phones[contact_id].append(phone)
        return phone

    async def get_contact_emails(self, contact_id: UUID) -> List[ContactEmail]:
        """Get contact emails."""
        return self._emails.get(contact_id, [])

    async def get_contact_phones(self, contact_id: UUID) -> List[ContactPhone]:
        """Get contact phones."""
        return self._phones.get(contact_id, [])


class ContactsSDK:
    """Small, composable SDK for contacts management across CRM, orders, support."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = ContactService()

    async def create_contact(
        self, first_name: str, last_name: str, contact_type: str = "person", **kwargs
    ) -> Dict[str, Any]:
        """Create contact for use across CRM, orders, support."""
        contact = await self._service.create_contact(
            tenant_id=self.tenant_id,
            first_name=first_name,
            last_name=last_name,
            contact_type=ContactType(contact_type),
            **kwargs,
        )

        return {
            "contact_id": str(contact.id),
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "display_name": contact.get_display_name(),
            "contact_type": contact.contact_type.value,
            "status": contact.status.value,
            "created_at": contact.created_at.isoformat(),
        }

    async def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact by ID."""
        contact = await self._service.get_contact(UUID(contact_id))
        if not contact or contact.tenant_id != self.tenant_id:
            return None

        return {
            "contact_id": str(contact.id),
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "middle_name": contact.middle_name,
            "display_name": contact.get_display_name(),
            "contact_type": contact.contact_type.value,
            "status": contact.status.value,
            "company": contact.company,
            "job_title": contact.job_title,
            "department": contact.department,
            "organization_id": (
                str(contact.organization_id) if contact.organization_id else None
            ),
            "account_id": str(contact.account_id) if contact.account_id else None,
            "notes": contact.notes,
            "tags": contact.tags,
            "custom_fields": contact.custom_fields,
            "created_at": contact.created_at.isoformat(),
            "updated_at": contact.updated_at.isoformat(),
        }

    async def add_email(
        self,
        contact_id: str,
        email: str,
        email_type: str = "primary",
        is_primary: bool = False,
    ) -> Dict[str, Any]:
        """Add email to contact."""
        contact_email = await self._service.add_email(
            contact_id=UUID(contact_id),
            tenant_id=self.tenant_id,
            email=email,
            email_type=EmailType(email_type),
            is_primary=is_primary,
        )

        return {
            "email_id": str(contact_email.id),
            "contact_id": str(contact_email.contact_id),
            "email": contact_email.email,
            "email_type": contact_email.email_type.value,
            "is_primary": contact_email.is_primary,
            "is_verified": contact_email.is_verified,
            "is_deliverable": contact_email.is_deliverable,
            "created_at": contact_email.created_at.isoformat(),
        }

    async def add_phone(
        self,
        contact_id: str,
        phone_number: str,
        phone_type: str = "primary",
        country_code: Optional[str] = None,
        is_primary: bool = False,
    ) -> Dict[str, Any]:
        """Add phone to contact."""
        contact_phone = await self._service.add_phone(
            contact_id=UUID(contact_id),
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            phone_type=PhoneType(phone_type),
            country_code=country_code,
            is_primary=is_primary,
        )

        return {
            "phone_id": str(contact_phone.id),
            "contact_id": str(contact_phone.contact_id),
            "phone_number": contact_phone.phone_number,
            "formatted_number": contact_phone.get_formatted_number(),
            "phone_type": contact_phone.phone_type.value,
            "country_code": contact_phone.country_code,
            "is_primary": contact_phone.is_primary,
            "is_verified": contact_phone.is_verified,
            "created_at": contact_phone.created_at.isoformat(),
        }

    async def get_contact_emails(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get all emails for contact."""
        emails = await self._service.get_contact_emails(UUID(contact_id))

        return [
            {
                "email_id": str(email.id),
                "email": email.email,
                "email_type": email.email_type.value,
                "is_primary": email.is_primary,
                "is_verified": email.is_verified,
                "is_deliverable": email.is_deliverable,
                "bounce_count": email.bounce_count,
            }
            for email in emails
            if email.tenant_id == self.tenant_id
        ]

    async def get_contact_phones(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get all phones for contact."""
        phones = await self._service.get_contact_phones(UUID(contact_id))

        return [
            {
                "phone_id": str(phone.id),
                "phone_number": phone.phone_number,
                "formatted_number": phone.get_formatted_number(),
                "phone_type": phone.phone_type.value,
                "country_code": phone.country_code,
                "is_primary": phone.is_primary,
                "is_verified": phone.is_verified,
            }
            for phone in phones
            if phone.tenant_id == self.tenant_id
        ]
