"""Tax service for calculating taxes on invoices."""

from typing import Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dotmac_isp.modules.billing.models import TaxRate, TaxType


class TaxService:
    """Service for tax calculations and management."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def calculate_tax(
        self,
        amount: Decimal,
        customer_location: dict,
        tenant_id: str,
        tax_type: Optional[TaxType] = None
    ) -> Decimal:
        """Calculate tax for an amount based on customer location."""
        tax_rate = await self.get_applicable_tax_rate(
            customer_location, tenant_id, tax_type
        )
        
        if tax_rate:
            return amount * tax_rate.rate
        
        return Decimal('0.00')
    
    async def get_applicable_tax_rate(
        self,
        location: dict,
        tenant_id: str,
        tax_type: Optional[TaxType] = None
    ) -> Optional[TaxRate]:
        """Get the applicable tax rate for a location."""
        query = select(TaxRate).where(
            TaxRate.tenant_id == tenant_id,
            TaxRate.is_active == True
        )
        
        # Add location filters if provided
        if location.get('country_code'):
            query = query.where(TaxRate.country_code == location['country_code'])
        
        if location.get('state_province'):
            query = query.where(TaxRate.state_province == location['state_province'])
        
        if location.get('city'):
            query = query.where(TaxRate.city == location['city'])
        
        if tax_type:
            query = query.where(TaxRate.tax_type == tax_type)
        
        # Order by most specific match first
        query = query.order_by(TaxRate.city.desc(), TaxRate.state_province.desc())
        
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def create_tax_rate(
        self,
        name: str,
        rate: Decimal,
        tax_type: TaxType,
        tenant_id: str,
        location: Optional[dict] = None
    ) -> TaxRate:
        """Create a new tax rate."""
        tax_rate = TaxRate(
            name=name,
            rate=rate,
            tax_type=tax_type,
            tenant_id=tenant_id,
            country_code=location.get('country_code') if location else None,
            state_province=location.get('state_province') if location else None,
            city=location.get('city') if location else None,
            postal_code=location.get('postal_code') if location else None,
            effective_from=location.get('effective_from') if location else date.today()
        )
        
        self.db_session.add(tax_rate)
        await self.db_session.commit()
        await self.db_session.refresh(tax_rate)
        
        return tax_rate
    
    async def get_tax_rates_by_location(
        self,
        tenant_id: str,
        country_code: Optional[str] = None,
        state_province: Optional[str] = None
    ) -> List[TaxRate]:
        """Get all tax rates for a specific location."""
        query = select(TaxRate).where(
            TaxRate.tenant_id == tenant_id,
            TaxRate.is_active == True
        )
        
        if country_code:
            query = query.where(TaxRate.country_code == country_code)
        
        if state_province:
            query = query.where(TaxRate.state_province == state_province)
        
        result = await self.db_session.execute(query)
        return result.scalars().all()