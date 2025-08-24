Billing Module
==============

The Billing module handles comprehensive billing operations, payment processing, and financial management.

Overview
--------

The Billing module provides:

* Invoice generation and management
* Payment processing with multiple gateways
* Subscription billing and recurring charges
* Tax calculations and compliance
* Credit management and refunds
* Financial reporting and analytics
* Multi-currency support

.. note::
   The billing module integrates with external payment processors and maintains
   PCI DSS compliance for secure payment handling.

Router & API Endpoints
----------------------

.. automodule:: dotmac_isp.modules.billing.router
   :members:
   :undoc-members:
   :show-inheritance:

Models
------

.. automodule:: dotmac_isp.modules.billing.models
   :members:
   :undoc-members:
   :show-inheritance:

Core Services
-------------

Billing Service
~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.services.billing_service
   :members:
   :undoc-members:
   :show-inheritance:

Invoice Service
~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.services.invoice_service
   :members:
   :undoc-members:
   :show-inheritance:

Payment Service
~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.services.payment_service
   :members:
   :undoc-members:
   :show-inheritance:

Subscription Service
~~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.services.subscription_service
   :members:
   :undoc-members:
   :show-inheritance:

Tax Service
~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.services.tax_service
   :members:
   :undoc-members:
   :show-inheritance:

Credit Service
~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.services.credit_service
   :members:
   :undoc-members:
   :show-inheritance:

Domain Services
---------------

Calculation Service
~~~~~~~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.domain.calculation_service
   :members:
   :undoc-members:
   :show-inheritance:

PDF Generator
~~~~~~~~~~~~~

.. automodule:: dotmac_isp.modules.billing.pdf_generator
   :members:
   :undoc-members:
   :show-inheritance:

Schemas
-------

.. automodule:: dotmac_isp.modules.billing.schemas
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Creating an Invoice
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.invoice_service import InvoiceService
   from dotmac_isp.modules.billing.schemas import InvoiceCreate
   from decimal import Decimal

   # Initialize service
   invoice_service = InvoiceService(db_session, tenant_id)

   # Create invoice data
   invoice_data = InvoiceCreate(
       customer_id="customer-123",
       due_date="2024-02-15",
       line_items=[
           {
               "description": "Internet Service - Fiber 100/100",
               "quantity": 1,
               "unit_price": Decimal("79.99"),
               "tax_rate": Decimal("0.08")
           },
           {
               "description": "Equipment Rental - Router",
               "quantity": 1,
               "unit_price": Decimal("9.99"),
               "tax_rate": Decimal("0.08")
           }
       ]
   )

   # Generate invoice
   invoice = await invoice_service.create_invoice(invoice_data)
   print(f"Created invoice {invoice.invoice_number} for ${invoice.total_amount}")

Processing a Payment
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.payment_service import PaymentService
   from dotmac_isp.modules.billing.schemas import PaymentCreate

   # Initialize payment service
   payment_service = PaymentService(db_session, tenant_id)

   # Process credit card payment
   payment_data = PaymentCreate(
       invoice_id="invoice-456",
       amount=Decimal("89.98"),
       payment_method="credit_card",
       payment_details={
           "card_token": "tok_visa_4242",  # Tokenized card data
           "billing_address": {
               "street": "123 Main St",
               "city": "Anytown",
               "state": "CA",
               "zip": "12345"
           }
       }
   )

   # Process payment
   result = await payment_service.process_payment(payment_data)
   
   if result.success:
       print(f"Payment processed: {result.transaction_id}")
       print(f"Status: {result.status}")
   else:
       print(f"Payment failed: {result.error_message}")

Setting Up Recurring Billing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.subscription_service import SubscriptionService
   from dotmac_isp.modules.billing.schemas import SubscriptionCreate

   # Initialize subscription service
   subscription_service = SubscriptionService(db_session, tenant_id)

   # Create recurring subscription
   subscription_data = SubscriptionCreate(
       customer_id="customer-123",
       service_plan_id="plan-fiber-100",
       billing_cycle="monthly",
       start_date="2024-02-01",
       amount=Decimal("79.99"),
       auto_pay=True,
       payment_method_id="pm_card_visa"
   )

   # Create subscription
   subscription = await subscription_service.create_subscription(subscription_data)
   print(f"Created subscription {subscription.id}")
   print(f"Next billing date: {subscription.next_billing_date}")

Advanced Tax Calculation
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.tax_service import TaxService
   from dotmac_isp.modules.billing.schemas import TaxCalculationRequest

   # Initialize tax service
   tax_service = TaxService(db_session, tenant_id)

   # Calculate taxes for complex scenario
   tax_request = TaxCalculationRequest(
       customer_address={
           "street": "123 Main St",
           "city": "San Francisco",
           "state": "CA",
           "zip": "94105",
           "country": "US"
       },
       line_items=[
           {
               "description": "Internet Service",
               "amount": Decimal("79.99"),
               "tax_category": "telecommunications"
           },
           {
               "description": "Equipment",
               "amount": Decimal("99.99"),
               "tax_category": "tangible_goods"
           }
       ],
       invoice_date="2024-02-01"
   )

   # Calculate taxes
   tax_result = await tax_service.calculate_taxes(tax_request)
   
   print(f"Subtotal: ${tax_result.subtotal}")
   print(f"Total tax: ${tax_result.total_tax}")
   print(f"Grand total: ${tax_result.total_amount}")
   
   # Detailed tax breakdown
   for tax_line in tax_result.tax_lines:
       print(f"  {tax_line.tax_type}: ${tax_line.amount} ({tax_line.rate}%)")

Handling Refunds
~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.credit_service import CreditService
   from dotmac_isp.modules.billing.schemas import RefundRequest

   # Initialize credit service
   credit_service = CreditService(db_session, tenant_id)

   # Process refund
   refund_request = RefundRequest(
       payment_id="payment-789",
       amount=Decimal("79.99"),
       reason="Service cancellation",
       refund_type="full"  # or "partial"
   )

   # Execute refund
   refund = await credit_service.process_refund(refund_request)
   
   if refund.success:
       print(f"Refund processed: ${refund.amount}")
       print(f"Refund ID: {refund.refund_id}")
       print(f"Expected in account: {refund.estimated_arrival}")
   else:
       print(f"Refund failed: {refund.error}")

Generating Financial Reports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.billing_service import BillingService
   from datetime import date, timedelta

   # Initialize billing service
   billing_service = BillingService(db_session, tenant_id)

   # Generate monthly revenue report
   end_date = date.today()
   start_date = end_date.replace(day=1)  # First day of current month

   revenue_report = await billing_service.generate_revenue_report(
       start_date=start_date,
       end_date=end_date,
       include_details=True
   )

   print(f"Revenue Report for {start_date} to {end_date}")
   print(f"Total Revenue: ${revenue_report.total_revenue}")
   print(f"Recurring Revenue: ${revenue_report.recurring_revenue}")
   print(f"One-time Charges: ${revenue_report.one_time_revenue}")
   print(f"Refunds: ${revenue_report.total_refunds}")
   print(f"Net Revenue: ${revenue_report.net_revenue}")

   # Payment method breakdown
   for method, amount in revenue_report.payment_methods.items():
       print(f"  {method}: ${amount}")

Webhook Handling
~~~~~~~~~~~~~~~~

.. code-block:: python

   from dotmac_isp.modules.billing.services.payment_service import PaymentService
   from fastapi import Request

   # Webhook handler for payment processor
   async def handle_payment_webhook(request: Request):
       payment_service = PaymentService(db_session, tenant_id)
       
       # Verify webhook signature
       signature = request.headers.get("stripe-signature")
       payload = await request.body()
       
       try:
           event = payment_service.verify_webhook(payload, signature)
           
           if event.type == "payment_intent.succeeded":
               payment_intent = event.data.object
               await payment_service.confirm_payment(payment_intent.id)
               print(f"Payment confirmed: {payment_intent.id}")
               
           elif event.type == "payment_intent.payment_failed":
               payment_intent = event.data.object
               await payment_service.handle_failed_payment(payment_intent.id)
               print(f"Payment failed: {payment_intent.id}")
               
       except ValueError as e:
           print(f"Invalid webhook signature: {e}")
           return {"error": "Invalid signature"}, 400
       
       return {"status": "success"}

Security Considerations
-----------------------

.. warning::
   **PCI DSS Compliance**: Never store raw credit card data. Always use tokenized payment methods and ensure PCI DSS compliance when handling payment information.

.. important::
   **Financial Data Integrity**: All financial operations should be logged and auditable. Use database transactions to ensure data consistency.

.. danger::
   **Webhook Security**: Always verify webhook signatures to prevent unauthorized payment status updates.

.. tip::
   **Idempotency**: Implement idempotency keys for payment operations to prevent duplicate charges.

Best Practices
--------------

1. **Error Handling**: Always handle payment processor errors gracefully and provide meaningful error messages to users.

2. **Audit Trail**: Maintain detailed logs of all financial transactions for compliance and debugging.

3. **Retry Logic**: Implement exponential backoff for failed payment retries.

4. **Currency Precision**: Use Decimal type for all monetary calculations to avoid floating-point precision issues.

5. **Testing**: Use payment processor sandbox environments for testing and validate all edge cases.

Common Issues & Solutions
-------------------------

**Failed Payments**
   - Insufficient funds: Implement retry logic with customer notification
   - Expired cards: Proactive card expiry notifications
   - Fraud detection: Clear communication about security holds

**Tax Calculation Errors**
   - Address validation: Ensure accurate customer addresses for tax calculation
   - Tax rate updates: Regular updates from tax service providers
   - Multi-jurisdiction: Handle customers across different tax jurisdictions

**Refund Processing**
   - Partial refunds: Clear documentation of refund amounts and reasons
   - Processing time: Set clear expectations for refund processing timeframes
   - Failed refunds: Fallback to manual processing when automated refunds fail