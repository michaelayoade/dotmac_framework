"""
Simple manual exchange rate service.

Provides functionality for managing customer currencies and manual exchange rates.
Uses DRY patterns from the shared framework.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from ..core.exchange_models import (
    CustomerCurrency,
    ExchangeRateHistory,
    ManualExchangeRate,
    MultiCurrencyPayment,
    calculate_converted_amount,
    calculate_variance,
)
from ..core.models import Customer, Payment
from ..schemas.exchange_schemas import (
    CustomerCurrencyCreate,
    ManualExchangeRateCreate,
    MultiCurrencyPaymentCreate,
    PaymentWithExchangeRateCreate,
)
from ...core.decorators import standard_exception_handler


class ExchangeRateService:
    """Service for managing manual exchange rates and multi-currency payments."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    # Customer Currency Management
    @standard_exception_handler
    async def add_customer_currency(
        self, 
        customer_id: UUID, 
        currency_data: CustomerCurrencyCreate
    ) -> CustomerCurrency:
        """Add a supported currency for a customer."""
        
        # Check if currency already exists for customer
        existing = (
            self.db.query(CustomerCurrency)
            .filter(
                CustomerCurrency.customer_id == customer_id,
                CustomerCurrency.currency_code == currency_data.currency_code
            )
            .first()
        )
        
        if existing:
            raise ValueError(f"Currency {currency_data.currency_code} already exists for customer")
        
        # If this is set as base currency, unset others
        if currency_data.is_base_currency:
            await self._unset_other_base_currencies(customer_id)
        
        # Create new currency
        customer_currency = CustomerCurrency(
            customer_id=customer_id,
            currency_code=currency_data.currency_code,
            is_base_currency=currency_data.is_base_currency,
            is_active=currency_data.is_active,
            display_name=currency_data.display_name,
            notes=currency_data.notes,
        )
        
        self.db.add(customer_currency)
        self.db.commit()
        self.db.refresh(customer_currency)
        
        return customer_currency
    
    @standard_exception_handler
    async def set_base_currency(
        self, 
        customer_id: UUID, 
        currency_code: str
    ) -> CustomerCurrency:
        """Set a customer's base currency."""
        
        # Find the currency configuration
        customer_currency = (
            self.db.query(CustomerCurrency)
            .filter(
                CustomerCurrency.customer_id == customer_id,
                CustomerCurrency.currency_code == currency_code,
                CustomerCurrency.is_active == True
            )
            .first()
        )
        
        if not customer_currency:
            raise ValueError(f"Currency {currency_code} not found for customer")
        
        # Unset other base currencies
        await self._unset_other_base_currencies(customer_id)
        
        # Set as base currency
        customer_currency.is_base_currency = True
        self.db.commit()
        
        return customer_currency
    
    @standard_exception_handler 
    async def get_customer_currencies(self, customer_id: UUID) -> List[CustomerCurrency]:
        """Get all currencies configured for a customer."""
        return (
            self.db.query(CustomerCurrency)
            .filter(CustomerCurrency.customer_id == customer_id)
            .order_by(CustomerCurrency.is_base_currency.desc(), CustomerCurrency.currency_code)
            .all()
        )
    
    @standard_exception_handler
    async def get_base_currency(self, customer_id: UUID) -> Optional[CustomerCurrency]:
        """Get customer's base currency."""
        return (
            self.db.query(CustomerCurrency)
            .filter(
                CustomerCurrency.customer_id == customer_id,
                CustomerCurrency.is_base_currency == True,
                CustomerCurrency.is_active == True
            )
            .first()
        )
    
    # Exchange Rate Management
    @standard_exception_handler
    async def set_exchange_rate(
        self,
        customer_currency_id: UUID,
        rate_data: ManualExchangeRateCreate,
        created_by: Optional[str] = None
    ) -> ManualExchangeRate:
        """Set a manual exchange rate."""
        
        # Validate customer currency exists
        customer_currency = (
            self.db.query(CustomerCurrency)
            .filter(CustomerCurrency.id == customer_currency_id)
            .first()
        )
        
        if not customer_currency:
            raise ValueError("Customer currency configuration not found")
        
        # Check for existing active rate for same currency pair
        existing_rate = (
            self.db.query(ManualExchangeRate)
            .filter(
                ManualExchangeRate.customer_currency_id == customer_currency_id,
                ManualExchangeRate.from_currency == rate_data.from_currency,
                ManualExchangeRate.to_currency == rate_data.to_currency,
                ManualExchangeRate.status == "active"
            )
            .first()
        )
        
        # Create new rate
        exchange_rate = ManualExchangeRate(
            customer_currency_id=customer_currency_id,
            from_currency=rate_data.from_currency,
            to_currency=rate_data.to_currency,
            exchange_rate=rate_data.exchange_rate,
            rate_date=rate_data.rate_date,
            valid_until=rate_data.valid_until,
            reference_invoice_id=rate_data.reference_invoice_id,
            reference_payment_id=rate_data.reference_payment_id,
            source=rate_data.source,
            notes=rate_data.notes,
            created_by=created_by or rate_data.created_by,
            status="active"
        )
        
        # If updating existing rate, create history record
        if existing_rate:
            await self._create_rate_history(
                existing_rate, 
                rate_data.exchange_rate, 
                created_by, 
                "Rate updated"
            )
            existing_rate.status = "expired"
        
        self.db.add(exchange_rate)
        self.db.commit()
        self.db.refresh(exchange_rate)
        
        return exchange_rate
    
    @standard_exception_handler
    async def get_exchange_rate(
        self,
        customer_id: UUID,
        from_currency: str,
        to_currency: str
    ) -> Optional[ManualExchangeRate]:
        """Get the current exchange rate for a currency pair."""
        
        return (
            self.db.query(ManualExchangeRate)
            .join(CustomerCurrency)
            .filter(
                CustomerCurrency.customer_id == customer_id,
                ManualExchangeRate.from_currency == from_currency,
                ManualExchangeRate.to_currency == to_currency,
                ManualExchangeRate.status == "active"
            )
            .filter(
                # Check if rate is still valid
                (ManualExchangeRate.valid_until.is_(None)) |
                (ManualExchangeRate.valid_until > datetime.now(timezone.utc))
            )
            .order_by(ManualExchangeRate.rate_date.desc())
            .first()
        )
    
    # Multi-Currency Payment Processing
    @standard_exception_handler
    async def process_multi_currency_payment(
        self,
        payment_data: PaymentWithExchangeRateCreate,
        created_by: Optional[str] = None
    ) -> Tuple[Payment, MultiCurrencyPayment]:
        """Process a payment with manual exchange rate conversion."""
        
        # Get customer's base currency
        base_currency = await self.get_base_currency(payment_data.customer_id)
        if not base_currency:
            raise ValueError("Customer base currency not configured")
        
        # Validate base currency matches
        if base_currency.currency_code != payment_data.base_currency:
            raise ValueError("Base currency mismatch")
        
        # Calculate converted amount
        converted_amount = calculate_converted_amount(
            payment_data.payment_amount,
            payment_data.exchange_rate,
            payment_data.payment_currency,
            payment_data.base_currency
        )
        
        # Create standard payment record
        payment = Payment(
            customer_id=payment_data.customer_id,
            invoice_id=payment_data.invoice_id,
            amount=converted_amount,  # Store in base currency
            currency=payment_data.base_currency,  # Base currency
            payment_method=payment_data.payment_method,
            notes=payment_data.payment_notes,
            status="completed"
        )
        
        self.db.add(payment)
        self.db.flush()  # Get payment ID
        
        # Create or get exchange rate record
        customer_currency = (
            self.db.query(CustomerCurrency)
            .filter(
                CustomerCurrency.customer_id == payment_data.customer_id,
                CustomerCurrency.currency_code == payment_data.payment_currency
            )
            .first()
        )
        
        if not customer_currency:
            # Auto-create currency if not exists
            customer_currency = CustomerCurrency(
                customer_id=payment_data.customer_id,
                currency_code=payment_data.payment_currency,
                is_base_currency=False,
                is_active=True
            )
            self.db.add(customer_currency)
            self.db.flush()
        
        # Create exchange rate for this transaction
        exchange_rate = ManualExchangeRate(
            customer_currency_id=customer_currency.id,
            from_currency=payment_data.payment_currency,
            to_currency=payment_data.base_currency,
            exchange_rate=payment_data.exchange_rate,
            reference_payment_id=payment.id,
            source=payment_data.rate_source or "Manual Entry",
            notes=payment_data.rate_notes,
            created_by=created_by,
            status="active"
        )
        
        self.db.add(exchange_rate)
        self.db.flush()
        
        # Create multi-currency payment record
        multi_currency_payment = MultiCurrencyPayment(
            payment_id=payment.id,
            exchange_rate_id=exchange_rate.id,
            original_amount=payment_data.payment_amount,
            original_currency=payment_data.payment_currency,
            converted_amount=converted_amount,
            converted_currency=payment_data.base_currency,
            conversion_rate=payment_data.exchange_rate,
            is_reconciled=True  # Manual entry is considered reconciled
        )
        
        self.db.add(multi_currency_payment)
        self.db.commit()
        
        # Refresh objects
        self.db.refresh(payment)
        self.db.refresh(multi_currency_payment)
        
        return payment, multi_currency_payment
    
    @standard_exception_handler
    async def convert_amount(
        self,
        customer_id: UUID,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Tuple[Decimal, Optional[ManualExchangeRate]]:
        """Convert amount using customer's exchange rate."""
        
        if from_currency == to_currency:
            return amount, None
        
        # Get exchange rate
        exchange_rate = await self.get_exchange_rate(
            customer_id, 
            from_currency, 
            to_currency
        )
        
        if not exchange_rate:
            raise ValueError(f"No exchange rate found for {from_currency} to {to_currency}")
        
        # Calculate converted amount
        converted_amount = calculate_converted_amount(
            amount,
            exchange_rate.exchange_rate,
            from_currency,
            to_currency
        )
        
        return converted_amount, exchange_rate
    
    # Utility Methods
    async def _unset_other_base_currencies(self, customer_id: UUID):
        """Unset base currency flag from other customer currencies."""
        (
            self.db.query(CustomerCurrency)
            .filter(
                CustomerCurrency.customer_id == customer_id,
                CustomerCurrency.is_base_currency == True
            )
            .update({"is_base_currency": False})
        )
    
    async def _create_rate_history(
        self,
        exchange_rate: ManualExchangeRate,
        new_rate: Decimal,
        changed_by: Optional[str],
        reason: str
    ):
        """Create exchange rate history record."""
        history = ExchangeRateHistory(
            exchange_rate_id=exchange_rate.id,
            old_rate=exchange_rate.exchange_rate,
            new_rate=new_rate,
            change_reason=reason,
            changed_by=changed_by or "System"
        )
        self.db.add(history)