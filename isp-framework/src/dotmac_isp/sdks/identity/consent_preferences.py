"""
Consent Preferences SDK - comms preferences (email/SMS/WhatsApp), GDPR/CCPA flags + audit.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.exceptions import ConsentError
from ..utils.datetime_compat import utcnow
from ..models.consent import (
    ComplianceRegion,
    ConsentAudit,
    ConsentMethod,
    ConsentPreference,
    ConsentStatus,
    ConsentType,
)


class ConsentPreferencesService:
    """In-memory service for consent preferences operations."""

    def __init__(self):
        """  Init   operation."""
        self._preferences: Dict[UUID, ConsentPreference] = {}
        self._audits: Dict[UUID, List[ConsentAudit]] = {}
        self._contact_preferences: Dict[UUID, List[UUID]] = {}

    async def create_preference(self, **kwargs) -> ConsentPreference:
        """Create consent preference."""
        preference = ConsentPreference(**kwargs)
        self._preferences[preference.id] = preference

        # Index by contact/account/customer
        if preference.contact_id:
            if preference.contact_id not in self._contact_preferences:
                self._contact_preferences[preference.contact_id] = []
            self._contact_preferences[preference.contact_id].append(preference.id)

        return preference

    async def get_preference(self, preference_id: UUID) -> Optional[ConsentPreference]:
        """Get consent preference by ID."""
        return self._preferences.get(preference_id)

    async def update_preference(
        self, preference_id: UUID, **updates
    ) -> ConsentPreference:
        """Update consent preference."""
        preference = self._preferences.get(preference_id)
        if not preference:
            raise ConsentError(f"Preference not found: {preference_id}")

        old_status = preference.status

        for key, value in updates.items():
            if hasattr(preference, key):
                setattr(preference, key, value)

        preference.updated_at = preference.updated_at.__class__.utcnow()

        # Create audit log
        await self._create_audit(preference, old_status, preference.status)

        return preference

    async def _create_audit(
        self,
        preference: ConsentPreference,
        old_status: ConsentStatus,
        new_status: ConsentStatus,
    ) -> ConsentAudit:
        """Create audit log entry."""
        audit = ConsentAudit(
            tenant_id=preference.tenant_id,
            consent_preference_id=preference.id,
            action="status_changed",
            previous_status=old_status,
            new_status=new_status,
            compliance_regions=preference.compliance_regions,
        )

        if preference.id not in self._audits:
            self._audits[preference.id] = []
        self._audits[preference.id].append(audit)

        return audit


class ConsentPreferencesSDK:
    """Small, composable SDK for consent preferences and GDPR/CCPA compliance."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = ConsentPreferencesService()

    async def grant_consent(
        self,
        consent_type: str,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        consent_method: str = "explicit_opt_in",
        compliance_regions: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Grant consent for communications preferences."""
        preference = await self._service.create_preference(
            tenant_id=self.tenant_id,
            contact_id=UUID(contact_id) if contact_id else None,
            account_id=UUID(account_id) if account_id else None,
            customer_id=UUID(customer_id) if customer_id else None,
            consent_type=ConsentType(consent_type),
            status=ConsentStatus.GRANTED,
            consent_method=ConsentMethod(consent_method),
            compliance_regions=[
                ComplianceRegion(r) for r in (compliance_regions or [])
            ],
            granted_at=(
                preference.granted_at.__class__.utcnow()
                if hasattr(preference, "granted_at")
                else None
            ),
            **kwargs,
        )

        return {
            "preference_id": str(preference.id),
            "consent_type": preference.consent_type.value,
            "status": preference.status.value,
            "consent_method": preference.consent_method.value,
            "compliance_regions": [r.value for r in preference.compliance_regions],
            "granted_at": (
                preference.granted_at.isoformat() if preference.granted_at else None
            ),
            "created_at": preference.created_at.isoformat(),
        }

    async def withdraw_consent(self, preference_id: str) -> Dict[str, Any]:
        """Withdraw consent (GDPR/CCPA compliance)."""
        preference = await self._service.update_preference(
            UUID(preference_id),
            status=ConsentStatus.WITHDRAWN,
            withdrawn_at=(
                preference.withdrawn_at.__class__.utcnow()
                if hasattr(preference, "withdrawn_at")
                else None
            ),
        )

        if preference.tenant_id != self.tenant_id:
            raise ConsentError("Preference not found in tenant")

        return {
            "preference_id": str(preference.id),
            "consent_type": preference.consent_type.value,
            "status": preference.status.value,
            "withdrawn_at": (
                preference.withdrawn_at.isoformat() if preference.withdrawn_at else None
            ),
            "updated_at": preference.updated_at.isoformat(),
        }

    async def get_consent_preference(
        self, preference_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get consent preference."""
        preference = await self._service.get_preference(UUID(preference_id))
        if not preference or preference.tenant_id != self.tenant_id:
            return None

        return {
            "preference_id": str(preference.id),
            "consent_type": preference.consent_type.value,
            "status": preference.status.value,
            "consent_method": preference.consent_method.value,
            "compliance_regions": [r.value for r in preference.compliance_regions],
            "legal_basis": preference.legal_basis,
            "collected_at": preference.collected_at.isoformat(),
            "collected_from": preference.collected_from,
            "granted_at": (
                preference.granted_at.isoformat() if preference.granted_at else None
            ),
            "withdrawn_at": (
                preference.withdrawn_at.isoformat() if preference.withdrawn_at else None
            ),
            "expires_at": (
                preference.expires_at.isoformat() if preference.expires_at else None
            ),
            "is_active": preference.is_active(),
            "is_expired": preference.is_expired(),
            "notes": preference.notes,
            "created_at": preference.created_at.isoformat(),
            "updated_at": preference.updated_at.isoformat(),
        }

    async def set_email_preferences(
        self,
        contact_id: str,
        marketing_email: bool = False,
        transactional_email: bool = True,
    ) -> List[Dict[str, Any]]:
        """Set email communication preferences."""
        preferences = []

        # Marketing email preference
        marketing_pref = (
            await self.grant_consent(
                consent_type="marketing_email", contact_id=contact_id
            )
            if marketing_email
            else await self._deny_consent("marketing_email", contact_id=contact_id)
        )
        preferences.append(marketing_pref)

        # Transactional email preference
        transactional_pref = (
            await self.grant_consent(
                consent_type="transactional_email", contact_id=contact_id
            )
            if transactional_email
            else await self._deny_consent("transactional_email", contact_id=contact_id)
        )
        preferences.append(transactional_pref)

        return preferences

    async def set_sms_preferences(
        self,
        contact_id: str,
        marketing_sms: bool = False,
        transactional_sms: bool = True,
    ) -> List[Dict[str, Any]]:
        """Set SMS communication preferences."""
        preferences = []

        # Marketing SMS preference
        marketing_pref = (
            await self.grant_consent(
                consent_type="marketing_sms", contact_id=contact_id
            )
            if marketing_sms
            else await self._deny_consent("marketing_sms", contact_id=contact_id)
        )
        preferences.append(marketing_pref)

        # Transactional SMS preference
        transactional_pref = (
            await self.grant_consent(
                consent_type="transactional_sms", contact_id=contact_id
            )
            if transactional_sms
            else await self._deny_consent("transactional_sms", contact_id=contact_id)
        )
        preferences.append(transactional_pref)

        return preferences

    async def set_gdpr_compliance(
        self,
        contact_id: str,
        data_processing: bool = True,
        third_party_sharing: bool = False,
    ) -> List[Dict[str, Any]]:
        """Set GDPR compliance flags."""
        preferences = []

        # Data processing consent
        data_pref = (
            await self.grant_consent(
                consent_type="data_processing",
                contact_id=contact_id,
                compliance_regions=["gdpr"],
            )
            if data_processing
            else await self._deny_consent(
                "data_processing", contact_id=contact_id, compliance_regions=["gdpr"]
            )
        )
        preferences.append(data_pref)

        # Third party sharing consent
        sharing_pref = (
            await self.grant_consent(
                consent_type="third_party_sharing",
                contact_id=contact_id,
                compliance_regions=["gdpr"],
            )
            if third_party_sharing
            else await self._deny_consent(
                "third_party_sharing",
                contact_id=contact_id,
                compliance_regions=["gdpr"],
            )
        )
        preferences.append(sharing_pref)

        return preferences

    async def _deny_consent(self, consent_type: str, **kwargs) -> Dict[str, Any]:
        """Internal method to deny consent."""
        preference = await self._service.create_preference(
            tenant_id=self.tenant_id,
            consent_type=ConsentType(consent_type),
            status=ConsentStatus.DENIED,
            consent_method=ConsentMethod.EXPLICIT_OPT_IN,
            compliance_regions=[
                ComplianceRegion(r) for r in kwargs.get("compliance_regions", [])
            ],
            **{
                k: UUID(v) if k.endswith("_id") and v else v
                for k, v in kwargs.items()
                if k != "compliance_regions"
            },
        )

        return {
            "preference_id": str(preference.id),
            "consent_type": preference.consent_type.value,
            "status": preference.status.value,
            "created_at": preference.created_at.isoformat(),
        }
