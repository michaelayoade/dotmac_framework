"""
Comprehensive commission system for reseller partners
Handles calculation, tracking, and payment of commissions
"""

import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .db_models import CommissionStructure, Reseller, ResellerCommission
from .repositories import (
    ResellerCommissionRepository,
    ResellerCustomerRepository,
    ResellerRepository,
)


class CommissionCalculator:
    """Commission calculation engine with multiple structures"""

    @staticmethod
    def calculate_percentage_commission(base_amount: Decimal, commission_rate: Decimal) -> Decimal:
        """Calculate percentage-based commission"""
        commission = base_amount * commission_rate / 100
        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_flat_fee_commission(transaction_count: int, flat_fee_amount: Decimal) -> Decimal:
        """Calculate flat fee commission"""
        commission = transaction_count * flat_fee_amount
        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_tiered_commission(base_amount: Decimal, tier_rates: dict[str, Any]) -> Decimal:
        """Calculate tiered commission based on volume"""
        # Example tier structure:
        # {
        #   "tiers": [
        #     {"min": 0, "max": 1000, "rate": 5.0},
        #     {"min": 1000, "max": 5000, "rate": 7.5},
        #     {"min": 5000, "max": None, "rate": 10.0}
        #   ]
        # }

        commission = Decimal("0.00")
        remaining_amount = base_amount

        for tier in tier_rates.get("tiers", []):
            tier_min = Decimal(str(tier["min"]))
            tier_max = Decimal(str(tier["max"])) if tier["max"] else None
            tier_rate = Decimal(str(tier["rate"]))

            if remaining_amount <= 0:
                break

            if base_amount <= tier_min:
                continue

            # Calculate amount in this tier
            if tier_max:
                tier_amount = min(remaining_amount, tier_max - tier_min)
            else:
                tier_amount = remaining_amount

            # Calculate commission for this tier
            tier_commission = tier_amount * tier_rate / 100
            commission += tier_commission
            remaining_amount -= tier_amount

        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_commission(
        cls,
        reseller: Reseller,
        base_amount: Decimal,
        commission_type: str = "monthly_recurring",
    ) -> dict[str, Any]:
        """Calculate commission based on reseller's structure"""

        if reseller.commission_structure == CommissionStructure.PERCENTAGE:
            commission = cls.calculate_percentage_commission(base_amount, reseller.base_commission_rate or Decimal("0"))

        elif reseller.commission_structure == CommissionStructure.FLAT_FEE:
            # For flat fee, base_amount is treated as transaction count
            transaction_count = int(base_amount)
            commission = cls.calculate_flat_fee_commission(
                transaction_count, reseller.base_commission_rate or Decimal("0")
            )

        elif reseller.commission_structure == CommissionStructure.TIERED:
            commission = cls.calculate_tiered_commission(base_amount, reseller.tier_rates or {})

        else:
            commission = Decimal("0.00")

        return {
            "commission_amount": commission,
            "base_amount": base_amount,
            "commission_rate": reseller.base_commission_rate or Decimal("0"),
            "commission_structure": reseller.commission_structure,
            "calculation_method": reseller.commission_structure.value,
        }


class CommissionService:
    """Service for managing commission calculations and payments"""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.commission_repo = ResellerCommissionRepository(db, tenant_id)
        self.reseller_repo = ResellerRepository(db, tenant_id)
        self.customer_repo = ResellerCustomerRepository(db, tenant_id)
        self.calculator = CommissionCalculator()

    async def create_commission_record(
        self,
        reseller_id: str,
        commission_type: str,
        base_amount: Decimal,
        service_period_start: date,
        service_period_end: date,
        customer_id: Optional[UUID] = None,
        service_id: Optional[UUID] = None,
        additional_data: Optional[dict[str, Any]] = None,
    ) -> ResellerCommission:
        """Create a new commission record"""

        # Get reseller
        reseller = await self.reseller_repo.get_by_id(reseller_id)
        if not reseller:
            raise ValueError(f"Reseller {reseller_id} not found")

        # Calculate commission
        commission_calc = self.calculator.calculate_commission(reseller, base_amount, commission_type)

        # Generate commission ID
        commission_id = f"COM-{date.today().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"

        # Prepare commission data
        commission_data = {
            "reseller_id": reseller.id,
            "commission_id": commission_id,
            "commission_type": commission_type,
            "base_amount": base_amount,
            "commission_rate": commission_calc["commission_rate"],
            "commission_amount": commission_calc["commission_amount"],
            "commission_period": f"{service_period_start.strftime('%Y-%m')}-{service_period_end.strftime('%Y-%m')}",
            "service_period_start": service_period_start,
            "service_period_end": service_period_end,
            "earned_date": date.today(),
            "payment_status": "pending",
            "payment_due_date": date.today() + timedelta(days=30),  # Net 30
            "calculation_notes": f"Calculated using {commission_calc['calculation_method']} structure",
        }

        # Add optional fields
        if customer_id:
            commission_data["customer_id"] = customer_id
        if service_id:
            commission_data["service_id"] = service_id

        # Add additional data
        if additional_data:
            commission_data.update(additional_data)

        # Create commission record
        commission = await self.commission_repo.create(commission_data)
        await self.commission_repo.commit()

        return commission

    async def process_monthly_commissions(self, reseller_id: str, month: date) -> list[ResellerCommission]:
        """Process all monthly commissions for a reseller"""

        # Get reseller's customers
        reseller = await self.reseller_repo.get_by_id(reseller_id)
        if not reseller:
            raise ValueError(f"Reseller {reseller_id} not found")

        customers = await self.customer_repo.list_for_reseller(reseller.id, limit=1000)

        commissions_created = []

        for customer in customers:
            if customer.relationship_status != "active":
                continue

            # Calculate commission based on customer's MRR
            if customer.monthly_recurring_revenue > 0:
                commission = await self.create_commission_record(
                    reseller_id=reseller_id,
                    commission_type="monthly_recurring",
                    base_amount=customer.monthly_recurring_revenue,
                    service_period_start=date(month.year, month.month, 1),
                    service_period_end=self._get_month_end(month),
                    customer_id=customer.customer_id,
                    additional_data={
                        "service_type": customer.primary_service_type,
                        "description": f"Monthly commission for customer {customer.customer_id}",
                    },
                )
                commissions_created.append(commission)

        return commissions_created

    async def process_installation_commission(
        self,
        reseller_id: str,
        customer_id: UUID,
        installation_amount: Decimal,
        installation_date: date,
    ) -> ResellerCommission:
        """Process one-time installation commission"""

        commission = await self.create_commission_record(
            reseller_id=reseller_id,
            commission_type="installation",
            base_amount=installation_amount,
            service_period_start=installation_date,
            service_period_end=installation_date,
            customer_id=customer_id,
            additional_data={
                "description": f"Installation commission for customer {customer_id}",
                "installation_commission": True,
            },
        )

        return commission

    async def generate_commission_statement(
        self, reseller_id: str, period_start: date, period_end: date
    ) -> dict[str, Any]:
        """Generate commission statement for a period"""

        reseller = await self.reseller_repo.get_by_id(reseller_id)
        if not reseller:
            raise ValueError(f"Reseller {reseller_id} not found")

        # Get all commissions for the period
        # Note: This would require additional repository method in production
        # For now, we'll simulate the data structure

        statement = {
            "reseller_id": reseller_id,
            "company_name": reseller.company_name,
            "statement_period": {"start": period_start, "end": period_end},
            "generated_at": datetime.now(timezone.utc),
            "summary": {
                "total_commissions": Decimal("0.00"),
                "total_paid": Decimal("0.00"),
                "total_pending": Decimal("0.00"),
                "total_overdue": Decimal("0.00"),
                "commission_count": 0,
            },
            "commission_breakdown": {
                "monthly_recurring": {"count": 0, "amount": Decimal("0.00")},
                "installation": {"count": 0, "amount": Decimal("0.00")},
                "other": {"count": 0, "amount": Decimal("0.00")},
            },
            "payment_history": [],
            "outstanding_payments": [],
        }

        return statement

    async def mark_commission_paid(
        self,
        commission_id: str,
        payment_reference: str,
        payment_method: str = "bank_transfer",
        payment_date: Optional[date] = None,
    ) -> ResellerCommission:
        """Mark commission as paid"""

        commission = await self.commission_repo.mark_paid(commission_id, payment_reference, payment_method)

        if not commission:
            raise ValueError(f"Commission {commission_id} not found")

        await self.commission_repo.commit()
        return commission

    async def process_bulk_commission_payment(
        self,
        commission_ids: list[str],
        batch_reference: str,
        payment_method: str = "bank_transfer",
    ) -> dict[str, Any]:
        """Process bulk commission payment"""

        results = {
            "batch_reference": batch_reference,
            "processed": [],
            "failed": [],
            "total_amount": Decimal("0.00"),
        }

        for commission_id in commission_ids:
            try:
                commission = await self.mark_commission_paid(
                    commission_id, f"{batch_reference}-{commission_id}", payment_method
                )
                results["processed"].append(
                    {
                        "commission_id": commission_id,
                        "amount": commission.commission_amount,
                        "status": "paid",
                    }
                )
                results["total_amount"] += commission.commission_amount

            except Exception as e:
                results["failed"].append({"commission_id": commission_id, "error": str(e)})

        return results

    async def get_reseller_commission_summary(self, reseller_id: str, last_n_months: int = 12) -> dict[str, Any]:
        """Get reseller commission summary for last N months"""

        reseller = await self.reseller_repo.get_by_id(reseller_id)
        if not reseller:
            raise ValueError(f"Reseller {reseller_id} not found")

        # This would require additional repository methods in production
        # For now, return simulated summary
        summary = {
            "reseller_id": reseller_id,
            "company_name": reseller.company_name,
            "period_months": last_n_months,
            "commission_summary": {
                "total_earned": Decimal("15250.75"),
                "total_paid": Decimal("12850.50"),
                "total_pending": Decimal("2400.25"),
                "average_monthly": Decimal("1270.90"),
                "highest_month": Decimal("2150.00"),
                "lowest_month": Decimal("850.25"),
            },
            "performance_metrics": {
                "customers_added": 24,
                "customers_churned": 3,
                "net_customer_growth": 21,
                "average_customer_value": Decimal("85.50"),
            },
            "payment_status": {
                "on_time_payments": 10,
                "late_payments": 2,
                "payment_reliability_score": 83.3,
            },
        }

        return summary

    def _get_month_end(self, month_date: date) -> date:
        """Get the last day of the month"""
        if month_date.month == 12:
            next_month = date(month_date.year + 1, 1, 1)
        else:
            next_month = date(month_date.year, month_date.month + 1, 1)

        return next_month - timedelta(days=1)


class CommissionReportGenerator:
    """Generate various commission reports and analytics"""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.commission_service = CommissionService(db, tenant_id)

    async def generate_monthly_commission_report(self, month: date, tenant_id: Optional[str] = None) -> dict[str, Any]:
        """Generate comprehensive monthly commission report"""

        report = {
            "report_type": "monthly_commission_report",
            "report_period": month.strftime("%Y-%m"),
            "generated_at": datetime.now(timezone.utc),
            "summary": {
                "total_resellers": 0,
                "active_resellers": 0,
                "total_commissions": Decimal("0.00"),
                "total_customers": 0,
                "average_commission_per_reseller": Decimal("0.00"),
            },
            "reseller_breakdown": [],
            "top_performers": [],
            "commission_trends": {},
        }

        return report

    async def generate_reseller_performance_report(self, reseller_id: str, period_months: int = 6) -> dict[str, Any]:
        """Generate detailed reseller performance report"""

        summary = await self.commission_service.get_reseller_commission_summary(reseller_id, period_months)

        performance_report = {
            "report_type": "reseller_performance",
            "reseller_info": {
                "reseller_id": summary["reseller_id"],
                "company_name": summary["company_name"],
            },
            "performance_period": f"Last {period_months} months",
            "financial_performance": summary["commission_summary"],
            "customer_performance": summary["performance_metrics"],
            "payment_performance": summary["payment_status"],
            "recommendations": self._generate_performance_recommendations(summary),
            "generated_at": datetime.now(timezone.utc),
        }

        return performance_report

    def _generate_performance_recommendations(self, summary: dict[str, Any]) -> list[str]:
        """Generate performance recommendations based on data"""

        recommendations = []

        payment_score = summary["payment_status"]["payment_reliability_score"]
        if payment_score < 90:
            recommendations.append("Consider implementing automated payment processing to improve payment reliability")

        avg_monthly = summary["commission_summary"]["average_monthly"]
        if avg_monthly < Decimal("1000"):
            recommendations.append("Focus on customer acquisition to increase monthly commission potential")

        churn_rate = summary["performance_metrics"]["customers_churned"] / max(
            1, summary["performance_metrics"]["customers_added"]
        )
        if churn_rate > 0.15:  # 15% churn
            recommendations.append("Implement customer retention strategies to reduce churn rate")

        return recommendations


# Export classes
__all__ = ["CommissionCalculator", "CommissionService", "CommissionReportGenerator"]
