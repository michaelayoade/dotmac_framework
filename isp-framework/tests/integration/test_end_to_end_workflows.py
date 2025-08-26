"""
End-to-End Integration Tests for ISP Business Workflows

Tests complete business workflows that span multiple modules and systems.
These tests validate that the entire ISP platform works together correctly.
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from dotmac_isp.modules.identity.service import CustomerService
from dotmac_isp.modules.billing.service import BillingService
from dotmac_isp.modules.services.service import ServiceProvisioningService
from dotmac_isp.modules.network_integration.service import NetworkIntegrationService
from dotmac_isp.modules.support.service import SupportTicketService
from dotmac_isp.modules.notifications.tasks import NotificationService
from dotmac_isp.modules.field_ops.service import FieldOperationsService


@pytest.mark.integration
@pytest.mark.customer_journey
@pytest.mark.revenue_critical
class TestCompleteCustomerLifecycle:
    """Test complete customer lifecycle from signup to service delivery."""
    
    async def test_residential_customer_onboarding_workflow(self, db_session, timezone):
        """Test complete onboarding workflow for residential customer."""
        
        # Initialize services
        customer_service = CustomerService(db_session, "tenant_001")
        billing_service = BillingService(db_session, "tenant_001")
        provisioning_service = ServiceProvisioningService(db_session, "tenant_001")
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        notification_service = NotificationService(db_session, "tenant_001")
        
        # 1. Customer Signup
        customer_data = {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@email.com",
            "phone": "+1-555-123-4567",
            "customer_type": "residential",
            "service_address": {
                "street": "123 Main Street",
                "city": "Anytown", 
                "state": "ST",
                "zip": "12345"
            },
            "requested_service": "fiber_internet_100",
            "installation_preference": "standard"
        }
        
        with patch.object(customer_service, 'create_customer') as mock_create_customer:
            with patch.object(customer_service, 'generate_portal_id') as mock_portal_id:
                
                mock_customer_id = str(uuid4())
                mock_portal_id.return_value = "CUST-12345"
                mock_create_customer.return_value = {
                    "customer_id": mock_customer_id,
                    "portal_id": "CUST-12345",
                    "account_status": "pending_installation"
                }
                
                customer = await customer_service.create_customer(customer_data)
                
                # Verify customer creation
                assert customer["customer_id"] == mock_customer_id
                assert customer["portal_id"] == "CUST-12345"
                assert customer["account_status"] == "pending_installation"
        
        # 2. Service Feasibility Check
        with patch.object(network_service, 'check_service_availability') as mock_feasibility:
            mock_feasibility.return_value = {
                "available": True,
                "service_type": "fiber",
                "max_bandwidth": 1000_000_000,  # 1 Gbps available
                "installation_type": "aerial",
                "estimated_install_time": 5  # 5 business days
            }
            
            feasibility = await network_service.check_service_availability(
                customer_data["service_address"]
            )
            
            assert feasibility["available"] is True
            assert feasibility["service_type"] == "fiber"
        
        # 3. Service Order Creation
        service_order = {
            "customer_id": mock_customer_id,
            "service_plan": "residential_fiber_100",
            "monthly_rate": Decimal("79.99"),
            "installation_fee": Decimal("99.00"),
            "equipment_fee": Decimal("10.00"),  # Router rental
            "requested_install_date": date.today() + timedelta(days=7)
        }
        
        with patch.object(provisioning_service, 'create_service_order') as mock_create_order:
            mock_order_id = str(uuid4())
            mock_create_order.return_value = {
                "order_id": mock_order_id,
                "status": "scheduled",
                "install_date": service_order["requested_install_date"]
            }
            
            order = await provisioning_service.create_service_order(service_order)
            
            assert order["order_id"] == mock_order_id
            assert order["status"] == "scheduled"
        
        # 4. Initial Billing Setup
        with patch.object(billing_service, 'setup_customer_billing') as mock_billing_setup:
            mock_billing_setup.return_value = {
                "billing_account_created": True,
                "first_bill_amount": Decimal("188.99"),  # Install + Equipment + Prorated service
                "next_billing_date": date.today() + timedelta(days=30),
                "auto_pay_available": True
            }
            
            billing_setup = await billing_service.setup_customer_billing(
                mock_customer_id,
                service_order["monthly_rate"],
                service_order["installation_fee"]
            )
            
            assert billing_setup["billing_account_created"] is True
            assert billing_setup["first_bill_amount"] == Decimal("188.99")
        
        # 5. Installation Scheduling
        from dotmac_isp.modules.field_ops.service import FieldOperationsService
        field_ops_service = FieldOperationsService(db_session, "tenant_001")
        
        with patch.object(field_ops_service, 'schedule_installation') as mock_schedule:
            mock_work_order_id = str(uuid4())
            mock_schedule.return_value = {
                "work_order_id": mock_work_order_id,
                "scheduled_date": service_order["requested_install_date"],
                "technician_assigned": "tech_001",
                "estimated_duration": 4  # 4 hours
            }
            
            installation = await field_ops_service.schedule_installation({
                "customer_id": mock_customer_id,
                "order_id": mock_order_id,
                "service_type": "fiber_installation",
                "address": customer_data["service_address"]
            })
            
            assert installation["work_order_id"] == mock_work_order_id
            assert installation["technician_assigned"] == "tech_001"
        
        # 6. Customer Notifications
        with patch.object(notification_service, 'send_welcome_sequence') as mock_notifications:
            mock_notifications.return_value = {
                "welcome_email_sent": True,
                "installation_confirmation_sent": True,
                "portal_access_sent": True
            }
            
            notifications = await notification_service.send_welcome_sequence(
                mock_customer_id,
                {
                    "portal_id": "CUST-12345",
                    "install_date": service_order["requested_install_date"],
                    "technician_contact": "1-800-INSTALL"
                }
            )
            
            assert notifications["welcome_email_sent"] is True
            assert notifications["portal_access_sent"] is True
        
        # 7. Verify Complete Onboarding State
        onboarding_status = {
            "customer_created": customer["customer_id"] is not None,
            "service_feasible": feasibility["available"],
            "order_scheduled": order["status"] == "scheduled", 
            "billing_setup": billing_setup["billing_account_created"],
            "installation_scheduled": installation["work_order_id"] is not None,
            "notifications_sent": notifications["welcome_email_sent"]
        }
        
        # All onboarding steps must complete successfully
        assert all(onboarding_status.values(), f"Onboarding failed: {onboarding_status}"

    async def test_service_installation_and_activation_workflow(self, db_session):
        """Test service installation and activation workflow."""
        
        # Initialize services
        field_ops_service = FieldOperationsService(db_session, "tenant_001")
        network_service = NetworkIntegrationService(db_session, "tenant_001")
        billing_service = BillingService(db_session, "tenant_001")
        notification_service = NotificationService(db_session, "tenant_001")
        
        # Existing customer with scheduled installation
        customer_id = "cust_install_001"
        work_order_id = "wo_install_001"
        
        installation_details = {
            "customer_id": customer_id,
            "work_order_id": work_order_id,
            "service_plan": "residential_fiber_100",
            "equipment_installed": {
                "ont_serial": "GPON12345678",
                "router_serial": "RTR87654321"
            },
            "installation_notes": "Fiber run completed to customer premises"
        }
        
        # 1. Technician Completes Physical Installation
        with patch.object(field_ops_service, 'complete_installation') as mock_complete:
            mock_complete.return_value = {
                "installation_complete": True,
                "equipment_activated": True,
                "signal_quality": "excellent",
                "customer_signature": "digital_signature_hash"
            }
            
            installation_result = await field_ops_service.complete_installation(
                installation_details
            )
            
            assert installation_result["installation_complete"] is True
            assert installation_result["equipment_activated"] is True
        
        # 2. Network Service Provisioning
        provisioning_config = {
            "customer_id": customer_id,
            "username": f"{customer_id}@isp.com",
            "service_plan": "residential_fiber_100",
            "bandwidth_down": 100_000_000,  # 100 Mbps
            "bandwidth_up": 100_000_000,    # 100 Mbps
            "vlan_id": 100,
            "ip_pool": "residential"
        }
        
        with patch.object(network_service, 'provision_customer_service') as mock_provision:
            mock_provision.return_value = {
                "service_active": True,
                "radius_configured": True,
                "bandwidth_profile_applied": True,
                "customer_credentials": {
                    "username": f"{customer_id}@isp.com",
                    "password": "temp_password_123"
                }
            }
            
            provisioning_result = await network_service.provision_customer_service(
                provisioning_config
            )
            
            assert provisioning_result["service_active"] is True
            assert provisioning_result["radius_configured"] is True
        
        # 3. Billing Activation
        with patch.object(billing_service, 'activate_customer_billing') as mock_activate_billing:
            mock_activate_billing.return_value = {
                "billing_activated": True,
                "first_invoice_generated": True,
                "recurring_billing_scheduled": True,
                "auto_pay_ready": True
            }
            
            billing_activation = await billing_service.activate_customer_billing(
                customer_id,
                {
                    "service_start_date": date.today(),
                    "monthly_rate": Decimal("79.99"),
                    "billing_cycle": "monthly"
                }
            )
            
            assert billing_activation["billing_activated"] is True
            assert billing_activation["first_invoice_generated"] is True
        
        # 4. Service Testing and Validation
        with patch.object(network_service, 'test_customer_connectivity') as mock_test:
            mock_test.return_value = {
                "connectivity_test_passed": True,
                "speed_test_down": 98.5,  # Mbps
                "speed_test_up": 99.2,    # Mbps
                "latency_ms": 12.3,
                "packet_loss_percent": 0.0
            }
            
            connectivity_test = await network_service.test_customer_connectivity(
                customer_id
            )
            
            assert connectivity_test["connectivity_test_passed"] is True
            assert connectivity_test["speed_test_down"] > 95.0  # At least 95% of advertised speed
        
        # 5. Customer Activation Notifications
        with patch.object(notification_service, 'send_service_activation_notifications') as mock_activation_notify:
            mock_activation_notify.return_value = {
                "activation_email_sent": True,
                "credentials_delivered": True,
                "portal_access_enabled": True,
                "welcome_call_scheduled": True
            }
            
            activation_notifications = await notification_service.send_service_activation_notifications(
                customer_id,
                {
                    "service_plan": "Fiber Internet 100 Mbps",
                    "username": f"{customer_id}@isp.com",
                    "portal_url": "https://customer.isp.com",
                    "support_number": "1-800-SUPPORT"
                }
            )
            
            assert activation_notifications["activation_email_sent"] is True
            assert activation_notifications["portal_access_enabled"] is True
        
        # 6. Verify Complete Activation State
        activation_status = {
            "physical_installation": installation_result["installation_complete"],
            "network_provisioning": provisioning_result["service_active"],
            "billing_activation": billing_activation["billing_activated"],
            "connectivity_verified": connectivity_test["connectivity_test_passed"],
            "customer_notified": activation_notifications["activation_email_sent"]
        }
        
        # All activation steps must complete successfully
        assert all(activation_status.values(), f"Service activation failed: {activation_status}"


@pytest.mark.integration
@pytest.mark.customer_journey
@pytest.mark.revenue_critical  
class TestServiceOutageResponseWorkflow:
    """Test complete service outage detection and response workflow."""
    
    async def test_network_outage_to_resolution_workflow(self, db_session):
        """Test complete workflow from outage detection to customer resolution."""
        
        # Initialize services
        monitoring_service = NetworkMonitoringService(db_session, "tenant_001")
        support_service = SupportTicketService(db_session, "tenant_001")
        notification_service = NotificationService(db_session, "tenant_001")
        field_ops_service = FieldOperationsService(db_session, "tenant_001")
        customer_service = CustomerService(db_session, "tenant_001")
        
        # 1. Network Monitoring Detects Outage
        outage_detection = {
            "device_id": "core_router_001",
            "device_type": "router",
            "location": "POP_Downtown",
            "alarm_type": "device_unreachable",
            "severity": "critical",
            "affected_services": 150,  # Number of customers affected
            "detection_time": datetime.now(timezone.utc)
        }
        
        with patch.object(monitoring_service, 'detect_network_outage') as mock_detect:
            mock_detect.return_value = {
                "outage_confirmed": True,
                "outage_id": "outage_001",
                "impact_assessment": {
                    "customers_affected": 150,
                    "services_impacted": ["internet", "voip"],
                    "estimated_revenue_impact": Decimal("750.00")  # per hour
                }
            }
            
            outage_info = await monitoring_service.detect_network_outage(outage_detection)
            
            assert outage_info["outage_confirmed"] is True
            assert outage_info["impact_assessment"]["customers_affected"] == 150
        
        # 2. Automatic Support Ticket Creation
        with patch.object(support_service, 'create_outage_ticket') as mock_create_ticket:
            mock_ticket_id = str(uuid4())
            mock_create_ticket.return_value = {
                "ticket_id": mock_ticket_id,
                "priority": "critical",
                "assigned_to": "network_operations",
                "sla_response_time": 15,  # minutes
                "escalation_time": 60     # minutes
            }
            
            outage_ticket = await support_service.create_outage_ticket({
                "outage_id": outage_info["outage_id"],
                "device_id": outage_detection["device_id"],
                "customers_affected": outage_info["impact_assessment"]["customers_affected"]
            })
            
            assert outage_ticket["priority"] == "critical"
            assert outage_ticket["assigned_to"] == "network_operations"
        
        # 3. Mass Customer Notifications  
        with patch.object(notification_service, 'send_outage_notifications') as mock_outage_notify:
            mock_outage_notify.return_value = {
                "notifications_sent": 150,
                "email_notifications": 120,
                "sms_notifications": 145,
                "portal_banner_updated": True,
                "social_media_posted": True
            }
            
            outage_notifications = await notification_service.send_outage_notifications({
                "outage_id": outage_info["outage_id"],
                "affected_customers": outage_info["impact_assessment"]["customers_affected"],
                "estimated_repair_time": "2 hours",
                "services_affected": ["Internet", "VoIP Phone"]
            })
            
            assert outage_notifications["notifications_sent"] == 150
            assert outage_notifications["portal_banner_updated"] is True
        
        # 4. Field Operations Response  
        with patch.object(field_ops_service, 'dispatch_emergency_repair') as mock_dispatch:
            mock_repair_order_id = str(uuid4())
            mock_dispatch.return_value = {
                "repair_order_id": mock_repair_order_id,
                "technicians_dispatched": 2,
                "estimated_arrival": datetime.now(timezone.utc) + timedelta(minutes=45),
                "repair_priority": "emergency",
                "escalation_level": 3
            }
            
            repair_dispatch = await field_ops_service.dispatch_emergency_repair({
                "outage_id": outage_info["outage_id"],
                "device_location": outage_detection["location"],
                "failure_type": "router_failure",
                "customers_impacted": 150
            })
            
            assert repair_dispatch["technicians_dispatched"] == 2
            assert repair_dispatch["repair_priority"] == "emergency"
        
        # 5. Service Restoration
        with patch.object(monitoring_service, 'confirm_service_restoration') as mock_restore:
            mock_restore.return_value = {
                "service_restored": True,
                "restoration_time": datetime.now(timezone.utc),
                "customers_restored": 150,
                "service_quality_verified": True,
                "outage_duration_minutes": 127
            }
            
            restoration_info = await monitoring_service.confirm_service_restoration(
                outage_info["outage_id"]
            )
            
            assert restoration_info["service_restored"] is True
            assert restoration_info["customers_restored"] == 150
        
        # 6. Customer Restoration Notifications
        with patch.object(notification_service, 'send_restoration_notifications') as mock_restore_notify:
            mock_restore_notify.return_value = {
                "restoration_notifications_sent": 150,
                "service_credits_applied": 45,  # Customers who qualify for credits
                "portal_banner_cleared": True,
                "satisfaction_survey_sent": 150
            }
            
            restore_notifications = await notification_service.send_restoration_notifications({
                "outage_id": outage_info["outage_id"], 
                "outage_duration_minutes": 127,
                "customers_affected": 150,
                "credit_policy": "auto_apply_for_outages_over_2_hours"
            })
            
            assert restore_notifications["restoration_notifications_sent"] == 150
            assert restore_notifications["portal_banner_cleared"] is True
        
        # 7. Post-Incident Analysis and Credits
        from dotmac_isp.modules.billing.service import BillingService
        billing_service = BillingService(db_session, "tenant_001")
        
        with patch.object(billing_service, 'process_outage_credits') as mock_credits:
            mock_credits.return_value = {
                "credits_processed": 45,
                "total_credit_amount": Decimal("337.50"),
                "average_credit_per_customer": Decimal("7.50"),
                "credits_applied_to_accounts": True
            }
            
            outage_credits = await billing_service.process_outage_credits({
                "outage_duration_minutes": 127,
                "customers_affected": 150,
                "credit_rate": Decimal("0.05")  # 5% of monthly rate per hour
            })
            
            assert outage_credits["credits_processed"] == 45
            assert outage_credits["total_credit_amount"] == Decimal("337.50")
        
        # 8. Verify Complete Outage Response
        response_completeness = {
            "outage_detected": outage_info["outage_confirmed"],
            "ticket_created": outage_ticket["ticket_id"] is not None,
            "customers_notified": outage_notifications["notifications_sent"] == 150,
            "repairs_dispatched": repair_dispatch["technicians_dispatched"] > 0,
            "service_restored": restoration_info["service_restored"],
            "restoration_notifications": restore_notifications["restoration_notifications_sent"] == 150,
            "credits_processed": outage_credits["credits_processed"] > 0
        }
        
        # Complete outage response workflow must execute successfully
        assert all(response_completeness.values(), f"Outage response incomplete: {response_completeness}"


@pytest.mark.integration  
@pytest.mark.critical
class TestBillingAndPaymentIntegration:
    """Test billing system integration with other modules."""
    
    async def test_monthly_billing_cycle_integration(self, db_session):
        """Test complete monthly billing cycle across all systems."""
        
        # Initialize services
        billing_service = BillingService(db_session, "tenant_001") 
        customer_service = CustomerService(db_session, "tenant_001")
        services_service = ServiceProvisioningService(db_session, "tenant_001")
        notification_service = NotificationService(db_session, "tenant_001")
        analytics_service = AnalyticsService(db_session, "tenant_001")
        
        # Mock customer base for billing cycle
        mock_customers = []
        for i in range(100):
            mock_customers.append({
                "customer_id": f"cust_{i:03d}",
                "billing_cycle": "monthly",
                "next_billing_date": date.today(),
                "services": [
                    {
                        "service_id": f"svc_{i:03d}",
                        "service_type": "internet",
                        "monthly_rate": Decimal("79.99"),
                        "usage_allowance_gb": 1000
                    }
                ]
            })
        
        # 1. Usage Data Collection
        with patch.object(analytics_service, 'collect_monthly_usage_data') as mock_usage:
            mock_usage_data = []
            for customer in mock_customers:
                mock_usage_data.append({
                    "customer_id": customer["customer_id"],
                    "service_id": customer["services"][0]["service_id"],
                    "usage_gb": random.uniform(200, 1200),  # Random usage between 200GB-1200GB
                    "overage_charges": Decimal("0.00")  # Most customers under limit
                })
            
            mock_usage.return_value = mock_usage_data
            
            usage_data = await analytics_service.collect_monthly_usage_data(
                billing_period_start=date.today().replace(day=1),
                billing_period_end=date.today()
            )
            
            assert len(usage_data) == 100
        
        # 2. Invoice Generation
        with patch.object(billing_service, 'generate_monthly_invoices') as mock_generate:
            mock_invoices = []
            total_billing_amount = Decimal("0.00")
            
            for i, customer in enumerate(mock_customers):
                invoice_amount = customer["services"][0]["monthly_rate"]
                # Add usage overages for some customers
                if usage_data[i]["usage_gb"] > 1000:
                    overage_gb = usage_data[i]["usage_gb"] - 1000
                    invoice_amount += overage_gb * Decimal("0.10")  # $0.10 per GB overage
                
                mock_invoices.append({
                    "invoice_id": f"inv_{i:03d}",
                    "customer_id": customer["customer_id"],
                    "total_amount": invoice_amount,
                    "due_date": date.today() + timedelta(days=30),
                    "status": "pending"
                })
                total_billing_amount += invoice_amount
            
            mock_generate.return_value = {
                "invoices_generated": len(mock_invoices),
                "total_billing_amount": total_billing_amount,
                "invoices": mock_invoices
            }
            
            invoice_generation = await billing_service.generate_monthly_invoices()
            
            assert invoice_generation["invoices_generated"] == 100
            assert invoice_generation["total_billing_amount"] > Decimal("7500.00")  # At least $75 average
        
        # 3. Auto-Payment Processing
        with patch.object(billing_service, 'process_auto_payments') as mock_auto_pay:
            auto_pay_customers = 75  # 75% have auto-pay enabled
            successful_payments = 70  # 93% success rate
            
            mock_auto_pay.return_value = {
                "auto_pay_attempts": auto_pay_customers,
                "successful_payments": successful_payments,
                "failed_payments": auto_pay_customers - successful_payments,
                "total_collected": Decimal("5599.25")
            }
            
            auto_payments = await billing_service.process_auto_payments(
                invoice_generation["invoices"]
            )
            
            assert auto_payments["auto_pay_attempts"] == 75
            assert auto_payments["successful_payments"] == 70
        
        # 4. Invoice Delivery Notifications
        with patch.object(notification_service, 'send_invoice_notifications') as mock_invoice_notify:
            mock_invoice_notify.return_value = {
                "email_invoices_sent": 95,
                "paper_invoices_queued": 5,
                "portal_notifications_posted": 100,
                "auto_pay_confirmations_sent": 70
            }
            
            invoice_notifications = await notification_service.send_invoice_notifications(
                invoice_generation["invoices"]
            )
            
            assert invoice_notifications["email_invoices_sent"] == 95
            assert invoice_notifications["portal_notifications_posted"] == 100
        
        # 5. Payment Reminder System
        with patch.object(notification_service, 'schedule_payment_reminders') as mock_reminders:
            unpaid_invoices = 100 - auto_payments["successful_payments"]  # 30 unpaid
            
            mock_reminders.return_value = {
                "payment_reminders_scheduled": unpaid_invoices,
                "reminder_schedule": [
                    {"days_before_due": 7, "method": "email"},
                    {"days_before_due": 3, "method": "email_sms"}, 
                    {"days_before_due": 1, "method": "phone_call"}
                ]
            }
            
            payment_reminders = await notification_service.schedule_payment_reminders(
                unpaid_invoices=unpaid_invoices
            )
            
            assert payment_reminders["payment_reminders_scheduled"] == unpaid_invoices
        
        # 6. Billing Cycle Analytics
        with patch.object(analytics_service, 'generate_billing_cycle_analytics') as mock_analytics:
            mock_analytics.return_value = {
                "total_revenue": total_billing_amount,
                "collection_rate": Decimal("93.3"),  # 70/75 auto-pay success
                "average_revenue_per_user": total_billing_amount / 100,
                "usage_patterns": {
                    "customers_over_limit": 15,
                    "average_usage_gb": 650.5
                },
                "billing_efficiency": {
                    "invoice_generation_time": "12 minutes",
                    "auto_pay_processing_time": "8 minutes"
                }
            }
            
            billing_analytics = await analytics_service.generate_billing_cycle_analytics()
            
            assert billing_analytics["collection_rate"] > Decimal("90.0")
            assert billing_analytics["total_revenue"] == total_billing_amount
        
        # 7. Verify Complete Billing Cycle
        billing_cycle_status = {
            "usage_collected": len(usage_data) == 100,
            "invoices_generated": invoice_generation["invoices_generated"] == 100,
            "auto_payments_processed": auto_payments["successful_payments"] > 0,
            "notifications_sent": invoice_notifications["portal_notifications_posted"] == 100,
            "reminders_scheduled": payment_reminders["payment_reminders_scheduled"] > 0,
            "analytics_generated": billing_analytics["total_revenue"] > Decimal("0")
        }
        
        # Complete billing cycle must execute successfully
        assert all(billing_cycle_status.values(), f"Billing cycle incomplete: {billing_cycle_status}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])