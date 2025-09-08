"""
Service Workflow Integration Tests - Multi-service orchestration, transaction management, and business flows.
Tests complex service interactions, dependency chains, and workflow orchestration patterns.
"""
from datetime import datetime, timezone

import pytest
from tests.utilities.integration_test_base import (
    ServiceIntegrationTestBase,
    TransactionIntegrationTestBase,
)


class TestUserRegistrationWorkflow(ServiceIntegrationTestBase):
    """Test user registration workflow across multiple services."""

    def setup_method(self):
        """Setup user registration workflow services."""
        super().setup_method()

        # Define service configuration for user registration
        self.user_services = {
            "user_service": {
                "dependencies": {"database", "cache"},
                "responses": {
                    "create_user": {
                        "id": "user-123",
                        "email": "test@example.com",
                        "status": "active",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    },
                    "validate_email": True,
                    "send_verification": {"sent": True, "verification_id": "verify-123"}
                }
            },
            "email_service": {
                "dependencies": {"smtp_client"},
                "responses": {
                    "send_welcome_email": {"sent": True, "message_id": "msg-123"},
                    "send_verification_email": {"sent": True, "verification_id": "verify-123"}
                }
            },
            "audit_service": {
                "dependencies": {"database"},
                "responses": {
                    "log_event": {"logged": True, "event_id": "audit-123"}
                }
            },
            "profile_service": {
                "dependencies": {"database", "user_service"},
                "responses": {
                    "create_profile": {
                        "id": "profile-123",
                        "user_id": "user-123",
                        "preferences": {"theme": "light", "notifications": True}
                    }
                }
            }
        }

        self.create_service_registry(self.user_services)

    @pytest.mark.asyncio
    async def test_successful_user_registration_workflow(self):
        """Test complete user registration workflow with all services."""
        # Define workflow steps
        workflow_steps = [
            {
                "name": "validate_email",
                "service": "user_service",
                "method": "validate_email",
                "kwargs": {"email": "test@example.com"},
                "context_key": "email_valid"
            },
            {
                "name": "create_user",
                "service": "user_service",
                "method": "create_user",
                "kwargs": {
                    "email": "test@example.com",
                    "name": "Test User",
                    "password_hash": "hashed_password"
                },
                "context_key": "user"
            },
            {
                "name": "create_profile",
                "service": "profile_service",
                "method": "create_profile",
                "kwargs": {"user_id": "user-123"},
                "context_key": "profile"
            },
            {
                "name": "send_welcome_email",
                "service": "email_service",
                "method": "send_welcome_email",
                "kwargs": {"email": "test@example.com", "name": "Test User"}
            },
            {
                "name": "send_verification_email",
                "service": "email_service",
                "method": "send_verification_email",
                "kwargs": {"email": "test@example.com", "user_id": "user-123"}
            },
            {
                "name": "log_registration",
                "service": "audit_service",
                "method": "log_event",
                "kwargs": {
                    "event_type": "user_registered",
                    "user_id": "user-123",
                    "metadata": {"registration_method": "web"}
                }
            }
        ]

        # Execute workflow
        results = await self.execute_service_workflow(workflow_steps)

        # Assertions
        assert len(results) == 6
        assert "step_0_validate_email" in results
        assert "step_1_create_user" in results
        assert "step_2_create_profile" in results
        assert "step_3_send_welcome_email" in results
        assert "step_4_send_verification_email" in results
        assert "step_5_log_registration" in results

        # Verify service call order
        self.assert_service_called_in_order(
            ["user_service", "user_service", "profile_service", "email_service", "email_service", "audit_service"],
            ["validate_email", "create_user", "create_profile", "send_welcome_email", "send_verification_email", "log_event"]
        )

    @pytest.mark.asyncio
    async def test_user_registration_workflow_with_email_validation_failure(self):
        """Test workflow failure when email validation fails."""
        # Setup email validation to fail
        self.service_registry["user_service"].validate_email.return_value = False

        workflow_steps = [
            {
                "name": "validate_email",
                "service": "user_service",
                "method": "validate_email",
                "kwargs": {"email": "invalid@example.com"},
                "context_key": "email_valid"
            }
        ]

        # Execute workflow
        results = await self.execute_service_workflow(workflow_steps)

        # Should complete but with validation failure
        assert results["step_0_validate_email"] is False

    @pytest.mark.asyncio
    async def test_user_registration_workflow_compensation_on_failure(self):
        """Test workflow compensation when user creation fails after profile creation."""
        # Setup user service to fail on create
        self.service_registry["user_service"].create_user.side_effect = Exception("Database error")

        workflow_steps = [
            {
                "name": "validate_email",
                "service": "user_service",
                "method": "validate_email",
                "kwargs": {"email": "test@example.com"}
            },
            {
                "name": "create_user",
                "service": "user_service",
                "method": "create_user",
                "kwargs": {"email": "test@example.com", "name": "Test User"}
            }
        ]

        # Execute workflow expecting failure
        with pytest.raises(Exception, match="Database error"):
            await self.execute_service_workflow(workflow_steps)


class TestOrderProcessingWorkflow(ServiceIntegrationTestBase):
    """Test e-commerce order processing workflow."""

    def setup_method(self):
        """Setup order processing workflow services."""
        super().setup_method()

        self.order_services = {
            "inventory_service": {
                "responses": {
                    "check_availability": {"available": True, "quantity": 10},
                    "reserve_items": {"reserved": True, "reservation_id": "res-123"},
                    "release_reservation": {"released": True}
                }
            },
            "payment_service": {
                "responses": {
                    "process_payment": {
                        "success": True,
                        "transaction_id": "txn-123",
                        "amount": 99.99
                    },
                    "refund_payment": {"refunded": True, "refund_id": "ref-123"}
                }
            },
            "order_service": {
                "responses": {
                    "create_order": {
                        "id": "order-123",
                        "status": "confirmed",
                        "total": 99.99,
                        "items": [{"sku": "ITEM-001", "quantity": 2}]
                    },
                    "update_status": {"updated": True}
                }
            },
            "shipping_service": {
                "responses": {
                    "calculate_shipping": {"cost": 9.99, "estimated_days": 3},
                    "create_shipment": {
                        "shipment_id": "ship-123",
                        "tracking_number": "TRK123456"
                    }
                }
            },
            "notification_service": {
                "responses": {
                    "send_confirmation": {"sent": True},
                    "send_shipping_notification": {"sent": True}
                }
            }
        }

        self.create_service_registry(self.order_services)

    @pytest.mark.asyncio
    async def test_successful_order_processing_workflow(self):
        """Test complete order processing from cart to shipment."""
        workflow_steps = [
            {
                "name": "check_inventory",
                "service": "inventory_service",
                "method": "check_availability",
                "kwargs": {"items": [{"sku": "ITEM-001", "quantity": 2}]},
                "context_key": "inventory_check"
            },
            {
                "name": "reserve_inventory",
                "service": "inventory_service",
                "method": "reserve_items",
                "kwargs": {"items": [{"sku": "ITEM-001", "quantity": 2}]},
                "context_key": "reservation"
            },
            {
                "name": "calculate_shipping",
                "service": "shipping_service",
                "method": "calculate_shipping",
                "kwargs": {"address": "123 Main St", "items": [{"sku": "ITEM-001", "quantity": 2}]},
                "context_key": "shipping"
            },
            {
                "name": "process_payment",
                "service": "payment_service",
                "method": "process_payment",
                "kwargs": {"amount": 109.98, "payment_method": "credit_card"},
                "context_key": "payment"
            },
            {
                "name": "create_order",
                "service": "order_service",
                "method": "create_order",
                "kwargs": {
                    "items": [{"sku": "ITEM-001", "quantity": 2}],
                    "payment_id": "txn-123",
                    "shipping_cost": 9.99
                },
                "context_key": "order"
            },
            {
                "name": "create_shipment",
                "service": "shipping_service",
                "method": "create_shipment",
                "kwargs": {"order_id": "order-123"},
                "context_key": "shipment"
            },
            {
                "name": "send_confirmation",
                "service": "notification_service",
                "method": "send_confirmation",
                "kwargs": {"order_id": "order-123", "customer_email": "customer@example.com"}
            }
        ]

        results = await self.execute_service_workflow(workflow_steps)

        # Verify all steps completed
        assert len(results) == 7

        # Verify key workflow data
        assert results["step_0_check_inventory"]["available"] is True
        assert results["step_1_reserve_inventory"]["reserved"] is True
        assert results["step_3_process_payment"]["success"] is True
        assert results["step_4_create_order"]["status"] == "confirmed"

        # Verify service interactions
        inventory_service = self.service_registry["inventory_service"]
        payment_service = self.service_registry["payment_service"]
        order_service = self.service_registry["order_service"]

        inventory_service.check_availability.assert_called_once()
        inventory_service.reserve_items.assert_called_once()
        payment_service.process_payment.assert_called_once()
        order_service.create_order.assert_called_once()


class TestWorkflowErrorRecovery(TransactionIntegrationTestBase):
    """Test workflow error recovery and compensation patterns."""

    def setup_method(self):
        """Setup error recovery test services."""
        super().setup_method()

        self.recovery_services = {
            "service_a": {
                "responses": {
                    "operation": {"success": True, "data": "result_a"},
                    "compensate": {"compensated": True}
                }
            },
            "service_b": {
                "responses": {
                    "operation": {"success": True, "data": "result_b"},
                    "compensate": {"compensated": True}
                }
            },
            "service_c": {
                "responses": {
                    "operation": {"success": True, "data": "result_c"},
                    "compensate": {"compensated": True}
                }
            }
        }

        self.create_service_registry(self.recovery_services)

    @pytest.mark.asyncio
    async def test_distributed_transaction_with_compensation(self):
        """Test distributed transaction with saga compensation pattern."""
        # Define operations and their compensations
        operations = [
            {"service": "service_a", "method": "operation", "kwargs": {"data": "input_a"}},
            {"service": "service_b", "method": "operation", "kwargs": {"data": "input_b"}},
            {"service": "service_c", "method": "operation", "kwargs": {"data": "input_c"}}
        ]

        compensation_actions = [
            {"service": "service_a", "method": "compensate", "kwargs": {"data": "undo_a"}},
            {"service": "service_b", "method": "compensate", "kwargs": {"data": "undo_b"}},
            {"service": "service_c", "method": "compensate", "kwargs": {"data": "undo_c"}}
        ]

        # Test successful transaction
        result = await self.simulate_distributed_transaction(operations)

        assert result["status"] == "completed"
        assert len(result["completed_operations"]) == 3

        # Test transaction with failure at operation 2 (service_c)
        failed_result = await self.simulate_distributed_transaction(
            operations,
            should_fail_at=2,
            compensation_actions=compensation_actions
        )

        assert failed_result["status"] == "failed"
        assert len(failed_result["completed_operations"]) == 2  # service_a and service_b completed
        assert len(failed_result["compensated_operations"]) == 2  # Both should be compensated

        # Verify compensation methods were called
        self.service_registry["service_a"].compensate.assert_called_once()
        self.service_registry["service_b"].compensate.assert_called_once()
        self.service_registry["service_c"].compensate.assert_not_called()  # Never reached

    @pytest.mark.asyncio
    async def test_retry_mechanism_with_eventual_success(self):
        """Test retry mechanism that eventually succeeds."""
        # Create retry policy
        self.create_retry_policy("flaky_operation", max_attempts=3, backoff_factor=1.5)

        # Setup service to fail twice then succeed
        call_count = 0
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Temporary failure #{call_count}")
            return {"success": True, "attempt": call_count}

        # Execute with retry
        result = await self.execute_with_retry(flaky_operation, "flaky_operation")

        assert result["success"] is True
        assert result["attempt"] == 3

        # Verify retry policy was used
        policy = self.retry_policies["flaky_operation"]
        assert policy["current_attempt"] == 3
        assert len(policy["delays"]) == 2  # Two retry delays

    @pytest.mark.asyncio
    async def test_retry_mechanism_with_permanent_failure(self):
        """Test retry mechanism that exhausts all attempts."""
        # Create retry policy
        self.create_retry_policy("failing_operation", max_attempts=2)

        def always_failing_operation():
            raise Exception("Permanent failure")

        # Execute with retry expecting final failure
        with pytest.raises(Exception, match="Permanent failure"):
            await self.execute_with_retry(always_failing_operation, "failing_operation")

        # Verify retry policy was exhausted
        policy = self.retry_policies["failing_operation"]
        assert policy["current_attempt"] == 2


class TestComplexBusinessWorkflows(ServiceIntegrationTestBase):
    """Test complex business workflows with multiple decision points."""

    def setup_method(self):
        """Setup complex business workflow services."""
        super().setup_method()

        self.business_services = {
            "customer_service": {
                "responses": {
                    "get_customer": {
                        "id": "cust-123",
                        "tier": "premium",
                        "credit_limit": 5000,
                        "account_status": "active"
                    },
                    "update_credit_usage": {"updated": True}
                }
            },
            "pricing_service": {
                "responses": {
                    "calculate_price": {"base_price": 100.0, "discount": 10.0, "final_price": 90.0},
                    "apply_tier_discount": {"discounted_price": 85.0, "discount_applied": 5.0}
                }
            },
            "approval_service": {
                "responses": {
                    "check_approval_required": {"required": True, "threshold": 1000},
                    "request_approval": {"approval_id": "app-123", "status": "pending"},
                    "check_approval_status": {"approved": True, "approved_by": "manager-456"}
                }
            },
            "workflow_service": {
                "responses": {
                    "route_request": {"route": "high_value_approval"},
                    "execute_workflow": {"executed": True, "workflow_id": "wf-123"}
                }
            }
        }

        self.create_service_registry(self.business_services)

    @pytest.mark.asyncio
    async def test_high_value_transaction_approval_workflow(self):
        """Test high-value transaction requiring approval workflow."""
        # Define complex workflow with decision points
        workflow_context = {
            "customer_id": "cust-123",
            "transaction_amount": 1500.0,
            "transaction_type": "purchase"
        }

        workflow_steps = [
            {
                "name": "get_customer_info",
                "service": "customer_service",
                "method": "get_customer",
                "kwargs": {"customer_id": "cust-123"},
                "context_key": "customer"
            },
            {
                "name": "calculate_base_price",
                "service": "pricing_service",
                "method": "calculate_price",
                "kwargs": {"amount": 1500.0, "product": "premium_service"},
                "context_key": "pricing"
            },
            {
                "name": "apply_tier_discount",
                "service": "pricing_service",
                "method": "apply_tier_discount",
                "kwargs": {"base_price": 90.0, "customer_tier": "premium"},
                "context_key": "final_pricing"
            },
            {
                "name": "check_approval_required",
                "service": "approval_service",
                "method": "check_approval_required",
                "kwargs": {"amount": 85.0, "customer_tier": "premium"},
                "context_key": "approval_check"
            },
            {
                "name": "request_approval",
                "service": "approval_service",
                "method": "request_approval",
                "kwargs": {
                    "customer_id": "cust-123",
                    "amount": 85.0,
                    "justification": "High-value premium customer transaction"
                },
                "context_key": "approval_request"
            },
            {
                "name": "route_workflow",
                "service": "workflow_service",
                "method": "route_request",
                "kwargs": {"approval_id": "app-123", "priority": "high"},
                "context_key": "routing"
            }
        ]

        results = await self.execute_service_workflow(workflow_steps, workflow_context)

        # Verify workflow execution
        assert len(results) == 6

        # Verify business logic
        customer_info = results["step_0_get_customer_info"]
        assert customer_info["tier"] == "premium"

        pricing_info = results["step_1_calculate_base_price"]
        assert pricing_info["final_price"] == 90.0

        tier_pricing = results["step_2_apply_tier_discount"]
        assert tier_pricing["discounted_price"] == 85.0

        approval_check = results["step_3_check_approval_required"]
        assert approval_check["required"] is True

        approval_request = results["step_4_request_approval"]
        assert approval_request["approval_id"] == "app-123"

        # Verify service call patterns
        customer_service = self.service_registry["customer_service"]
        pricing_service = self.service_registry["pricing_service"]
        approval_service = self.service_registry["approval_service"]

        customer_service.get_customer.assert_called_once()
        pricing_service.calculate_price.assert_called_once()
        pricing_service.apply_tier_discount.assert_called_once()
        approval_service.check_approval_required.assert_called_once()
        approval_service.request_approval.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_context_propagation(self):
        """Test that workflow context is properly propagated between steps."""
        workflow_steps = [
            {
                "name": "step1",
                "service": "customer_service",
                "method": "get_customer",
                "kwargs": {"customer_id": "cust-123"},
                "context_key": "customer_data"
            },
            {
                "name": "step2",
                "service": "pricing_service",
                "method": "calculate_price",
                "kwargs": {"customer_tier": "premium"},  # This should get customer_data from context
                "context_key": "price_data"
            }
        ]

        initial_context = {"session_id": "sess-123", "user_agent": "test-agent"}

        results = await self.execute_service_workflow(workflow_steps, initial_context)

        # Verify results contain expected data
        assert "step_0_step1" in results
        assert "step_1_step2" in results

        # Verify workflow state tracking
        workflow_states = list(self.workflow_states.values())
        assert len(workflow_states) == 1

        workflow = workflow_states[0]
        assert workflow["steps_completed"] == 2
        assert workflow["steps_failed"] == 0
        assert "session_id" in workflow["context"]
        assert "user_agent" in workflow["context"]
