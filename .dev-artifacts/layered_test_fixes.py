#!/usr/bin/env python3
"""
Layered approach to fix failing tests in InvoiceGenerationWorkflow.

Layer 1: Problem Analysis
- test_deliver_invoice_with_failures: Webhook delivery fails due to missing invoice_data
- test_process_automatic_payment_step: Payment method lookup failure

Layer 2: Root Cause Identification  
- Webhook delivery needs invoice_data available but it's None
- Payment processing falls through to error handling

Layer 3: Targeted Implementation Fixes
"""

import os

# Read test file
test_file = "/home/dotmac_framework/packages/dotmac-business-logic/tests/test_invoice_generation_workflow.py"
with open(test_file, 'r') as f:
    test_content = f.read()

# Fix 1: Ensure webhook delivery has required data available
fix_webhook_test = '''        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        # Add invoice_data needed for webhook delivery
        workflow.invoice_data = {"total_amount": 100.0}

        result = await workflow.execute_step("deliver_invoice")'''

test_content = test_content.replace(
    '''        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice

        result = await workflow.execute_step("deliver_invoice")''',
    fix_webhook_test
)

# Fix 2: Ensure payment method is available and prevent error path
payment_fix = '''        # Setup payment processing
        payment_result = MagicMock(
            id=uuid4(),
            status=PaymentStatus.SUCCESS.value,
        )
        mock_services["payment_service"].process_payment.return_value = payment_result
        mock_services["payment_service"].get_default_payment_method = AsyncMock(return_value="test_method")

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        workflow.customer = mock_customer
        # Add invoice_data needed for payment processing
        workflow.invoice_data = {"amount_due": 100.0}

        result = await workflow.execute_step("process_automatic_payment")'''

test_content = test_content.replace(
    '''        # Setup payment processing
        payment_result = MagicMock(
            id=uuid4(),
            status=PaymentStatus.SUCCESS.value,
        )
        mock_services["payment_service"].process_payment.return_value = payment_result
        mock_services["payment_service"].get_default_payment_method = AsyncMock(return_value="test_method")

        workflow = InvoiceGenerationWorkflow(
            request=request,
            **mock_services
        )
        workflow.invoice = mock_invoice
        workflow.customer = mock_customer

        result = await workflow.execute_step("process_automatic_payment")''',
    payment_fix
)

# Write fixed content
with open(test_file, 'w') as f:
    f.write(test_content)

print("Layer 3: Applied targeted test fixes for:")
print("- Webhook delivery data availability")
print("- Payment processing mock setup")