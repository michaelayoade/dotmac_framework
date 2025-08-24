"""Repository pattern for resellers database operations."""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, asc

from .models import (
    Partner,
    PartnerContact,
    PartnerCertification,
    DealRegistration,
    Commission,
    CommissionPayment,
    PartnerPerformance,
    ChannelIncentive,
    PartnerType,
    PartnerStatus,
    PartnerTier,
    CommissionStatus,
    CommissionType,
    DealStatus,
    CertificationStatus,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class PartnerRepository:
    """Repository for partner database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, partner_data: Dict[str, Any]) -> Partner:
        """Create new partner."""
        try:
            # Generate partner code if not provided
            if not partner_data.get("partner_code"):
                partner_data["partner_code"] = self._generate_partner_code(
                    partner_data.get("partner_type", "RESELLER")
                )

            partner = Partner(id=uuid4(), tenant_id=self.tenant_id, **partner_data)

            self.db.add(partner)
            self.db.commit()
            self.db.refresh(partner)
            return partner

        except IntegrityError as e:
            self.db.rollback()
            if "partner_code" in str(e):
                raise ConflictError(
                    f"Partner code {partner_data.get('partner_code')} already exists"
                )
            if "business_registration_number" in str(e):
                raise ConflictError(
                    f"Business registration number {partner_data.get('business_registration_number')} already exists"
                )
            raise ConflictError("Partner creation failed due to data conflict")

    def get_by_id(self, partner_id: UUID) -> Optional[Partner]:
        """Get partner by ID."""
        return (
            self.db.query(Partner)
            .filter(and_(Partner.id == partner_id, Partner.tenant_id == self.tenant_id))
            .first()
        )

    def get_by_partner_code(self, partner_code: str) -> Optional[Partner]:
        """Get partner by partner code."""
        return (
            self.db.query(Partner)
            .filter(
                and_(
                    Partner.partner_code == partner_code,
                    Partner.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_partners(
        self,
        partner_type: Optional[PartnerType] = None,
        partner_status: Optional[PartnerStatus] = None,
        partner_tier: Optional[PartnerTier] = None,
        territories: Optional[List[str]] = None,
        contract_expiring: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Partner]:
        """List partners with filtering."""
        query = self.db.query(Partner).filter(Partner.tenant_id == self.tenant_id)

        if partner_type:
            query = query.filter(Partner.partner_type == partner_type)
        if partner_status:
            query = query.filter(Partner.partner_status == partner_status)
        if partner_tier:
            query = query.filter(Partner.partner_tier == partner_tier)
        if territories:
            # Filter by any matching territory
            query = query.filter(
                or_(
                    *[
                        Partner.territories.op("?")(territory)
                        for territory in territories
                    ]
                )
            )
        if contract_expiring:
            # Contracts expiring within 90 days
            expiry_date = date.today() + timedelta(days=90)
            query = query.filter(
                and_(
                    Partner.contract_end_date.isnot(None),
                    Partner.contract_end_date <= expiry_date,
                    Partner.contract_end_date >= date.today(),
                )
            )

        return query.order_by(Partner.legal_name).offset(skip).limit(limit).all()

    def update_status(
        self, partner_id: UUID, status: PartnerStatus, notes: Optional[str] = None
    ) -> Optional[Partner]:
        """Update partner status."""
        partner = self.get_by_id(partner_id)
        if not partner:
            return None

        partner.partner_status = status
        partner.updated_at = datetime.utcnow()

        if notes:
            current_notes = partner.notes or ""
            partner.notes = (
                f"{current_notes}\n{datetime.utcnow().isoformat()}: {notes}".strip()
            )

        self.db.commit()
        self.db.refresh(partner)
        return partner

    def update_tier(self, partner_id: UUID, tier: PartnerTier) -> Optional[Partner]:
        """Update partner tier."""
        partner = self.get_by_id(partner_id)
        if not partner:
            return None

        partner.partner_tier = tier
        partner.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(partner)
        return partner

    def update_sales_metrics(
        self,
        partner_id: UUID,
        ytd_sales: Decimal,
        target_achievement: Optional[float] = None,
    ) -> Optional[Partner]:
        """Update partner sales metrics."""
        partner = self.get_by_id(partner_id)
        if not partner:
            return None

        partner.ytd_sales = ytd_sales
        partner.updated_at = datetime.utcnow()

        # Update tier based on performance if specified
        if target_achievement and partner.sales_target:
            if target_achievement >= 150:
                partner.partner_tier = PartnerTier.ELITE
            elif target_achievement >= 120:
                partner.partner_tier = PartnerTier.PLATINUM
            elif target_achievement >= 100:
                partner.partner_tier = PartnerTier.GOLD
            elif target_achievement >= 75:
                partner.partner_tier = PartnerTier.SILVER
            else:
                partner.partner_tier = PartnerTier.BRONZE

        self.db.commit()
        self.db.refresh(partner)
        return partner

    def get_partners_by_performance(
        self, min_achievement: float = 0.0, limit: int = 100
    ) -> List[Partner]:
        """Get partners sorted by sales performance."""
        return (
            self.db.query(Partner)
            .filter(
                and_(
                    Partner.tenant_id == self.tenant_id,
                    Partner.partner_status == PartnerStatus.ACTIVE,
                    Partner.sales_target.isnot(None),
                    Partner.sales_target > 0,
                )
            )
            .order_by(desc((Partner.ytd_sales / Partner.sales_target) * 100))
            .limit(limit)
            .all()
        )

    def get_expiring_contracts(self, days: int = 90) -> List[Partner]:
        """Get partners with contracts expiring soon."""
        expiry_date = date.today() + timedelta(days=days)

        return (
            self.db.query(Partner)
            .filter(
                and_(
                    Partner.tenant_id == self.tenant_id,
                    Partner.contract_end_date.isnot(None),
                    Partner.contract_end_date <= expiry_date,
                    Partner.contract_end_date >= date.today(),
                    Partner.partner_status == PartnerStatus.ACTIVE,
                )
            )
            .order_by(Partner.contract_end_date)
            .all()
        )

    def _generate_partner_code(self, partner_type: str) -> str:
        """Generate unique partner code."""
        prefix_map = {
            "RESELLER": "RSL",
            "DISTRIBUTOR": "DST",
            "AGENT": "AGT",
            "REFERRAL": "REF",
            "VAR": "VAR",
            "MSP": "MSP",
            "CHANNEL": "CHN",
            "AFFILIATE": "AFF",
        }

        prefix = prefix_map.get(partner_type, "PTR")
        today = date.today()
        count = (
            self.db.query(func.count(Partner.id))
            .filter(
                and_(
                    Partner.tenant_id == self.tenant_id,
                    func.date(Partner.created_at) == today,
                )
            )
            .scalar()
        )

        return f"{prefix}-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class PartnerContactRepository:
    """Repository for partner contact database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, contact_data: Dict[str, Any]) -> PartnerContact:
        """Create new partner contact."""
        contact = PartnerContact(id=uuid4(), tenant_id=self.tenant_id, **contact_data)

        # If this is marked as primary, unset other primary contacts for the same partner
        if contact_data.get("is_primary", False):
            self.db.query(PartnerContact).filter(
                and_(
                    PartnerContact.partner_id == contact_data["partner_id"],
                    PartnerContact.tenant_id == self.tenant_id,
                    PartnerContact.is_primary == True,
                )
            ).update({"is_primary": False})

        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_by_id(self, contact_id: UUID) -> Optional[PartnerContact]:
        """Get contact by ID."""
        return (
            self.db.query(PartnerContact)
            .filter(
                and_(
                    PartnerContact.id == contact_id,
                    PartnerContact.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_by_partner(self, partner_id: UUID) -> List[PartnerContact]:
        """List contacts for a partner."""
        return (
            self.db.query(PartnerContact)
            .filter(
                and_(
                    PartnerContact.partner_id == partner_id,
                    PartnerContact.tenant_id == self.tenant_id,
                )
            )
            .order_by(PartnerContact.is_primary.desc(), PartnerContact.first_name)
            .all()
        )

    def get_primary_contact(self, partner_id: UUID) -> Optional[PartnerContact]:
        """Get primary contact for partner."""
        return (
            self.db.query(PartnerContact)
            .filter(
                and_(
                    PartnerContact.partner_id == partner_id,
                    PartnerContact.tenant_id == self.tenant_id,
                    PartnerContact.is_primary == True,
                )
            )
            .first()
        )

    def set_primary_contact(self, contact_id: UUID) -> Optional[PartnerContact]:
        """Set contact as primary."""
        contact = self.get_by_id(contact_id)
        if not contact:
            return None

        # Unset other primary contacts for the same partner
        self.db.query(PartnerContact).filter(
            and_(
                PartnerContact.partner_id == contact.partner_id,
                PartnerContact.tenant_id == self.tenant_id,
                PartnerContact.id != contact_id,
            )
        ).update({"is_primary": False})

        # Set this contact as primary
        contact.is_primary = True
        self.db.commit()
        self.db.refresh(contact)
        return contact


class DealRegistrationRepository:
    """Repository for deal registration database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, deal_data: Dict[str, Any]) -> DealRegistration:
        """Create new deal registration."""
        try:
            # Generate deal number if not provided
            if not deal_data.get("deal_number"):
                deal_data["deal_number"] = self._generate_deal_number()

            # Set protection period (usually 90 days from registration)
            if not deal_data.get("protection_period_end"):
                deal_data["protection_period_end"] = date.today() + timedelta(days=90)

            deal = DealRegistration(id=uuid4(), tenant_id=self.tenant_id, **deal_data)

            self.db.add(deal)
            self.db.commit()
            self.db.refresh(deal)
            return deal

        except IntegrityError as e:
            self.db.rollback()
            if "deal_number" in str(e):
                raise ConflictError(
                    f"Deal number {deal_data.get('deal_number')} already exists"
                )
            raise ConflictError("Deal registration failed due to data conflict")

    def get_by_id(self, deal_id: UUID) -> Optional[DealRegistration]:
        """Get deal by ID."""
        return (
            self.db.query(DealRegistration)
            .filter(
                and_(
                    DealRegistration.id == deal_id,
                    DealRegistration.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_deal_number(self, deal_number: str) -> Optional[DealRegistration]:
        """Get deal by deal number."""
        return (
            self.db.query(DealRegistration)
            .filter(
                and_(
                    DealRegistration.deal_number == deal_number,
                    DealRegistration.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_deals(
        self,
        partner_id: Optional[UUID] = None,
        deal_status: Optional[DealStatus] = None,
        expected_close_from: Optional[date] = None,
        expected_close_to: Optional[date] = None,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        overdue_only: bool = False,
        protected_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DealRegistration]:
        """List deals with filtering."""
        query = self.db.query(DealRegistration).filter(
            DealRegistration.tenant_id == self.tenant_id
        )

        if partner_id:
            query = query.filter(DealRegistration.partner_id == partner_id)
        if deal_status:
            query = query.filter(DealRegistration.deal_status == deal_status)
        if expected_close_from:
            query = query.filter(
                DealRegistration.expected_close_date >= expected_close_from
            )
        if expected_close_to:
            query = query.filter(
                DealRegistration.expected_close_date <= expected_close_to
            )
        if min_value:
            query = query.filter(DealRegistration.deal_value >= min_value)
        if max_value:
            query = query.filter(DealRegistration.deal_value <= max_value)
        if overdue_only:
            query = query.filter(
                and_(
                    DealRegistration.deal_status.in_(
                        [DealStatus.SUBMITTED, DealStatus.APPROVED]
                    ),
                    DealRegistration.expected_close_date < date.today(),
                )
            )
        if protected_only:
            query = query.filter(
                and_(
                    DealRegistration.protection_period_end.isnot(None),
                    DealRegistration.protection_period_end >= date.today(),
                )
            )

        return (
            query.order_by(desc(DealRegistration.deal_value))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_status(
        self, deal_id: UUID, status: DealStatus, notes: Optional[str] = None
    ) -> Optional[DealRegistration]:
        """Update deal status."""
        deal = self.get_by_id(deal_id)
        if not deal:
            return None

        deal.deal_status = status
        deal.updated_at = datetime.utcnow()

        if status == DealStatus.APPROVED:
            deal.approval_date = date.today()
        elif status in [DealStatus.WON, DealStatus.LOST]:
            deal.actual_close_date = date.today()

        if notes:
            if status == DealStatus.REJECTED:
                deal.rejection_reason = notes
            else:
                current_notes = deal.notes or ""
                deal.notes = (
                    f"{current_notes}\n{datetime.utcnow().isoformat()}: {notes}".strip()
                )

        self.db.commit()
        self.db.refresh(deal)
        return deal

    def close_deal(
        self,
        deal_id: UUID,
        is_won: bool,
        actual_value: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> Optional[DealRegistration]:
        """Close deal as won or lost."""
        deal = self.get_by_id(deal_id)
        if not deal:
            return None

        deal.deal_status = DealStatus.WON if is_won else DealStatus.LOST
        deal.actual_close_date = date.today()

        if actual_value is not None:
            deal.actual_deal_value = actual_value

        if reason:
            deal.win_loss_reason = reason

        deal.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(deal)
        return deal

    def get_partner_deal_summary(self, partner_id: UUID) -> Dict[str, Any]:
        """Get deal summary for partner."""
        deals = (
            self.db.query(DealRegistration)
            .filter(
                and_(
                    DealRegistration.partner_id == partner_id,
                    DealRegistration.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

        # Group by status
        status_counts = {}
        status_values = {}

        for status in DealStatus:
            status_deals = [d for d in deals if d.deal_status == status]
            status_counts[status.value] = len(status_deals)
            status_values[status.value] = sum(d.deal_value for d in status_deals)

        # Calculate metrics
        won_deals = [d for d in deals if d.deal_status == DealStatus.WON]
        lost_deals = [d for d in deals if d.deal_status == DealStatus.LOST]
        closed_deals = won_deals + lost_deals

        win_rate = (len(won_deals) / len(closed_deals) * 100) if closed_deals else 0
        total_pipeline = sum(
            d.deal_value
            for d in deals
            if d.deal_status in [DealStatus.SUBMITTED, DealStatus.APPROVED]
        )
        total_won = sum(d.actual_deal_value or d.deal_value for d in won_deals)

        return {
            "total_deals": len(deals),
            "status_counts": status_counts,
            "status_values": {k: float(v) for k, v in status_values.items()},
            "win_rate": round(win_rate, 2),
            "total_pipeline_value": float(total_pipeline),
            "total_won_value": float(total_won),
            "average_deal_size": (
                float(sum(d.deal_value for d in deals) / len(deals)) if deals else 0
            ),
        }

    def _generate_deal_number(self) -> str:
        """Generate unique deal number."""
        today = date.today()
        count = (
            self.db.query(func.count(DealRegistration.id))
            .filter(
                and_(
                    DealRegistration.tenant_id == self.tenant_id,
                    func.date(DealRegistration.created_at) == today,
                )
            )
            .scalar()
        )

        return f"DEAL-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class CommissionRepository:
    """Repository for commission database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, commission_data: Dict[str, Any]) -> Commission:
        """Create new commission."""
        try:
            # Generate commission ID if not provided
            if not commission_data.get("commission_id"):
                commission_data["commission_id"] = self._generate_commission_id()

            commission = Commission(
                id=uuid4(), tenant_id=self.tenant_id, **commission_data
            )

            self.db.add(commission)
            self.db.commit()
            self.db.refresh(commission)
            return commission

        except IntegrityError as e:
            self.db.rollback()
            if "commission_id" in str(e):
                raise ConflictError(
                    f"Commission ID {commission_data.get('commission_id')} already exists"
                )
            raise ConflictError("Commission creation failed due to data conflict")

    def get_by_id(self, commission_id: UUID) -> Optional[Commission]:
        """Get commission by ID."""
        return (
            self.db.query(Commission)
            .filter(
                and_(
                    Commission.id == commission_id,
                    Commission.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_commissions(
        self,
        partner_id: Optional[UUID] = None,
        deal_id: Optional[UUID] = None,
        commission_status: Optional[CommissionStatus] = None,
        commission_type: Optional[CommissionType] = None,
        earned_from: Optional[date] = None,
        earned_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Commission]:
        """List commissions with filtering."""
        query = self.db.query(Commission).filter(Commission.tenant_id == self.tenant_id)

        if partner_id:
            query = query.filter(Commission.partner_id == partner_id)
        if deal_id:
            query = query.filter(Commission.deal_id == deal_id)
        if commission_status:
            query = query.filter(Commission.commission_status == commission_status)
        if commission_type:
            query = query.filter(Commission.commission_type == commission_type)
        if earned_from:
            query = query.filter(Commission.earned_date >= earned_from)
        if earned_to:
            query = query.filter(Commission.earned_date <= earned_to)

        return (
            query.order_by(desc(Commission.earned_date)).offset(skip).limit(limit).all()
        )

    def update_status(
        self, commission_id: UUID, status: CommissionStatus
    ) -> Optional[Commission]:
        """Update commission status."""
        commission = self.get_by_id(commission_id)
        if not commission:
            return None

        commission.commission_status = status
        commission.updated_at = datetime.utcnow()

        if status == CommissionStatus.APPROVED:
            commission.approved_date = date.today()
        elif status == CommissionStatus.PAID:
            commission.paid_date = date.today()

        self.db.commit()
        self.db.refresh(commission)
        return commission

    def get_partner_commission_summary(
        self, partner_id: UUID, year: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get commission summary for partner."""
        query = self.db.query(Commission).filter(
            and_(
                Commission.partner_id == partner_id,
                Commission.tenant_id == self.tenant_id,
            )
        )

        if year:
            query = query.filter(extract("year", Commission.earned_date) == year)

        commissions = query.all()

        # Group by status
        status_summary = {}
        for status in CommissionStatus:
            status_commissions = [
                c for c in commissions if c.commission_status == status
            ]
            status_summary[status.value] = {
                "count": len(status_commissions),
                "amount": sum(c.commission_amount for c in status_commissions),
            }

        total_earned = sum(c.commission_amount for c in commissions)
        total_paid = sum(
            c.commission_amount
            for c in commissions
            if c.commission_status == CommissionStatus.PAID
        )
        total_pending = sum(
            c.commission_amount
            for c in commissions
            if c.commission_status == CommissionStatus.PENDING
        )

        return {
            "total_commissions": len(commissions),
            "total_earned": float(total_earned),
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "status_breakdown": {
                k: {"count": v["count"], "amount": float(v["amount"])}
                for k, v in status_summary.items()
            },
            "year": year or date.today().year,
        }

    def _generate_commission_id(self) -> str:
        """Generate unique commission ID."""
        today = date.today()
        count = (
            self.db.query(func.count(Commission.id))
            .filter(
                and_(
                    Commission.tenant_id == self.tenant_id,
                    func.date(Commission.created_at) == today,
                )
            )
            .scalar()
        )

        return f"COM-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class PartnerAnalyticsRepository:
    """Repository for partner analytics and reporting."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def get_partner_performance_metrics(
        self, start_date: date, end_date: date, partner_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get comprehensive partner performance metrics."""

        # Base filters
        partner_filters = [Partner.tenant_id == self.tenant_id]
        deal_filters = [DealRegistration.tenant_id == self.tenant_id]
        commission_filters = [Commission.tenant_id == self.tenant_id]

        if partner_id:
            partner_filters.append(Partner.id == partner_id)
            deal_filters.append(DealRegistration.partner_id == partner_id)
            commission_filters.append(Commission.partner_id == partner_id)

        # Deal metrics
        deals = (
            self.db.query(DealRegistration)
            .filter(
                and_(
                    *deal_filters,
                    DealRegistration.registration_date >= start_date,
                    DealRegistration.registration_date <= end_date,
                )
            )
            .all()
        )

        won_deals = [d for d in deals if d.deal_status == DealStatus.WON]
        lost_deals = [d for d in deals if d.deal_status == DealStatus.LOST]
        pipeline_deals = [
            d
            for d in deals
            if d.deal_status in [DealStatus.SUBMITTED, DealStatus.APPROVED]
        ]

        # Commission metrics
        commissions = (
            self.db.query(Commission)
            .filter(
                and_(
                    *commission_filters,
                    Commission.earned_date >= start_date,
                    Commission.earned_date <= end_date,
                )
            )
            .all()
        )

        # Partner count and tiers
        partners = self.db.query(Partner).filter(and_(*partner_filters)).all()

        tier_distribution = {}
        for tier in PartnerTier:
            tier_distribution[tier.value] = len(
                [p for p in partners if p.partner_tier == tier]
            )

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "partners": {
                "total_active": len(
                    [p for p in partners if p.partner_status == PartnerStatus.ACTIVE]
                ),
                "tier_distribution": tier_distribution,
            },
            "deals": {
                "total_registered": len(deals),
                "total_won": len(won_deals),
                "total_lost": len(lost_deals),
                "pipeline_count": len(pipeline_deals),
                "total_pipeline_value": float(
                    sum(d.deal_value for d in pipeline_deals)
                ),
                "total_won_value": float(
                    sum(d.actual_deal_value or d.deal_value for d in won_deals)
                ),
                "win_rate": (
                    (len(won_deals) / (len(won_deals) + len(lost_deals)) * 100)
                    if (won_deals or lost_deals)
                    else 0
                ),
                "average_deal_size": (
                    float(sum(d.deal_value for d in deals) / len(deals)) if deals else 0
                ),
            },
            "commissions": {
                "total_earned": float(sum(c.commission_amount for c in commissions)),
                "total_paid": float(
                    sum(
                        c.commission_amount
                        for c in commissions
                        if c.commission_status == CommissionStatus.PAID
                    )
                ),
                "commission_count": len(commissions),
            },
        }
