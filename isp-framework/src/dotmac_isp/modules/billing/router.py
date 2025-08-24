"""Billing API router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
import io

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from .schemas import (
    InvoiceResponse,
    InvoiceCreate,
    InvoiceUpdate,
    PaymentResponse,
    PaymentCreate,
    PaymentUpdate,
    CreditNote,
    CreditNoteCreate,
    Receipt,
    ReceiptCreate,
    TaxRate,
    TaxRateCreate,
    Subscription,
    SubscriptionCreate,
    BillingReport,
)
from .models import InvoiceStatus, PaymentStatus, PaymentMethod
from .service import InvoiceService, PaymentService, BillingService
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    ServiceError
)

router = APIRouter(tags=["billing"])
billing_router = router  # Standard export alias


# Invoice endpoints
@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new invoice."""
    try:
        service = InvoiceService(db, tenant_id)
        return await service.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[InvoiceStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List invoices with optional filtering."""
    try:
        service = InvoiceService(db, tenant_id)
        filters = {}
        if customer_id:
            filters['customer_id'] = customer_id
        if status:
            filters['status'] = status
        
        return await service.list(
            filters=filters,
            limit=limit,
            offset=skip
        )
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get invoice by ID."""
    try:
        service = InvoiceService(db, tenant_id)
        return await service.get_by_id_or_raise(invoice_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    data: InvoiceUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update invoice."""
    try:
        service = InvoiceService(db, tenant_id)
        return await service.update(invoice_id, data)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Payment endpoints
@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    data: PaymentCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new payment."""
    try:
        service = PaymentService(db, tenant_id)
        return await service.create(data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    invoice_id: Optional[UUID] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List payments with optional filtering."""
    try:
        service = PaymentService(db, tenant_id)
        filters = {}
        if invoice_id:
            filters['invoice_id'] = invoice_id
        if status:
            filters['status'] = status
        
        return await service.list(
            filters=filters,
            limit=limit,
            offset=skip
        )
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new invoice."""
    try:
        service = BillingService(db, tenant_id)
        invoice = await service.create_invoice(invoice_data)
        return invoice
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get invoice by ID."""
    try:
        service = BillingService(db, tenant_id)
        invoice = await service.get_invoice(invoice_id)
        return invoice
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/by-number/{invoice_number}", response_model=Invoice)
async def get_invoice_by_number(
    invoice_number: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get invoice by invoice number."""
    try:
        service = BillingService(db, tenant_id)
        invoice = await service.get_invoice_by_number(invoice_number)
        return invoice
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices/{invoice_id}/send", response_model=Invoice)
async def send_invoice(
    invoice_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Send invoice to customer."""
    try:
        service = BillingService(db, tenant_id)
        invoice = await service.send_invoice(invoice_id)
        return invoice
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices/{invoice_id}/void", response_model=Invoice)
async def void_invoice(
    invoice_id: UUID,
    reason: str = Query(..., description="Reason for voiding the invoice"),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Void an invoice."""
    try:
        service = BillingService(db, tenant_id)
        invoice = await service.void_invoice(invoice_id, reason)
        return invoice
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Invoice not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Payment endpoints
@router.get("/payments", response_model=List[Payment])
async def list_payments(
    customer_id: Optional[UUID] = Query(None),
    invoice_id: Optional[UUID] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
    payment_method: Optional[PaymentMethod] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List payments with optional filtering."""
    try:
        service = BillingService(db, tenant_id)
        payments = await service.list_payments(
            customer_id=customer_id,
            invoice_id=invoice_id,
            status=status,
            payment_method=payment_method,
            skip=skip,
            limit=limit,
        )
        return payments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def process_payment(
    payment_data: PaymentCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Process a payment."""
    try:
        service = BillingService(db, tenant_id)
        payment = await service.process_payment(payment_data)
        return payment
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/{payment_id}", response_model=Payment)
async def get_payment(
    payment_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get payment by ID."""
    try:
        service = BillingService(db, tenant_id)
        payment = await service.get_payment(payment_id)
        return payment
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Subscription endpoints
@router.post(
    "/subscriptions", response_model=Subscription, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new subscription."""
    try:
        service = BillingService(db, tenant_id)
        subscription = await service.create_subscription(subscription_data)
        return subscription
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{subscription_id}", response_model=Subscription)
async def get_subscription(
    subscription_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get subscription by ID."""
    try:
        service = BillingService(db, tenant_id)
        subscription = await service.get_subscription(subscription_id)
        return subscription
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Subscription not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscription_id}/cancel", response_model=Subscription)
async def cancel_subscription(
    subscription_id: UUID,
    cancel_date: Optional[date] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Cancel a subscription."""
    try:
        service = BillingService(db, tenant_id)
        subscription = await service.cancel_subscription(subscription_id, cancel_date)
        return subscription
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Subscription not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Credit Note endpoints
@router.post(
    "/credit-notes", response_model=CreditNote, status_code=status.HTTP_201_CREATED
)
async def create_credit_note(
    credit_note_data: CreditNoteCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a credit note."""
    try:
        service = BillingService(db, tenant_id)
        credit_note = await service.create_credit_note(credit_note_data)
        return credit_note
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Billing automation endpoints
@router.post("/billing/process-recurring")
async def process_recurring_billing(
    tenant_id: str = Depends(get_tenant_id_dependency), db: Session = Depends(get_db)
):
    """Process recurring billing for all subscriptions."""
    try:
        service = SubscriptionBillingService(db, tenant_id)
        results = await service.process_recurring_billing()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Customer billing endpoints
@router.get("/customers/{customer_id}/invoices", response_model=List[Invoice])
async def get_customer_invoices(
    customer_id: UUID,
    status: Optional[InvoiceStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get all invoices for a customer."""
    try:
        service = BillingService(db, tenant_id)
        invoices = await service.list_invoices(
            customer_id=customer_id, status=status, skip=skip, limit=limit
        )
        return invoices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/{customer_id}/payments", response_model=List[Payment])
async def get_customer_payments(
    customer_id: UUID,
    status: Optional[PaymentStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get all payments for a customer."""
    try:
        service = BillingService(db, tenant_id)
        payments = await service.list_payments(
            customer_id=customer_id, status=status, skip=skip, limit=limit
        )
        return payments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for billing module."""
    return {
        "status": "healthy",
        "module": "billing",
        "timestamp": datetime.utcnow().isoformat(),
    }


# PDF Generation endpoints
@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Download invoice as PDF."""
    try:
        service = BillingService(db, tenant_id)
        invoice = await service.get_invoice(invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Get customer data (this would typically come from customer service)
        customer_data = {
            'name': f'Customer {invoice.customer_id}',
            'address': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'zip': '12345',
            'email': 'customer@example.com'
        }
        
        pdf_data = await generate_invoice_pdf(invoice, customer_data)
        
        return Response(
            content=pdf_data,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/receipts/{receipt_id}/pdf")
async def download_receipt_pdf(
    receipt_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Download receipt as PDF."""
    try:
        service = BillingService(db, tenant_id)
        receipt = await service.get_receipt(receipt_id)
        
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        # Get customer data
        customer_data = {
            'name': receipt.customer_name,
            'email': 'customer@example.com'
        }
        
        pdf_data = await generate_receipt_pdf(receipt, customer_data)
        
        return Response(
            content=pdf_data,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="receipt_{receipt.receipt_number}.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# CSV Export endpoints
@router.get("/invoices/export/csv")
async def export_invoices_to_csv(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[InvoiceStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    include_line_items: bool = Query(False),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Export invoices to CSV."""
    try:
        service = BillingService(db, tenant_id)
        invoices = await service.list_invoices(
            customer_id=customer_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            skip=0,
            limit=10000  # Large limit for export
        )
        
        csv_data = await export_invoices_csv(invoices, include_line_items)
        
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="invoices_{datetime.utcnow().strftime("%Y%m%d")}.csv"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payments/export/csv")
async def export_payments_to_csv(
    customer_id: Optional[UUID] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Export payments to CSV."""
    try:
        service = BillingService(db, tenant_id)
        payments = await service.list_payments(
            customer_id=customer_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            skip=0,
            limit=10000
        )
        
        csv_data = await export_payments_csv(payments)
        
        return StreamingResponse(
            io.StringIO(csv_data),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="payments_{datetime.utcnow().strftime("%Y%m%d")}.csv"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# File Upload endpoints
@router.post("/invoices/{invoice_id}/attachments")
async def upload_invoice_attachment(
    invoice_id: UUID,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Upload attachment for an invoice."""
    try:
        # Verify invoice exists
        service = BillingService(db, tenant_id)
        invoice = await service.get_invoice(invoice_id)
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Upload file
        result = await file_upload_service.upload_invoice_attachment(
            file, tenant_id, str(invoice_id)
        )
        
        # Publish WebSocket event
        await event_publisher.publish_invoice_updated(
            tenant_id=tenant_id,
            customer_id=str(invoice.customer_id),
            invoice_id=str(invoice_id),
            invoice_data={
                'action': 'attachment_added',
                'attachment_filename': result['original_filename']
            }
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments/{payment_id}/receipts")
async def upload_payment_receipt(
    payment_id: UUID,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Upload receipt for a payment."""
    try:
        # Verify payment exists
        service = BillingService(db, tenant_id)
        payment = await service.get_payment(payment_id)
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Upload file
        result = await file_upload_service.upload_payment_receipt(
            file, tenant_id, str(payment_id)
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/{import_type}")
async def bulk_import(
    import_type: str,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Bulk import billing data from CSV file."""
    if import_type not in ['invoices', 'payments']:
        raise HTTPException(status_code=400, detail="Invalid import type")
    
    try:
        result = await file_upload_service.upload_bulk_import(
            file, tenant_id, import_type
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_path:path}")
async def get_uploaded_file(
    file_path: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
):
    """Download uploaded file."""
    try:
        content, content_type = await file_upload_service.get_file(file_path)
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{file_path.split("/")[-1]}"'
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket connection info endpoint
@router.get("/websocket/info")
async def websocket_info(
    tenant_id: str = Depends(get_tenant_id_dependency),
):
    """Get WebSocket connection information."""
    try:
        from .websocket_manager import websocket_manager
        
        connection_count = await websocket_manager.get_connection_count(tenant_id)
        health = await websocket_manager.health_check()
        
        return {
            'tenant_connections': connection_count,
            'websocket_health': health,
            'websocket_url': f'/ws/billing/{tenant_id}'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
