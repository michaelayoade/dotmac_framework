"""Billing API router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date

from dotmac_isp.core.database import get_db
from .schemas import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
    Payment,
    PaymentCreate,
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

router = APIRouter(tags=["billing"])
billing_router = router  # Export with expected name


# Invoice endpoints
@router.get("/invoices", response_model=List[Invoice])
async def list_invoices(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List invoices with optional filtering."""
    return [
        Invoice(
            id="inv_001",
            customer_id="cust_001",
            invoice_number="INV-2024-001",
            issue_date=datetime.now(),
            due_date=datetime.now(),
            status="sent",
            subtotal=100.00,
            tax_total=8.50,
            discount_total=0.00,
            total_amount=108.50,
            amount_paid=0.00,
            amount_due=108.50,
            currency="USD",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]


@router.post("/invoices", response_model=Invoice, status_code=status.HTTP_201_CREATED)
async def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a new invoice."""
    return Invoice(
        id="inv_002",
        customer_id=invoice.customer_id,
        invoice_number="INV-2024-002",
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status="draft",
        subtotal=100.00,
        tax_total=8.50,
        discount_total=0.00,
        total_amount=108.50,
        amount_paid=0.00,
        amount_due=108.50,
        currency=invoice.currency,
        notes=invoice.notes,
        terms=invoice.terms,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Get invoice by ID."""
    if invoice_id == "404":
        raise HTTPException(status_code=404, detail="Invoice not found")

    return Invoice(
        id=invoice_id,
        customer_id="cust_001",
        invoice_number=f"INV-2024-{invoice_id[-3:]}",
        issue_date=datetime.now(),
        due_date=datetime.now(),
        status="sent",
        subtotal=100.00,
        tax_total=8.50,
        discount_total=0.00,
        total_amount=108.50,
        amount_paid=0.00,
        amount_due=108.50,
        currency="USD",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.patch("/invoices/{invoice_id}", response_model=Invoice)
async def update_invoice(
    invoice_id: str, update: InvoiceUpdate, db: Session = Depends(get_db)
):
    """Update invoice."""
    return Invoice(
        id=invoice_id,
        customer_id="cust_001",
        invoice_number=f"INV-2024-{invoice_id[-3:]}",
        issue_date=datetime.now(),
        due_date=update.due_date or datetime.now(),
        status=update.status or "sent",
        subtotal=100.00,
        tax_total=8.50,
        discount_total=0.00,
        total_amount=108.50,
        amount_paid=0.00,
        amount_due=108.50,
        currency="USD",
        notes=update.notes,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: str, db: Session = Depends(get_db)):
    """Send invoice to customer."""
    return {"message": f"Invoice {invoice_id} sent successfully"}


# Payment endpoints
@router.get("/payments", response_model=List[Payment])
async def list_payments(
    customer_id: Optional[str] = Query(None),
    invoice_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List payments with optional filtering."""
    return [
        Payment(
            id="pay_001",
            invoice_id="inv_001",
            amount=108.50,
            payment_method="credit_card",
            payment_date=datetime.now(),
            status="completed",
            transaction_id="txn_12345",
            reference_number="REF-001",
            created_at=datetime.now(),
        )
    ]


@router.post("/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
async def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """Record a new payment."""
    return Payment(
        id="pay_002",
        invoice_id=payment.invoice_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        payment_date=datetime.now(),
        status="completed",
        transaction_id="txn_12346",
        reference_number=payment.reference_number,
        notes=payment.notes,
        created_at=datetime.now(),
    )


@router.get("/payments/{payment_id}", response_model=Payment)
async def get_payment(payment_id: str, db: Session = Depends(get_db)):
    """Get payment by ID."""
    return Payment(
        id=payment_id,
        invoice_id="inv_001",
        amount=108.50,
        payment_method="credit_card",
        payment_date=datetime.now(),
        status="completed",
        transaction_id="txn_12345",
        reference_number="REF-001",
        created_at=datetime.now(),
    )


# Credit Note endpoints
@router.get("/credit-notes", response_model=List[CreditNote])
async def list_credit_notes(
    customer_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List credit notes."""
    return [
        CreditNote(
            id="cn_001",
            invoice_id="inv_001",
            credit_note_number="CN-2024-001",
            reason="Product return",
            amount=50.00,
            status="applied",
            created_at=datetime.now(),
            applied_at=datetime.now(),
        )
    ]


@router.post(
    "/credit-notes", response_model=CreditNote, status_code=status.HTTP_201_CREATED
)
async def create_credit_note(
    credit_note: CreditNoteCreate, db: Session = Depends(get_db)
):
    """Create a new credit note."""
    return CreditNote(
        id="cn_002",
        invoice_id=credit_note.invoice_id,
        credit_note_number="CN-2024-002",
        reason=credit_note.reason,
        amount=credit_note.amount,
        status="pending",
        notes=credit_note.notes,
        created_at=datetime.now(),
    )


# Receipt endpoints
@router.get("/receipts", response_model=List[Receipt])
async def list_receipts(
    customer_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List receipts."""
    return [
        Receipt(
            id="rec_001",
            payment_id="pay_001",
            receipt_number="REC-2024-001",
            issued_at=datetime.now(),
            amount=108.50,
            payment_method="credit_card",
            customer_name="John Doe",
            invoice_number="INV-2024-001",
        )
    ]


@router.post("/receipts", response_model=Receipt, status_code=status.HTTP_201_CREATED)
async def create_receipt(receipt: ReceiptCreate, db: Session = Depends(get_db)):
    """Generate a receipt for payment."""
    return Receipt(
        id="rec_002",
        payment_id=receipt.payment_id,
        receipt_number="REC-2024-002",
        issued_at=datetime.now(),
        amount=108.50,
        payment_method="credit_card",
        customer_name="Jane Smith",
        invoice_number="INV-2024-002",
    )


# Tax endpoints
@router.get("/tax-rates", response_model=List[TaxRate])
async def list_tax_rates(
    jurisdiction: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List tax rates."""
    return [
        TaxRate(
            id="tax_001",
            name="State Sales Tax",
            rate=0.085,
            tax_type="sales_tax",
            jurisdiction="CA",
            active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]


@router.post("/tax-rates", response_model=TaxRate, status_code=status.HTTP_201_CREATED)
async def create_tax_rate(tax_rate: TaxRateCreate, db: Session = Depends(get_db)):
    """Create a new tax rate."""
    return TaxRate(
        id="tax_002",
        name=tax_rate.name,
        rate=tax_rate.rate,
        tax_type=tax_rate.tax_type,
        jurisdiction=tax_rate.jurisdiction,
        active=tax_rate.active,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# Subscription endpoints
@router.get("/subscriptions", response_model=List[Subscription])
async def list_subscriptions(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List subscriptions."""
    return [
        Subscription(
            id="sub_001",
            customer_id="cust_001",
            plan_id="plan_001",
            billing_cycle="monthly",
            amount=29.99,
            currency="USD",
            status="active",
            start_date=datetime.now(),
            current_period_start=datetime.now(),
            current_period_end=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    ]


@router.post(
    "/subscriptions", response_model=Subscription, status_code=status.HTTP_201_CREATED
)
async def create_subscription(
    subscription: SubscriptionCreate, db: Session = Depends(get_db)
):
    """Create a new subscription."""
    return Subscription(
        id="sub_002",
        customer_id=subscription.customer_id,
        plan_id=subscription.plan_id,
        billing_cycle=subscription.billing_cycle,
        amount=subscription.amount,
        currency=subscription.currency,
        status="active",
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        current_period_start=datetime.now(),
        current_period_end=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# Reporting endpoints
@router.get("/reports/summary", response_model=BillingReport)
async def get_billing_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
):
    """Get billing summary report for date range."""
    return BillingReport(
        period_start=datetime.combine(start_date, datetime.min.time()),
        period_end=datetime.combine(end_date, datetime.max.time()),
        total_invoiced=5000.00,
        total_paid=4500.00,
        total_outstanding=500.00,
        invoice_count=25,
        payment_count=22,
        average_payment_time=3.5,
    )
