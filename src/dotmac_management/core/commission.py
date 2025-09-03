"""
Commission calculation engine for partner management
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..models.partner import Commission, Partner, PartnerCustomer


class CommissionTier(BaseModel, timezone):
    """Commission tier configuration"""

    id: str
    name: str
    minimum_revenue: float
    base_rate: float  # Decimal (0.05 = 5%)
    bonus_rate: float = 0.0
    product_multipliers: Dict[str, float] = Field(default_factory=dict)


class CommissionResult(BaseModel):
    """Commission calculation result"""

    customer_id: str
    partner_id: str
    base_commission: float
    bonus_commission: float
    total_commission: float
    effective_rate: float
    tier: str
    breakdown: Dict[str, float]
    calculated_at: datetime
    audit_trail: List[str]


class CommissionCalculator:
    """Commission calculation engine"""

    # Default commission tiers
    DEFAULT_TIERS = [
        CommissionTier(
            id="bronze",
            name="Bronze Partner",
            minimum_revenue=0,
            base_rate=0.05,  # 5%
            product_multipliers={
                "residential_basic": 1.0,
                "residential_premium": 1.2,
                "business_pro": 1.5,
                "enterprise": 2.0,
            },
        ),
        CommissionTier(
            id="silver",
            name="Silver Partner",
            minimum_revenue=50000,
            base_rate=0.07,  # 7%
            bonus_rate=0.01,  # 1% bonus
            product_multipliers={
                "residential_basic": 1.0,
                "residential_premium": 1.3,
                "business_pro": 1.6,
                "enterprise": 2.2,
            },
        ),
        CommissionTier(
            id="gold",
            name="Gold Partner",
            minimum_revenue=150000,
            base_rate=0.10,  # 10%
            bonus_rate=0.02,  # 2% bonus
            product_multipliers={
                "residential_basic": 1.1,
                "residential_premium": 1.4,
                "business_pro": 1.8,
                "enterprise": 2.5,
            },
        ),
        CommissionTier(
            id="platinum",
            name="Platinum Partner",
            minimum_revenue=500000,
            base_rate=0.12,  # 12%
            bonus_rate=0.03,  # 3% bonus
            product_multipliers={
                "residential_basic": 1.2,
                "residential_premium": 1.5,
                "business_pro": 2.0,
                "enterprise": 3.0,
            },
        ),
    ]

    def __init__(self, custom_tiers: List[CommissionTier] = None):
        self.tiers = {tier.id: tier for tier in (custom_tiers or self.DEFAULT_TIERS)}
        self.audit_log: List[str] = []

    def _add_audit(self, message: str) -> None:
        """Add message to audit trail"""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.audit_log.append(f"{timestamp}: {message}")

    def _get_tier(self, tier_id: str) -> CommissionTier:
        """Get commission tier by ID"""
        tier = self.tiers.get(tier_id)
        if not tier:
            raise ValueError(f"Invalid commission tier: {tier_id}")
        return tier

    def _validate_tier_eligibility(
        self, lifetime_revenue: float, tier: CommissionTier
    ) -> bool:
        """Check if partner is eligible for tier"""
        return lifetime_revenue >= tier.minimum_revenue

    def _calculate_new_customer_bonus(
        self, tier: CommissionTier, monthly_revenue: float
    ) -> float:
        """Calculate new customer bonus (50% of first month's commission)"""
        base_commission = monthly_revenue * tier.base_rate
        return base_commission * 0.5

    def _calculate_contract_length_bonus(
        self, contract_length: int, base_commission: float
    ) -> float:
        """Calculate bonus based on contract length"""
        if contract_length >= 24:
            return base_commission * 0.1  # 10% for 2+ years
        elif contract_length >= 12:
            return base_commission * 0.05  # 5% for 1+ year
        return 0.0

    def _calculate_territory_bonus(
        self, territory_bonus_rate: float, base_commission: float
    ) -> float:
        """Calculate territory-specific bonus"""
        return base_commission * territory_bonus_rate

    def calculate_customer_commission(
        self,
        customer: PartnerCustomer,
        partner: Partner,
        is_new_customer: bool = False,
        territory_bonus_rate: float = 0.0,
        promotional_rate: float = 1.0,
    ) -> CommissionResult:
        """Calculate commission for a specific customer"""

        # Clear previous audit log
        self.audit_log = []

        self._add_audit(f"Starting commission calculation for customer {customer.id}")

        # Get partner tier
        tier = self._get_tier(partner.tier)
        self._add_audit(f"Using tier: {tier.name} ({tier.base_rate * 100}% base rate)")

        # Validate tier eligibility
        if not self._validate_tier_eligibility(partner.total_lifetime_revenue, tier):
            error_msg = (
                f"Partner not eligible for {tier.name} tier "
                f"(requires ${tier.minimum_revenue:,.2f}, has ${partner.total_lifetime_revenue:,.2f})"
            )
            self._add_audit(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

        # Base commission calculation
        base_amount = customer.mrr
        tier_multiplier = tier.base_rate + tier.bonus_rate
        product_multiplier = tier.product_multipliers.get(customer.service_plan, 1.0)

        base_commission = base_amount * tier_multiplier * product_multiplier
        self._add_audit(
            f"Base commission: ${base_amount:.2f} × {tier_multiplier} × {product_multiplier} = ${base_commission:.2f}"
        )

        # Calculate bonuses
        new_customer_bonus = 0.0
        if is_new_customer:
            new_customer_bonus = self._calculate_new_customer_bonus(tier, customer.mrr)
            self._add_audit(f"New customer bonus: ${new_customer_bonus:.2f}")

        contract_length_bonus = self._calculate_contract_length_bonus(
            customer.contract_length, base_commission
        )
        self._add_audit(f"Contract length bonus: ${contract_length_bonus:.2f}")

        territory_bonus = self._calculate_territory_bonus(
            territory_bonus_rate, base_commission
        )
        self._add_audit(f"Territory bonus: ${territory_bonus:.2f}")

        # Calculate total before promotional adjustment
        pre_promotional_total = (
            base_commission
            + new_customer_bonus
            + contract_length_bonus
            + territory_bonus
        )

        # Apply promotional adjustment
        total_commission = pre_promotional_total * promotional_rate
        promotional_adjustment = total_commission - pre_promotional_total

        bonus_commission = new_customer_bonus + contract_length_bonus + territory_bonus
        effective_rate = total_commission / customer.mrr if customer.mrr > 0 else 0

        self._add_audit(
            f"Final commission: ${total_commission:.2f} ({effective_rate * 100:.2f}% effective rate)"
        )

        # Security check: Ensure commission doesn't exceed reasonable limits
        max_commission_rate = 0.5  # 50% maximum
        if effective_rate > max_commission_rate:
            error_msg = f"Commission rate {effective_rate * 100:.2f}% exceeds maximum allowed {max_commission_rate * 100}%"
            self._add_audit(f"SECURITY ERROR: {error_msg}")
            raise ValueError(error_msg)

        return CommissionResult(
            customer_id=customer.id,
            partner_id=partner.id,
            base_commission=base_commission,
            bonus_commission=bonus_commission,
            total_commission=total_commission,
            effective_rate=effective_rate,
            tier=tier.name,
            breakdown={
                "base_amount": base_amount,
                "tier_multiplier": tier_multiplier,
                "product_multiplier": product_multiplier,
                "new_customer_bonus": new_customer_bonus,
                "territory_bonus": territory_bonus,
                "contract_length_bonus": contract_length_bonus,
                "promotional_adjustment": promotional_adjustment,
            },
            calculated_at=datetime.now(timezone.utc),
            audit_trail=list(self.audit_log),
        )

    def create_commission_record(
        self,
        db: Session,
        customer_id: str,
        partner_id: str,
        commission_result: CommissionResult,
    ) -> Commission:
        """Create commission record in database"""

        now = datetime.now(timezone.utc)

        commission = Commission(
            partner_id=partner_id,
            customer_id=customer_id,
            amount=commission_result.total_commission,
            base_amount=commission_result.base_commission,
            bonus_amount=commission_result.bonus_commission,
            effective_rate=commission_result.effective_rate,
            tier_multiplier=commission_result.breakdown["tier_multiplier"],
            product_multiplier=commission_result.breakdown["product_multiplier"],
            new_customer_bonus=commission_result.breakdown["new_customer_bonus"],
            territory_bonus=commission_result.breakdown["territory_bonus"],
            contract_length_bonus=commission_result.breakdown["contract_length_bonus"],
            promotional_adjustment=commission_result.breakdown[
                "promotional_adjustment"
            ],
            commission_type="monthly",
            period_start=now,
            period_end=now + timedelta(days=30),
            status="pending",
            calculation_method="automated",
            calculation_details={
                "audit_trail": commission_result.audit_trail,
                "breakdown": commission_result.breakdown,
                "tier": commission_result.tier,
                "calculated_at": commission_result.calculated_at.isoformat(),
            },
            created_by="system",
        )
        db.add(commission)
        db.commit()
        db.refresh(commission)

        return commission

    def update_commission_record(
        self,
        db: Session,
        customer_id: str,
        partner_id: str,
        commission_result: CommissionResult,
    ) -> Commission:
        """Update existing commission record"""

        # Find most recent pending commission for this customer
        commission = (
            db.query(Commission)
            .filter(
                Commission.customer_id == customer_id,
                Commission.partner_id == partner_id,
                Commission.status == "pending",
            )
            .order_by(Commission.created_at.desc())
            .first()
        )

        if not commission:
            # Create new record if none exists
            return self.create_commission_record(
                db, customer_id, partner_id, commission_result
            )

        # Update existing record
        commission.amount = commission_result.total_commission
        commission.base_amount = commission_result.base_commission
        commission.bonus_amount = commission_result.bonus_commission
        commission.effective_rate = commission_result.effective_rate
        commission.tier_multiplier = commission_result.breakdown["tier_multiplier"]
        commission.product_multiplier = commission_result.breakdown[
            "product_multiplier"
        ]
        commission.new_customer_bonus = commission_result.breakdown[
            "new_customer_bonus"
        ]
        commission.territory_bonus = commission_result.breakdown["territory_bonus"]
        commission.contract_length_bonus = commission_result.breakdown[
            "contract_length_bonus"
        ]
        commission.promotional_adjustment = commission_result.breakdown[
            "promotional_adjustment"
        ]

        commission.calculation_details = {
            "audit_trail": commission_result.audit_trail,
            "breakdown": commission_result.breakdown,
            "tier": commission_result.tier,
            "calculated_at": commission_result.calculated_at.isoformat(),
        }

        commission.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(commission)

        return commission

    def validate_commission(
        self, commission: Commission, customer: PartnerCustomer, partner: Partner
    ) -> bool:
        """Validate existing commission calculation"""

        try:
            recalculated = self.calculate_customer_commission(customer, partner)

            # Compare with tolerance for floating point precision
            tolerance = 0.01
            total_match = (
                abs(recalculated.total_commission - commission.amount) < tolerance
            )
            rate_match = (
                abs(recalculated.effective_rate - commission.effective_rate) < tolerance
            )

            return total_match and rate_match
        except Exception:
            return False

    def determine_eligible_tier(self, lifetime_revenue: float) -> CommissionTier:
        """Determine highest tier partner qualifies for"""

        eligible_tiers = [
            tier
            for tier in self.tiers.values()
            if lifetime_revenue >= tier.minimum_revenue
        ]

        # Sort by minimum revenue descending to get highest tier first
        eligible_tiers.sort(key=lambda t: t.minimum_revenue, reverse=True)

        return eligible_tiers[0] if eligible_tiers else list(self.tiers.values())[0]

    def calculate_batch_commissions(
        self, db: Session, partner_id: str, recalculate_all: bool = False
    ) -> List[CommissionResult]:
        """Calculate commissions for all partner customers"""

        partner = db.query(Partner).filter(Partner.id == partner_id).first()
        if not partner:
            raise ValueError(f"Partner {partner_id} not found")

        customers_query = db.query(PartnerCustomer).filter(
            PartnerCustomer.partner_id == partner_id, PartnerCustomer.status == "active"
        )
        if not recalculate_all:
            # Only calculate for customers without pending commissions
            customers_with_commissions = (
                db.query(Commission.customer_id)
                .filter(
                    Commission.partner_id == partner_id, Commission.status == "pending"
                )
                .subquery()
            )

            customers_query = customers_query.filter(
                ~PartnerCustomer.id.in_(customers_with_commissions)
            )
        customers = customers_query.all()
        results = []

        for customer in customers:
            try:
                # Determine if this is a new customer (activated in last 30 days)
                is_new = (
                    customer.activated_at
                    and customer.activated_at >= datetime.now(timezone.utc) - timedelta(days=30)
                )
                result = self.calculate_customer_commission(
                    customer, partner, is_new_customer=is_new
                )
                results.append(result)

                # Create or update commission record
                if recalculate_all:
                    self.update_commission_record(db, customer.id, partner_id, result)
                else:
                    self.create_commission_record(db, customer.id, partner_id, result)

            except Exception as e:
                self._add_audit(
                    f"Error calculating commission for customer {customer.id}: {str(e)}"
                )
                continue

        return results
