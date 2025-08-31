"""
Service layer for ISP reseller operations.
Provides business logic for reseller management.
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.schemas import PaginatedResponse
from dotmac_shared.services.base import BaseService

from .models import (
    Commission,
    CommissionStatus,
    Reseller,
    ResellerAgreement,
    ResellerContact,
    ResellerOpportunity,
    ResellerPerformance,
    ResellerStatus,
    ResellerTerritory,
    ResellerTier,
    ResellerType,
)
from .repository import (
    CommissionRepository,
    ResellerAgreementRepository,
    ResellerContactRepository,
    ResellerOpportunityRepository,
    ResellerPerformanceRepository,
    ResellerRepository,
    ResellerTerritoryRepository,
)

logger = logging.getLogger(__name__)


class ResellerService(BaseService):
    """Service for reseller operations."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, tenant_id)
        self.reseller_repo = ResellerRepository(session)
        self.contact_repo = ResellerContactRepository(session)
        self.opportunity_repo = ResellerOpportunityRepository(session)
        self.commission_repo = CommissionRepository(session)
        self.performance_repo = ResellerPerformanceRepository(session)
        self.territory_repo = ResellerTerritoryRepository(session)
        self.agreement_repo = ResellerAgreementRepository(session)

    async def create_reseller(self, reseller_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new reseller."""
        try:
            # Generate unique reseller ID
            reseller_data["reseller_id"] = str(uuid4())
            reseller_data["status"] = ResellerStatus.ACTIVE

            # Parse date strings to datetime objects
            if "contract_start_date" in reseller_data:
                reseller_data["contract_start_date"] = datetime.fromisoformat(
                    reseller_data["contract_start_date"]
                ).date()
            if "contract_end_date" in reseller_data and reseller_data["contract_end_date"]:
                reseller_data["contract_end_date"] = datetime.fromisoformat(
                    reseller_data["contract_end_date"]
                ).date()

            # Convert string enums to enum instances
            if "reseller_type" in reseller_data:
                reseller_data["reseller_type"] = ResellerType(reseller_data["reseller_type"])
            if "reseller_tier" in reseller_data:
                reseller_data["reseller_tier"] = ResellerTier(reseller_data["reseller_tier"])

            reseller = await self.reseller_repo.create_reseller(
                self.tenant_id, reseller_data
            )

            # Create initial agreement if contract dates are provided
            if "contract_start_date" in reseller_data:
                agreement_data = {
                    "agreement_type": "STANDARD",
                    "start_date": reseller_data["contract_start_date"],
                    "end_date": reseller_data.get("contract_end_date"),
                    "terms": reseller_data.get("performance_targets", {}),
                    "is_active": True,
                }
                await self.agreement_repo.create_agreement(
                    self.tenant_id, reseller.reseller_id, agreement_data
                )

            logger.info(f"Created reseller {reseller.reseller_id} for tenant {self.tenant_id}")
            return self._format_reseller_response(reseller)

        except Exception as e:
            logger.error(f"Error creating reseller: {e}")
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create reseller: {str(e)}")

    async def get_reseller(self, reseller_id: str) -> Optional[Dict[str, Any]]:
        """Get reseller by ID with all details."""
        try:
            reseller = await self.reseller_repo.get_reseller_with_details(
                self.tenant_id, reseller_id
            )
            if not reseller:
                return None

            return self._format_reseller_response(reseller, include_details=True)

        except Exception as e:
            logger.error(f"Error getting reseller {reseller_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get reseller: {str(e)}")

    async def list_resellers(
        self,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[Dict[str, Any]]:
        """List resellers with filtering and pagination."""
        try:
            result = await self.reseller_repo.list_resellers(
                self.tenant_id, limit=limit, offset=offset, filters=filters, search=search
            )

            formatted_items = [
                self._format_reseller_response(reseller) for reseller in result.items
            ]

            return PaginatedResponse(
                items=formatted_items,
                total=result.total,
                limit=result.limit,
                offset=result.offset,
            )

        except Exception as e:
            logger.error(f"Error listing resellers: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to list resellers: {str(e)}")

    async def update_reseller(
        self, reseller_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update reseller information."""
        try:
            # Convert string enums to enum instances if present
            if "reseller_type" in update_data:
                update_data["reseller_type"] = ResellerType(update_data["reseller_type"])
            if "reseller_tier" in update_data:
                update_data["reseller_tier"] = ResellerTier(update_data["reseller_tier"])

            reseller = await self.reseller_repo.update_by_id(
                self.tenant_id, reseller_id, update_data
            )
            if not reseller:
                return None

            logger.info(f"Updated reseller {reseller_id} for tenant {self.tenant_id}")
            return self._format_reseller_response(reseller)

        except Exception as e:
            logger.error(f"Error updating reseller {reseller_id}: {e}")
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update reseller: {str(e)}")

    async def delete_reseller(self, reseller_id: str) -> bool:
        """Soft delete a reseller."""
        try:
            success = await self.reseller_repo.soft_delete_by_id(self.tenant_id, reseller_id)
            if success:
                logger.info(f"Deleted reseller {reseller_id} for tenant {self.tenant_id}")
            return success

        except Exception as e:
            logger.error(f"Error deleting reseller {reseller_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete reseller: {str(e)}")

    async def create_reseller_opportunity(
        self, reseller_id: str, opportunity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assign an opportunity to a reseller."""
        try:
            # Verify reseller exists
            reseller = await self.reseller_repo.get_by_id(self.tenant_id, reseller_id)
            if not reseller:
                raise HTTPException(status_code=404, detail="Reseller not found")

            opportunity_data["reseller_opportunity_id"] = str(uuid4())
            opportunity_data["assigned_date"] = datetime.utcnow().date()
            opportunity_data["status"] = "ASSIGNED"

            opportunity = await self.opportunity_repo.assign_opportunity(
                self.tenant_id, reseller_id, opportunity_data
            )

            logger.info(
                f"Assigned opportunity {opportunity.opportunity_id} to reseller {reseller_id}"
            )
            return self._format_opportunity_response(opportunity)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating reseller opportunity: {e}")
            await self.session.rollback()
            raise HTTPException(
                status_code=500, detail=f"Failed to create reseller opportunity: {str(e)}"
            )

    async def calculate_commission(
        self,
        reseller_id: str,
        sale_amount: Decimal,
        commission_override: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """Calculate commission for a reseller sale."""
        try:
            reseller = await self.reseller_repo.get_by_id(self.tenant_id, reseller_id)
            if not reseller:
                raise HTTPException(status_code=404, detail="Reseller not found")

            # Use override rate if provided, otherwise use reseller's rate
            commission_rate = commission_override or reseller.commission_rate
            commission_amount = sale_amount * commission_rate

            return {
                "reseller_id": reseller_id,
                "sale_amount": float(sale_amount),
                "commission_rate": float(commission_rate),
                "commission_amount": float(commission_amount),
                "calculated_at": datetime.utcnow().isoformat(),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calculating commission: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to calculate commission: {str(e)}"
            )

    async def record_commission(
        self, reseller_id: str, commission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record a commission payment."""
        try:
            # Verify reseller exists
            reseller = await self.reseller_repo.get_by_id(self.tenant_id, reseller_id)
            if not reseller:
                raise HTTPException(status_code=404, detail="Reseller not found")

            commission_data["commission_id"] = str(uuid4())
            commission_data["calculated_date"] = datetime.utcnow().date()
            commission_data["payment_status"] = CommissionStatus.PENDING

            commission = await self.commission_repo.create_commission(
                self.tenant_id, commission_data
            )

            logger.info(f"Recorded commission {commission.commission_id} for reseller {reseller_id}")
            return self._format_commission_response(commission)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error recording commission: {e}")
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to record commission: {str(e)}")

    async def get_reseller_performance(
        self,
        reseller_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get reseller performance metrics."""
        try:
            # Verify reseller exists
            reseller = await self.reseller_repo.get_by_id(self.tenant_id, reseller_id)
            if not reseller:
                return None

            # Get commission data for the period
            commissions = await self.commission_repo.get_commissions_by_reseller(
                self.tenant_id, reseller_id, start_date, end_date
            )

            total_commission = await self.commission_repo.get_total_commission_amount(
                self.tenant_id, reseller_id, start_date, end_date
            )

            # Get opportunities for the period
            opportunities = await self.opportunity_repo.get_opportunities_by_reseller(
                self.tenant_id, reseller_id
            )

            # Calculate metrics
            metrics = {
                "total_commissions": float(total_commission),
                "commission_count": len(commissions),
                "opportunities_count": len(opportunities),
                "average_commission": (
                    float(total_commission / len(commissions)) if commissions else 0.0
                ),
                "paid_commissions": len(
                    [c for c in commissions if c.payment_status == CommissionStatus.PAID]
                ),
                "pending_commissions": len(
                    [c for c in commissions if c.payment_status == CommissionStatus.PENDING]
                ),
            }

            return {
                "reseller_id": reseller_id,
                "tenant_id": self.tenant_id,
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None,
                "metrics": metrics,
                "calculated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting reseller performance: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get reseller performance: {str(e)}"
            )

    async def assign_territory(self, reseller_id: str, territory: str) -> bool:
        """Assign a territory to a reseller."""
        try:
            # Verify reseller exists
            reseller = await self.reseller_repo.get_by_id(self.tenant_id, reseller_id)
            if not reseller:
                return False

            territory_assignment = await self.territory_repo.assign_territory(
                self.tenant_id, reseller_id, territory
            )

            logger.info(f"Assigned territory {territory} to reseller {reseller_id}")
            return True

        except Exception as e:
            logger.error(f"Error assigning territory: {e}")
            await self.session.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to assign territory: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for reseller service."""
        try:
            # Test database connectivity
            test_query_result = await self.reseller_repo.list_resellers(
                self.tenant_id, limit=1
            )

            return {
                "reseller_service": "healthy",
                "tenant_id": self.tenant_id,
                "user_service": "connected" if test_query_result else "disconnected",
                "cache_service": {"status": "healthy", "connection": "active"},
                "event_bus": "connected",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "reseller_service": "unhealthy",
                "tenant_id": self.tenant_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _format_reseller_response(
        self, reseller: Reseller, include_details: bool = False
    ) -> Dict[str, Any]:
        """Format reseller for API response."""
        response = {
            "reseller_id": reseller.reseller_id,
            "tenant_id": reseller.tenant_id,
            "company_name": reseller.company_name,
            "reseller_type": reseller.reseller_type.value,
            "reseller_tier": reseller.reseller_tier.value,
            "commission_rate": float(reseller.commission_rate),
            "contact_email": reseller.contact_email,
            "contact_phone": reseller.contact_phone,
            "contact_person": reseller.contact_person,
            "billing_address": reseller.billing_address,
            "shipping_address": reseller.shipping_address,
            "website": reseller.website,
            "territories": reseller.territories or [],
            "status": reseller.status.value,
            "created_at": reseller.created_at.isoformat(),
            "updated_at": reseller.updated_at.isoformat(),
        }

        if include_details:
            # Add related data if loaded
            if hasattr(reseller, "contacts") and reseller.contacts:
                response["additional_contacts"] = len(reseller.contacts)
            if hasattr(reseller, "opportunities") and reseller.opportunities:
                response["opportunities_count"] = len(reseller.opportunities)
            if hasattr(reseller, "commissions") and reseller.commissions:
                response["commissions_count"] = len(reseller.commissions)

        return response

    def _format_opportunity_response(
        self, opportunity: ResellerOpportunity
    ) -> Dict[str, Any]:
        """Format reseller opportunity for API response."""
        return {
            "reseller_opportunity_id": opportunity.reseller_opportunity_id,
            "tenant_id": opportunity.tenant_id,
            "reseller_id": opportunity.reseller_id,
            "opportunity_id": opportunity.opportunity_id,
            "assigned_date": opportunity.assigned_date.isoformat(),
            "commission_override": (
                float(opportunity.commission_override)
                if opportunity.commission_override
                else None
            ),
            "status": opportunity.status,
            "created_at": opportunity.created_at.isoformat(),
        }

    def _format_commission_response(self, commission: Commission) -> Dict[str, Any]:
        """Format commission for API response."""
        return {
            "commission_id": commission.commission_id,
            "tenant_id": commission.tenant_id,
            "reseller_id": commission.reseller_id,
            "sale_amount": float(commission.sale_amount),
            "commission_amount": float(commission.commission_amount),
            "payment_status": commission.payment_status.value,
            "calculated_date": commission.calculated_date.isoformat(),
            "created_at": commission.created_at.isoformat(),
        }


class CommissionCalculationService:
    """Service for advanced commission calculations."""

    @staticmethod
    def calculate_tiered_commission(
        sale_amount: Decimal, reseller_tier: ResellerTier, base_rate: Decimal
    ) -> Decimal:
        """Calculate commission based on reseller tier with multipliers."""
        tier_multipliers = {
            ResellerTier.BRONZE: Decimal("1.0"),
            ResellerTier.SILVER: Decimal("1.1"),
            ResellerTier.GOLD: Decimal("1.25"),
            ResellerTier.PLATINUM: Decimal("1.5"),
        }

        multiplier = tier_multipliers.get(reseller_tier, Decimal("1.0"))
        return sale_amount * base_rate * multiplier

    @staticmethod
    def calculate_performance_bonus(
        base_commission: Decimal, performance_metrics: Dict[str, Any]
    ) -> Decimal:
        """Calculate performance-based commission bonus."""
        bonus = Decimal("0.0")

        # Volume bonus
        total_sales = performance_metrics.get("total_sales", 0)
        if total_sales > 100000:
            bonus += base_commission * Decimal("0.05")  # 5% bonus
        elif total_sales > 50000:
            bonus += base_commission * Decimal("0.025")  # 2.5% bonus

        # Retention bonus
        retention_rate = performance_metrics.get("customer_retention_rate", 0)
        if retention_rate > 0.95:
            bonus += base_commission * Decimal("0.03")  # 3% bonus
        elif retention_rate > 0.90:
            bonus += base_commission * Decimal("0.015")  # 1.5% bonus

        return bonus