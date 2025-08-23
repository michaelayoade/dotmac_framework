"""Contact management service for omnichannel communication."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings
from dotmac_isp.shared.exceptions import DuplicateEntityError, EntityNotFoundError

from .repository import OmnichannelRepository
from .schemas import (
    ContactCommunicationChannelCreate,
    CustomerContactCreate,
    CustomerContactResponse,
    CustomerContactUpdate,
)

logger = logging.getLogger(__name__)


class ContactManager:
    """Service class for managing customer contacts and communication channels."""

    def __init__(self, db: Session, tenant_id: UUID):
        """Initialize contact manager."""
        self.db = db
        self.tenant_id = tenant_id
        self.repository = OmnichannelRepository(db, tenant_id)
        self.settings = get_settings()

    async def create_customer_contact(
        self, contact_data: CustomerContactCreate
    ) -> CustomerContactResponse:
        """Create a new customer contact with communication channels."""
        try:
            logger.info(
                f"Creating customer contact for customer_id: {contact_data.customer_id}"
            )

            # Validate customer exists
            customer = await self.repository.get_customer(contact_data.customer_id)
            if not customer:
                raise EntityNotFoundError(
                    f"Customer not found: {contact_data.customer_id}"
                )

            # Create contact
            contact = await self.repository.create_customer_contact(
                {**contact_data.dict(), "tenant_id": self.tenant_id}
            )

            logger.info(f"Created customer contact: {contact.id}")
            return await self._build_contact_response(contact)

        except Exception as e:
            logger.error(f"Error creating customer contact: {e}")
            raise

    async def update_customer_contact(
        self, contact_id: UUID, update_data: CustomerContactUpdate
    ) -> CustomerContactResponse:
        """Update existing customer contact."""
        try:
            # Validate contact exists
            contact = await self.repository.get_customer_contact(contact_id)
            if not contact:
                raise EntityNotFoundError(f"Contact not found: {contact_id}")

            # Update contact
            updated_contact = await self.repository.update_customer_contact(
                contact_id, update_data.dict(exclude_unset=True)
            )

            logger.info(f"Updated customer contact: {contact_id}")
            return await self._build_contact_response(updated_contact)

        except Exception as e:
            logger.error(f"Error updating customer contact: {e}")
            raise

    async def add_communication_channel(
        self, channel_data: ContactCommunicationChannelCreate
    ) -> ContactCommunicationChannelCreate:
        """Add communication channel to contact."""
        try:
            logger.info(
                f"Adding communication channel for contact: {channel_data.contact_id}"
            )

            # Validate contact exists
            contact = await self.repository.get_customer_contact(
                channel_data.contact_id
            )
            if not contact:
                raise EntityNotFoundError(
                    f"Contact not found: {channel_data.contact_id}"
                )

            # Check for duplicate channel values
            existing = await self.repository.get_channel_by_value(
                channel_data.channel_type, channel_data.channel_value
            )
            if existing and existing.contact_id != channel_data.contact_id:
                raise DuplicateEntityError(
                    f"Channel {channel_data.channel_type}:"
                    f"{channel_data.channel_value} already exists"
                )

            # Handle primary channel logic
            if channel_data.is_primary:
                existing_primary = await self.repository.get_primary_channel(
                    channel_data.contact_id, channel_data.channel_type
                )
                if existing_primary:
                    await self.repository.update_channel(
                        existing_primary.id, {"is_primary": False}
                    )

            # Create channel
            channel = await self.repository.create_communication_channel(
                {**channel_data.dict(), "tenant_id": self.tenant_id}
            )

            logger.info(f"Created communication channel: {channel.id}")
            return channel

        except Exception as e:
            logger.error(f"Error adding communication channel: {e}")
            raise

    async def get_customer_contacts(
        self, customer_id: UUID
    ) -> List[CustomerContactResponse]:
        """Get all contacts for a customer."""
        contacts = await self.repository.get_customer_contacts(customer_id)
        return [await self._build_contact_response(contact) for contact in contacts]

    async def verify_communication_channel(
        self, channel_id: UUID, verification_code: Optional[str] = None
    ) -> bool:
        """Verify communication channel with optional code."""
        try:
            channel = await self.repository.get_communication_channel(channel_id)
            if not channel:
                raise EntityNotFoundError(f"Channel not found: {channel_id}")

            # For now, mark as verified if verification code matches or is not required
            if verification_code:
                # In a real implementation, check against stored verification code
                pass

            # Update verification status
            await self.repository.update_channel(
                channel_id, {"is_verified": True, "verified_at": datetime.utcnow()}
            )

            logger.info(f"Verified communication channel: {channel_id}")
            return True

        except Exception as e:
            logger.error(f"Error verifying channel: {e}")
            return False

    async def _build_contact_response(self, contact) -> CustomerContactResponse:
        """Build complete contact response with channels."""
        # Get communication channels
        channels = await self.repository.get_contact_channels(contact.id)

        return CustomerContactResponse(
            id=contact.id,
            customer_id=contact.customer_id,
            contact_type=contact.contact_type,
            first_name=contact.first_name,
            last_name=contact.last_name,
            full_name=f"{contact.first_name} {contact.last_name}".strip(),
            title=contact.title,
            department=contact.department,
            communication_channels=[
                {
                    "id": ch.id,
                    "channel_type": ch.channel_type,
                    "channel_value": ch.channel_value,
                    "is_primary": ch.is_primary,
                    "is_verified": ch.is_verified,
                }
                for ch in channels
            ],
            created_at=contact.created_at,
            updated_at=contact.updated_at,
        )
