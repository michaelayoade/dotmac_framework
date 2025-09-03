"""
API routes for multi-currency exchange rate management.

Provides REST endpoints for managing customer currencies and exchange rates.
Uses DRY patterns with RouterFactory and standard exception handling.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.router_factory import RouterFactory
from ...core.decorators import standard_exception_handler
from ..core.exchange_models import CustomerCurrency, ManualExchangeRate
from ..schemas.exchange_schemas import (
    CustomerCurrencyCreate,
    CustomerCurrencyListResponse,
    CustomerCurrencyResponse,
    CustomerCurrencyUpdate,
    CurrencyConversionRequest,
    CurrencyConversionResponse,
    ExchangeRateListResponse,
    ManualExchangeRateCreate,
    ManualExchangeRateResponse,
    ManualExchangeRateUpdate,
    MultiCurrencyPaymentListResponse,
    PaymentWithExchangeRateCreate,
)
from ..services.exchange_service import ExchangeRateService


# Create router using DRY RouterFactory pattern
router_factory = RouterFactory(
    prefix="/exchange",
    tags=["Multi-Currency Exchange"],
    dependencies=[]
)

router = router_factory.create_router()


def get_exchange_service(db: AsyncSession = Depends(get_db)) -> ExchangeRateService:
    """Dependency to get exchange rate service."""
    return ExchangeRateService(db)


# Customer Currency Management Routes
@router.post(
    "/customers/{customer_id}/currencies",
    response_model=CustomerCurrencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add currency for customer",
    description="Add a new supported currency for a customer"
)
@standard_exception_handler
async def add_customer_currency(
    customer_id: UUID,
    currency_data: CustomerCurrencyCreate,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> CustomerCurrencyResponse:
    """Add a supported currency for a customer."""
    
    # Set customer_id from path parameter
    currency_data.customer_id = customer_id
    
    try:
        customer_currency = await service.add_customer_currency(customer_id, currency_data)
        return CustomerCurrencyResponse.model_validate(customer_currency)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/customers/{customer_id}/currencies",
    response_model=CustomerCurrencyListResponse,
    summary="Get customer currencies",
    description="Get all currencies configured for a customer"
)
@standard_exception_handler
async def get_customer_currencies(
    customer_id: UUID,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> CustomerCurrencyListResponse:
    """Get all currencies configured for a customer."""
    
    currencies = await service.get_customer_currencies(customer_id)
    
    return CustomerCurrencyListResponse(
        currencies=[CustomerCurrencyResponse.model_validate(c) for c in currencies],
        total_count=len(currencies)
    )


@router.patch(
    "/customers/{customer_id}/currencies/{currency_id}",
    response_model=CustomerCurrencyResponse,
    summary="Update customer currency",
    description="Update currency configuration for a customer"
)
@standard_exception_handler
async def update_customer_currency(
    customer_id: UUID,
    currency_id: UUID,
    update_data: CustomerCurrencyUpdate,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> CustomerCurrencyResponse:
    """Update customer currency configuration."""
    
    try:
        # Implementation would update the currency configuration
        # For now, return a placeholder response
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Update functionality not yet implemented"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/customers/{customer_id}/currencies/{currency_id}/set-base",
    response_model=CustomerCurrencyResponse,
    summary="Set base currency",
    description="Set a currency as the customer's base currency"
)
@standard_exception_handler
async def set_base_currency(
    customer_id: UUID,
    currency_id: UUID,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> CustomerCurrencyResponse:
    """Set a currency as the customer's base currency."""
    
    try:
        # First get the currency to find the currency_code
        currencies = await service.get_customer_currencies(customer_id)
        target_currency = next((c for c in currencies if c.id == currency_id), None)
        
        if not target_currency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Currency configuration not found"
            )
        
        customer_currency = await service.set_base_currency(
            customer_id, 
            target_currency.currency_code
        )
        return CustomerCurrencyResponse.model_validate(customer_currency)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Exchange Rate Management Routes
@router.post(
    "/currencies/{customer_currency_id}/rates",
    response_model=ManualExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set exchange rate",
    description="Set a manual exchange rate for a currency pair"
)
@standard_exception_handler
async def set_exchange_rate(
    customer_currency_id: UUID,
    rate_data: ManualExchangeRateCreate,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> ManualExchangeRateResponse:
    """Set a manual exchange rate."""
    
    # Set customer_currency_id from path parameter
    rate_data.customer_currency_id = customer_currency_id
    
    try:
        exchange_rate = await service.set_exchange_rate(
            customer_currency_id, 
            rate_data,
            created_by="API_USER"  # In real implementation, get from auth context
        )
        return ManualExchangeRateResponse.model_validate(exchange_rate)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/customers/{customer_id}/rates",
    response_model=ExchangeRateListResponse,
    summary="Get exchange rates",
    description="Get all active exchange rates for a customer"
)
@standard_exception_handler
async def get_customer_exchange_rates(
    customer_id: UUID,
    from_currency: Optional[str] = None,
    to_currency: Optional[str] = None,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> ExchangeRateListResponse:
    """Get exchange rates for a customer."""
    
    # Implementation would fetch rates with optional filters
    # For now, return empty list
    return ExchangeRateListResponse(
        exchange_rates=[],
        total_count=0
    )


@router.get(
    "/customers/{customer_id}/rates/{from_currency}/{to_currency}",
    response_model=ManualExchangeRateResponse,
    summary="Get specific exchange rate",
    description="Get the current exchange rate for a specific currency pair"
)
@standard_exception_handler
async def get_exchange_rate(
    customer_id: UUID,
    from_currency: str,
    to_currency: str,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> ManualExchangeRateResponse:
    """Get exchange rate for a specific currency pair."""
    
    try:
        exchange_rate = await service.get_exchange_rate(
            customer_id, 
            from_currency.upper(), 
            to_currency.upper()
        )
        
        if not exchange_rate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exchange rate not found for {from_currency} to {to_currency}"
            )
        
        return ManualExchangeRateResponse.model_validate(exchange_rate)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Multi-Currency Payment Routes
@router.post(
    "/payments/multi-currency",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Process multi-currency payment",
    description="Process a payment with manual exchange rate conversion"
)
@standard_exception_handler
async def process_multi_currency_payment(
    payment_data: PaymentWithExchangeRateCreate,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> dict:
    """Process a multi-currency payment."""
    
    try:
        payment, multi_currency_payment = await service.process_multi_currency_payment(
            payment_data,
            created_by="API_USER"  # In real implementation, get from auth context
        )
        
        return {
            "payment_id": str(payment.id),
            "multi_currency_payment_id": str(multi_currency_payment.id),
            "original_amount": float(multi_currency_payment.original_amount),
            "original_currency": multi_currency_payment.original_currency,
            "converted_amount": float(multi_currency_payment.converted_amount),
            "converted_currency": multi_currency_payment.converted_currency,
            "conversion_rate": float(multi_currency_payment.conversion_rate),
            "status": "completed"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/customers/{customer_id}/payments/multi-currency",
    response_model=MultiCurrencyPaymentListResponse,
    summary="Get multi-currency payments",
    description="Get multi-currency payment history for a customer"
)
@standard_exception_handler
async def get_multi_currency_payments(
    customer_id: UUID,
    skip: int = 0,
    limit: int = 50,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> MultiCurrencyPaymentListResponse:
    """Get multi-currency payment history."""
    
    # Implementation would fetch multi-currency payments
    # For now, return empty list
    return MultiCurrencyPaymentListResponse(
        payments=[],
        total_count=0
    )


# Utility Routes
@router.post(
    "/convert",
    response_model=CurrencyConversionResponse,
    summary="Convert currency amount",
    description="Convert an amount using customer's exchange rate"
)
@standard_exception_handler
async def convert_currency(
    conversion_request: CurrencyConversionRequest,
    customer_id: UUID,
    service: ExchangeRateService = Depends(get_exchange_service),
) -> CurrencyConversionResponse:
    """Convert currency amount using customer's exchange rate."""
    
    try:
        converted_amount, exchange_rate = await service.convert_amount(
            customer_id,
            conversion_request.amount,
            conversion_request.from_currency,
            conversion_request.to_currency
        )
        
        return CurrencyConversionResponse(
            original_amount=conversion_request.amount,
            original_currency=conversion_request.from_currency,
            converted_amount=converted_amount,
            converted_currency=conversion_request.to_currency,
            exchange_rate=exchange_rate.exchange_rate if exchange_rate else conversion_request.exchange_rate,
            conversion_date=datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Import the shared database dependency
from ...database import get_db


# Export the router for inclusion in main app
__all__ = ["router"]