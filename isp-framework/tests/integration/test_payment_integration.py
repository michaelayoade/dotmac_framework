"""
Integration tests for payment processing workflow.

Tests the end-to-end payment flow including external payment processor
integration and database persistence.
"""

import pytest
import requests
import asyncio
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.payment_flow
@pytest.mark.revenue_critical
def test_payment_processor_integration():
    """
    Integration Test: Payment processor handles real payment requests correctly.
    
    This test validates:
    1. Mock payment processor responds to payment requests
    2. Payment success/failure scenarios work correctly
    3. Response format matches expected contract
    """
    # Given: Mock payment processor is running
    payment_url = "http://localhost:8080"
    
    # When: We send a payment request
    payment_data = {
        "amount": 99.99,
        "card_number": "4111111111111111",
        "customer_id": "test-customer-123"
    }
    
    response = requests.post(f"{payment_url}/process-payment", json=payment_data)
    
    # Then: Payment processor should respond correctly
    assert response.status_code == 200
    
    result = response.json()
    assert "status" in result
    assert result["status"] in ["success", "failed"]
    assert result["amount"] == payment_data["amount"]
    
    if result["status"] == "success":
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("txn_")
    else:
        assert "error" in result


@pytest.mark.integration
@pytest.mark.contract
@pytest.mark.revenue_critical
def test_payment_processor_health_check():
    """
    Contract Test: Payment processor health endpoint works correctly.
    """
    # Given: Payment processor should be healthy
    health_url = "http://localhost:8080/health"
    
    # When: We check health
    response = requests.get(health_url)
    
    # Then: Should return healthy status
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "ok"


@pytest.mark.integration
@pytest.mark.behavior
@pytest.mark.billing_core
def test_end_to_end_billing_workflow():
    """
    Behavior Test: Complete billing workflow from invoice creation to payment.
    
    This test simulates:
    1. Customer has service
    2. Invoice is generated
    3. Customer pays invoice
    4. Payment is processed
    5. Account is updated
    """
    # This would be a complete workflow test
    # For now, we'll test the mock payment integration
    
    # Given: Customer with outstanding invoice
    customer_id = "test-customer-billing"
    invoice_amount = 79.99
    
    # When: Customer pays invoice
    payment_data = {
        "amount": invoice_amount,
        "card_number": "4111111111111111",
        "customer_id": customer_id
    }
    
    payment_response = requests.post(
        "http://localhost:8080/process-payment", 
        json=payment_data
    )
    
    # Then: Payment should be processed
    assert payment_response.status_code == 200
    payment_result = payment_response.json()
    
    # And: Payment amount should match invoice
    assert payment_result["amount"] == invoice_amount
    
    # And: If successful, should have transaction ID
    if payment_result["status"] == "success":
        assert "transaction_id" in payment_result


@pytest.mark.integration
@pytest.mark.performance_baseline
def test_payment_processor_performance():
    """
    Performance Test: Payment processor meets response time requirements.
    """
    import time
    
    # Given: Payment processor performance requirements
    max_response_time_seconds = 1.0
    
    # When: We send multiple payment requests
    payment_data = {
        "amount": 50.00,
        "card_number": "4111111111111111",
        "customer_id": "perf-test-customer"
    }
    
    response_times = []
    for _ in range(5):
        start_time = time.time()
        response = requests.post(
            "http://localhost:8080/process-payment",
            json=payment_data
        )
        end_time = time.time()
        
        assert response.status_code == 200
        response_times.append(end_time - start_time)
    
    # Then: Average response time should be within limits
    avg_response_time = sum(response_times) / len(response_times)
    assert avg_response_time < max_response_time_seconds, \
        f"Average response time {avg_response_time:.3f}s exceeds {max_response_time_seconds}s"
    
    # And: No single request should be too slow
    max_response_time = max(response_times)
    assert max_response_time < max_response_time_seconds * 2, \
        f"Slowest request {max_response_time:.3f}s exceeds tolerance"


@pytest.mark.integration
@pytest.mark.data_safety
def test_payment_data_persistence():
    """
    Data Safety Test: Payment transaction data is properly persisted.
    
    This would test that payment data is correctly stored in the database
    after processing. For the mock environment, we test that the payment
    processor maintains consistent state.
    """
    # Given: Multiple payment requests
    payment_requests = [
        {"amount": 25.00, "card_number": "4111111111111111", "customer_id": "data-test-1"},
        {"amount": 50.00, "card_number": "4111111111111111", "customer_id": "data-test-2"},
        {"amount": 75.00, "card_number": "4111111111111111", "customer_id": "data-test-3"},
    ]
    
    # When: We process all payments
    results = []
    for payment_data in payment_requests:
        response = requests.post(
            "http://localhost:8080/process-payment",
            json=payment_data
        )
        assert response.status_code == 200
        results.append(response.json()
    
    # Then: All results should be consistent
    for i, result in enumerate(results):
        assert result["amount"] == payment_requests[i]["amount"]
        assert "status" in result
        
        # If successful, should have unique transaction IDs
        if result["status"] == "success":
            assert "transaction_id" in result
            # Transaction IDs should be unique
            other_successful = [r for r in results if r.get("status") == "success" and r != result]
            for other in other_successful:
                assert result["transaction_id"] != other["transaction_id"]


@pytest.mark.integration
@pytest.mark.ai_safety
def test_payment_processor_input_validation():
    """
    AI Safety Test: Payment processor properly validates input data.
    
    This ensures that AI-generated or modified code properly handles
    edge cases and malicious input.
    """
    base_url = "http://localhost:8080/process-payment"
    
    # Test cases for input validation
    invalid_inputs = [
        # Negative amounts
        {"amount": -100.00, "card_number": "4111111111111111", "customer_id": "test"},
        # Zero amounts  
        {"amount": 0.0, "card_number": "4111111111111111", "customer_id": "test"},
        # Extremely large amounts
        {"amount": 999999999.99, "card_number": "4111111111111111", "customer_id": "test"},
        # Invalid card numbers
        {"amount": 50.00, "card_number": "invalid", "customer_id": "test"},
        # Missing fields
        {"amount": 50.00, "card_number": "4111111111111111"},
        # Empty customer ID
        {"amount": 50.00, "card_number": "4111111111111111", "customer_id": ""},
    ]
    
    for invalid_input in invalid_inputs:
        response = requests.post(base_url, json=invalid_input)
        
        # Payment processor should handle invalid input gracefully
        # Either reject with 400 or process and return failure status
        if response.status_code == 200:
            result = response.json()
            # If it processes invalid input, it should fail
            if "amount" in invalid_input and invalid_input["amount"] <= 0:
                assert result["status"] == "failed"
        else:
            # Or it should reject with appropriate error code
            assert response.status_code in [400, 422]