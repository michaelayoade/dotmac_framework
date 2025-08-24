"""Integration service connecting omnichannel with other modules."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    ServiceError,
)
from dotmac_isp.modules.omnichannel.cache import omnichannel_cache

logger = logging.getLogger(__name__)


class OmnichannelIntegrationService:
    """Service for integrating omnichannel with other modules in the monolith."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id
        self.cache = omnichannel_cache

        # Lazy load other services to avoid circular imports
        self._identity_service = None
        self._billing_service = None
        self._notification_service = None

    # ===== IDENTITY MODULE INTEGRATION =====

    @property
    def identity_service(self):
        """Lazy load identity service."""
        if self._identity_service is None:
            try:
                from dotmac_isp.modules.identity.service import CustomerService

                self._identity_service = CustomerService(self.db, self.tenant_id)
            except ImportError as e:
                logger.error(f"Failed to import identity service: {e}")
                self._identity_service = None
        return self._identity_service

    async def get_customer_details(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer details from identity module."""
        try:
            if not self.identity_service:
                logger.warning("Identity service not available")
                return None

            # Check cache first
            cache_key = f"customer_details_{customer_id}"
            cached_customer = self.cache.get(cache_key)
            if cached_customer:
                return cached_customer

            # Fetch from identity service
            customer = await self.identity_service.get_customer(customer_id)

            if customer:
                customer_data = {
                    "id": str(customer.id),
                    "customer_number": customer.customer_number,
                    "display_name": customer.display_name,
                    "customer_type": customer.customer_type,
                    "account_status": customer.account_status,
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "company_name": customer.company_name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "address": {
                        "street": customer.street_address,
                        "city": customer.city,
                        "state": customer.state_province,
                        "postal_code": customer.postal_code,
                        "country": customer.country,
                    },
                    "credit_limit": customer.credit_limit,
                    "payment_terms": customer.payment_terms,
                    "installation_date": (
                        customer.installation_date.isoformat()
                        if customer.installation_date
                        else None
                    ),
                    "portal_id": customer.portal_id,
                }

                # Cache for 5 minutes
                self.cache.set(cache_key, customer_data, ttl=300)
                return customer_data

            return None

        except Exception as e:
            logger.error(f"Failed to get customer details for {customer_id}: {e}")
            return None

    async def sync_customer_contact_info(
        self, customer_id: str, contact_id: str
    ) -> bool:
        """Sync contact information changes back to identity module."""
        try:
            from dotmac_isp.modules.omnichannel.models_production import CustomerContact

            # Get contact details
            contact = (
                self.db.query(CustomerContact)
                .filter(
                    CustomerContact.id == contact_id,
                    CustomerContact.tenant_id == self.tenant_id,
                )
                .first()
            )

            if not contact or not self.identity_service:
                return False

            # Update customer in identity module if this is the primary contact
            if contact.is_primary and contact.contact_type.value == "primary":
                customer_update = {
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "email": contact.email_primary,
                    "phone": contact.phone_primary,
                }

                # Use identity service to update
                updated = await self.identity_service.update_customer(
                    customer_id, customer_update
                )

                if updated:
                    # Clear cached customer data
                    cache_key = f"customer_details_{customer_id}"
                    self.cache.delete(cache_key)
                    logger.info(
                        f"Synced primary contact info for customer {customer_id}"
                    )
                    return True

            return True

        except Exception as e:
            logger.error(f"Failed to sync customer contact info: {e}")
            return False

    async def get_customer_service_status(self, customer_id: str) -> Dict[str, Any]:
        """Get customer's service status for interaction context."""
        try:
            customer_details = await self.get_customer_details(customer_id)
            if not customer_details:
                return {"status": "unknown", "services": []}

            # Check if services module is available
            try:
                from dotmac_isp.modules.services.service import ServiceInstanceService

                service_service = ServiceInstanceService(self.db, self.tenant_id)

                # Get active services
                services = await service_service.get_customer_services(customer_id)

                service_status = {
                    "customer_status": customer_details["account_status"],
                    "customer_type": customer_details["customer_type"],
                    "active_services": len(
                        [s for s in services if s.get("status") == "active"]
                    ),
                    "total_services": len(services),
                    "services": services,
                    "has_billing_issues": customer_details["account_status"]
                    in ["suspended", "pending"],
                }

                return service_status

            except ImportError:
                logger.warning("Services module not available")
                return {
                    "customer_status": customer_details["account_status"],
                    "customer_type": customer_details["customer_type"],
                    "services": [],
                }

        except Exception as e:
            logger.error(f"Failed to get customer service status: {e}")
            return {"status": "error", "error": str(e)}

    # ===== BILLING MODULE INTEGRATION =====

    @property
    def billing_service(self):
        """Lazy load billing service."""
        if self._billing_service is None:
            try:
                from dotmac_isp.modules.billing.service import BillingService

                self._billing_service = BillingService(self.db, self.tenant_id)
            except ImportError as e:
                logger.error(f"Failed to import billing service: {e}")
                self._billing_service = None
        return self._billing_service

    async def get_customer_billing_status(self, customer_id: str) -> Dict[str, Any]:
        """Get customer billing status for interaction context."""
        try:
            if not self.billing_service:
                return {"status": "unavailable"}

            # Check cache first
            cache_key = f"billing_status_{customer_id}"
            cached_status = self.cache.get(cache_key)
            if cached_status:
                return cached_status

            # Get billing information
            billing_info = await self.billing_service.get_customer_billing_summary(
                customer_id
            )

            if billing_info:
                billing_status = {
                    "account_balance": billing_info.get("current_balance", 0.0),
                    "outstanding_amount": billing_info.get("outstanding_amount", 0.0),
                    "last_payment_date": billing_info.get("last_payment_date"),
                    "next_bill_date": billing_info.get("next_bill_date"),
                    "payment_method": billing_info.get("payment_method"),
                    "billing_status": billing_info.get("status", "unknown"),
                    "overdue_invoices": billing_info.get("overdue_invoices", 0),
                }

                # Cache for 10 minutes
                self.cache.set(cache_key, billing_status, ttl=600)
                return billing_status

            return {"status": "no_data"}

        except Exception as e:
            logger.error(f"Failed to get customer billing status: {e}")
            return {"status": "error", "error": str(e)}

    # ===== NOTIFICATION MODULE INTEGRATION =====

    @property
    def notification_service(self):
        """Lazy load notification service."""
        if self._notification_service is None:
            try:
                # Use the existing notification tasks
                from dotmac_isp.modules.notifications.tasks import send_notification

                self._notification_service = send_notification
            except ImportError as e:
                logger.error(f"Failed to import notification service: {e}")
                self._notification_service = None
        return self._notification_service

    async def send_interaction_notification(
        self,
        interaction_id: str,
        notification_type: str,
        recipients: List[str],
        data: Dict[str, Any] = None,
    ):
        """Send notifications about interaction events."""
        try:
            if not self.notification_service:
                logger.warning("Notification service not available")
                return False

            notification_data = {
                "type": f"omnichannel_{notification_type}",
                "tenant_id": self.tenant_id,
                "recipients": recipients,
                "data": {
                    "interaction_id": interaction_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(data or {}),
                },
                "channels": ["email", "push"],
                "priority": "normal",
            }

            # Send via existing notification system
            self.notification_service.delay(notification_data)

            logger.info(
                f"Sent {notification_type} notification for interaction {interaction_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send interaction notification: {e}")
            return False

    # ===== CONTEXT ENRICHMENT =====

    async def enrich_interaction_context(
        self, interaction_id: str, customer_id: str
    ) -> Dict[str, Any]:
        """Enrich interaction with context from other modules."""
        try:
            # Get customer details
            customer_details = await self.get_customer_details(customer_id)

            # Get service status
            service_status = await self.get_customer_service_status(customer_id)

            # Get billing status
            billing_status = await self.get_customer_billing_status(customer_id)

            # Get interaction history summary (recent interactions)
            interaction_history = await self.get_recent_interaction_summary(customer_id)

            enriched_context = {
                "customer": customer_details,
                "services": service_status,
                "billing": billing_status,
                "history": interaction_history,
                "context_generated_at": datetime.utcnow().isoformat(),
                "priority_indicators": self._calculate_priority_indicators(
                    customer_details, service_status, billing_status
                ),
            }

            # Cache the enriched context
            self.cache.cache_interaction_context(
                self.tenant_id, interaction_id, enriched_context, ttl=1800
            )

            return enriched_context

        except Exception as e:
            logger.error(f"Failed to enrich interaction context: {e}")
            return {
                "error": str(e),
                "context_generated_at": datetime.utcnow().isoformat(),
            }

    async def get_recent_interaction_summary(
        self, customer_id: str, limit: int = 5
    ) -> Dict[str, Any]:
        """Get summary of recent interactions for this customer."""
        try:
            from dotmac_isp.modules.omnichannel.models_production import (
                CommunicationInteraction,
                CustomerContact,
            )
            from sqlalchemy import desc

            # Get recent interactions
            recent_interactions = (
                self.db.query(CommunicationInteraction)
                .join(
                    CustomerContact,
                    CommunicationInteraction.contact_id == CustomerContact.id,
                )
                .filter(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.tenant_id == self.tenant_id,
                )
                .order_by(desc(CommunicationInteraction.created_at))
                .limit(limit)
                .all()
            )

            interaction_summary = {
                "total_recent": len(recent_interactions),
                "interactions": [],
                "most_used_channel": None,
                "average_satisfaction": None,
                "open_issues": 0,
            }

            if recent_interactions:
                # Build interaction list
                for interaction in recent_interactions:
                    interaction_summary["interactions"].append(
                        {
                            "id": str(interaction.id),
                            "subject": interaction.subject,
                            "status": interaction.status.value,
                            "channel": (
                                interaction.channel_info.registered_channel.channel_name
                                if interaction.channel_info
                                else "Unknown"
                            ),
                            "created_at": interaction.created_at.isoformat(),
                            "satisfaction_rating": interaction.satisfaction_rating,
                        }
                    )

                # Calculate statistics
                channel_usage = {}
                satisfaction_ratings = []
                open_count = 0

                for interaction in recent_interactions:
                    # Channel usage
                    if (
                        interaction.channel_info
                        and interaction.channel_info.registered_channel
                    ):
                        channel_name = (
                            interaction.channel_info.registered_channel.channel_name
                        )
                        channel_usage[channel_name] = (
                            channel_usage.get(channel_name, 0) + 1
                        )

                    # Satisfaction ratings
                    if interaction.satisfaction_rating:
                        satisfaction_ratings.append(interaction.satisfaction_rating)

                    # Open issues
                    if interaction.status.value in [
                        "pending",
                        "in_progress",
                        "waiting_customer",
                    ]:
                        open_count += 1

                # Most used channel
                if channel_usage:
                    interaction_summary["most_used_channel"] = max(
                        channel_usage, key=channel_usage.get
                    )

                # Average satisfaction
                if satisfaction_ratings:
                    interaction_summary["average_satisfaction"] = sum(
                        satisfaction_ratings
                    ) / len(satisfaction_ratings)

                interaction_summary["open_issues"] = open_count

            return interaction_summary

        except Exception as e:
            logger.error(
                f"Failed to get interaction summary for customer {customer_id}: {e}"
            )
            return {"error": str(e)}

    def _calculate_priority_indicators(
        self, customer_details: Dict, service_status: Dict, billing_status: Dict
    ) -> Dict[str, Any]:
        """Calculate priority indicators based on customer context."""
        try:
            indicators = {
                "priority_level": 3,  # Default: normal
                "factors": [],
                "vip_customer": False,
                "urgent_flags": [],
            }

            # Customer type priority
            if (
                customer_details
                and customer_details.get("customer_type") == "enterprise"
            ):
                indicators["priority_level"] = min(indicators["priority_level"], 2)
                indicators["factors"].append("Enterprise customer")

            # Service issues priority
            if service_status and service_status.get("has_billing_issues"):
                indicators["urgent_flags"].append("Account has billing issues")
                indicators["priority_level"] = min(indicators["priority_level"], 2)

            # Billing priority
            if billing_status:
                outstanding = billing_status.get("outstanding_amount", 0)
                if outstanding > 500:  # Configurable threshold
                    indicators["urgent_flags"].append(
                        f"Outstanding amount: ${outstanding}"
                    )
                    indicators["priority_level"] = min(indicators["priority_level"], 2)

                overdue = billing_status.get("overdue_invoices", 0)
                if overdue > 0:
                    indicators["urgent_flags"].append(f"{overdue} overdue invoices")
                    indicators["priority_level"] = min(indicators["priority_level"], 2)

            # VIP determination (could be based on revenue, contract terms, etc.)
            if customer_details:
                customer_type = customer_details.get("customer_type")
                if customer_type == "enterprise":
                    indicators["vip_customer"] = True
                    indicators["priority_level"] = 1  # Highest priority

            return indicators

        except Exception as e:
            logger.error(f"Failed to calculate priority indicators: {e}")
            return {"priority_level": 3, "factors": [], "error": str(e)}

    # ===== CACHE MANAGEMENT =====

    def invalidate_customer_cache(self, customer_id: str):
        """Invalidate all cached data for a customer."""
        try:
            cache_keys = [
                f"customer_details_{customer_id}",
                f"billing_status_{customer_id}",
                f"service_status_{customer_id}",
            ]

            for key in cache_keys:
                self.cache.delete(key)

            # Also invalidate customer threads cache
            self.cache.invalidate_customer_threads(self.tenant_id, customer_id)

            logger.info(f"Invalidated cache for customer {customer_id}")

        except Exception as e:
            logger.error(f"Failed to invalidate customer cache: {e}")

    # ===== HEALTH CHECK =====

    async def integration_health_check(self) -> Dict[str, Any]:
        """Check health of all integrated modules."""
        health_status = {
            "identity_service": "unknown",
            "billing_service": "unknown",
            "notification_service": "unknown",
            "cache_service": "unknown",
            "overall_status": "healthy",
            "checked_at": datetime.utcnow().isoformat(),
        }

        try:
            # Check identity service
            if self.identity_service:
                health_status["identity_service"] = "available"
            else:
                health_status["identity_service"] = "unavailable"
                health_status["overall_status"] = "degraded"

            # Check billing service
            if self.billing_service:
                health_status["billing_service"] = "available"
            else:
                health_status["billing_service"] = "unavailable"
                health_status["overall_status"] = "degraded"

            # Check notification service
            if self.notification_service:
                health_status["notification_service"] = "available"
            else:
                health_status["notification_service"] = "unavailable"
                health_status["overall_status"] = "degraded"

            # Check cache service
            try:
                cache_stats = self.cache.get_cache_stats(self.tenant_id)
                if "error" not in cache_stats:
                    health_status["cache_service"] = "available"
                    health_status["cache_stats"] = cache_stats
                else:
                    health_status["cache_service"] = "error"
                    health_status["overall_status"] = "degraded"
            except Exception as e:
                health_status["cache_service"] = "error"
                health_status["cache_error"] = str(e)
                health_status["overall_status"] = "degraded"

        except Exception as e:
            logger.error(f"Integration health check failed: {e}")
            health_status["overall_status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status
