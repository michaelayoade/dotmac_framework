"""
Comprehensive Integration Tests for end-to-end workflows and system integration.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.mark.asyncio
class TestIntegrationComprehensive:
    """Comprehensive integration tests for complete ISP workflows."""

    @pytest.fixture
    def customer_onboarding_data(self):
        """Customer onboarding test data."""
        return {
            "customer_id": "CUST-2024-001",
            "customer_name": "Test Customer Inc",
            "service_type": "business_fiber",
            "bandwidth_tier": "100M",
            "vlan_id": 200,
            "static_ip_block": "203.0.113.0/29",
            "equipment": {
                "ont_serial": "ALCL12345678",
                "router_model": "Cisco ISR4321"
            },
            "location": {
                "address": "123 Business Ave",
                "coordinates": {"lat": 40.7128, "lon": -74.0060},
                "pop_id": "NYC-POP-01"
            }
        }

    async def test_end_to_end_customer_provisioning(self, customer_onboarding_data):
        """Test complete customer provisioning workflow."""
        try:
            from dotmac.networking.workflows.customer_provisioning import (
                CustomerProvisioningWorkflow,
            )
        except ImportError:
            pytest.skip("Customer provisioning workflow not available")

        workflow = CustomerProvisioningWorkflow()

        # Step 1: Network Planning and Resource Allocation
        planning_result = await workflow.plan_network_resources(customer_onboarding_data)

        assert planning_result["status"] == "success"
        assert "vlan_assignment" in planning_result
        assert "ip_allocation" in planning_result
        assert "device_assignments" in planning_result

        # Step 2: IPAM Integration - Allocate IP resources
        ip_allocation = await workflow.allocate_ip_resources({
            "customer_id": customer_onboarding_data["customer_id"],
            "service_type": customer_onboarding_data["service_type"],
            "ip_block": customer_onboarding_data["static_ip_block"]
        })

        assert ip_allocation["status"] == "allocated"
        assert "gateway_ip" in ip_allocation
        assert "usable_range" in ip_allocation
        assert len(ip_allocation["allocated_ips"]) == 6  # /29 has 6 usable IPs

        # Step 3: Device Provisioning - Configure ONT and Router
        device_config = {
            "ont": {
                "serial": customer_onboarding_data["equipment"]["ont_serial"],
                "vlan": planning_result["vlan_assignment"],
                "bandwidth_profile": customer_onboarding_data["bandwidth_tier"]
            },
            "router": {
                "model": customer_onboarding_data["equipment"]["router_model"],
                "wan_ip": ip_allocation["gateway_ip"],
                "lan_network": "192.168.1.0/24"
            }
        }

        provisioning_result = await workflow.provision_customer_equipment(device_config)

        assert provisioning_result["ont"]["status"] == "configured"
        assert provisioning_result["router"]["status"] == "configured"
        assert "configuration_backup_id" in provisioning_result["router"]

        # Step 4: RADIUS Integration - Create customer authentication
        radius_config = {
            "username": f"{customer_onboarding_data['customer_id'].lower()}@isp.local",
            "password": "temp_password_123",
            "vlan_id": planning_result["vlan_assignment"],
            "bandwidth_limit": customer_onboarding_data["bandwidth_tier"],
            "static_ip": ip_allocation["gateway_ip"]
        }

        radius_result = await workflow.configure_radius_authentication(radius_config)

        assert radius_result["status"] == "user_created"
        assert radius_result["username"] == radius_config["username"]

        # Step 5: Monitoring Setup - Add customer to monitoring systems
        monitoring_setup = await workflow.setup_customer_monitoring({
            "customer_id": customer_onboarding_data["customer_id"],
            "devices": [
                {"type": "ont", "ip": "192.168.100.1"},
                {"type": "router", "ip": ip_allocation["gateway_ip"]}
            ],
            "service_level": "business_premium"
        })

        assert monitoring_setup["status"] == "configured"
        assert len(monitoring_setup["monitored_devices"]) == 2

        # Step 6: Complete workflow and verify
        completion_result = await workflow.complete_provisioning(
            customer_onboarding_data["customer_id"]
        )

        assert completion_result["status"] == "completed"
        assert completion_result["service_ready"] == True
        assert "activation_timestamp" in completion_result

    async def test_network_topology_discovery_integration(self):
        """Test network topology discovery and mapping integration."""
        try:
            from dotmac.networking.integration.topology_integration import (
                TopologyIntegration,
            )
        except ImportError:
            pytest.skip("Topology integration not available")

        topology = TopologyIntegration()

        # Step 1: Discover network devices
        discovery_range = "192.168.1.0/24"
        discovered_devices = await topology.discover_network_devices(discovery_range)

        assert len(discovered_devices) > 0
        assert all("ip_address" in device for device in discovered_devices)
        assert all("device_type" in device for device in discovered_devices)

        # Step 2: Map device connections via LLDP/CDP
        device_connections = {}
        for device in discovered_devices[:5]:  # Test first 5 devices
            if device["reachable"]:
                connections = await topology.map_device_connections(device["ip_address"])
                device_connections[device["ip_address"]] = connections

        assert len(device_connections) > 0

        # Step 3: Build network topology graph
        topology_graph = await topology.build_topology_graph(device_connections)

        assert "nodes" in topology_graph
        assert "edges" in topology_graph
        assert len(topology_graph["nodes"]) == len(device_connections)

        # Step 4: Identify network segments and VLANs
        network_segments = await topology.identify_network_segments(topology_graph)

        assert "access_layer" in network_segments
        assert "distribution_layer" in network_segments
        assert "core_layer" in network_segments

        # Step 5: Generate topology visualization data
        visualization_data = await topology.generate_visualization_data(
            topology_graph,
            network_segments
        )

        assert "positions" in visualization_data
        assert "node_colors" in visualization_data
        assert "edge_weights" in visualization_data

    async def test_service_quality_monitoring_integration(self):
        """Test integrated service quality monitoring across all systems."""
        try:
            from dotmac.networking.integration.service_monitoring import (
                ServiceMonitoringIntegration,
            )
        except ImportError:
            pytest.skip("Service monitoring integration not available")

        monitor = ServiceMonitoringIntegration()

        # Step 1: Collect metrics from all monitoring systems
        customer_id = "CUST-2024-001"

        # SNMP metrics from network devices
        snmp_metrics = await monitor.collect_snmp_metrics(customer_id)
        assert "device_health" in snmp_metrics
        assert "interface_utilization" in snmp_metrics
        assert "error_rates" in snmp_metrics

        # RADIUS session metrics
        radius_metrics = await monitor.collect_radius_metrics(customer_id)
        assert "active_sessions" in radius_metrics
        assert "authentication_success_rate" in radius_metrics
        assert "session_duration" in radius_metrics

        # Network performance metrics
        network_metrics = await monitor.collect_network_performance(customer_id)
        assert "latency" in network_metrics
        assert "packet_loss" in network_metrics
        assert "jitter" in network_metrics

        # Step 2: Correlate metrics across systems
        correlated_data = await monitor.correlate_service_metrics(
            snmp_metrics, radius_metrics, network_metrics
        )

        assert "service_health_score" in correlated_data
        assert "performance_indicators" in correlated_data
        assert "anomaly_detection" in correlated_data

        # Step 3: Generate service level reports
        sla_report = await monitor.generate_sla_report(
            customer_id,
            period_days=30
        )

        assert sla_report["availability_percentage"] >= 0
        assert sla_report["performance_metrics"]["average_latency"] >= 0
        assert "sla_violations" in sla_report

        # Step 4: Automated alerting based on thresholds
        alert_rules = [
            {"metric": "availability", "threshold": 99.5, "operator": "<"},
            {"metric": "latency", "threshold": 50, "operator": ">"},
            {"metric": "packet_loss", "threshold": 0.1, "operator": ">"}
        ]

        alerts = await monitor.evaluate_service_alerts(correlated_data, alert_rules)

        # May or may not have alerts based on mock data
        assert isinstance(alerts, list)

    async def test_automated_incident_response_workflow(self):
        """Test automated incident detection and response workflow."""
        try:
            from dotmac.networking.integration.incident_automation import (
                IncidentAutomation,
            )
        except ImportError:
            pytest.skip("Incident automation not available")

        incident_system = IncidentAutomation()

        # Step 1: Simulate network incident (interface down)
        incident_data = {
            "event_type": "interface_down",
            "device_ip": "192.168.1.1",
            "interface": "GigabitEthernet0/1",
            "customer_impact": ["CUST-2024-001", "CUST-2024-002"],
            "timestamp": datetime.now(),
            "severity": "high"
        }

        # Step 2: Automated incident detection
        incident_id = await incident_system.create_incident(incident_data)

        assert incident_id is not None
        assert len(incident_id) > 0

        # Step 3: Impact assessment
        impact_assessment = await incident_system.assess_incident_impact(incident_id)

        assert "affected_customers" in impact_assessment
        assert len(impact_assessment["affected_customers"]) == 2
        assert "service_degradation" in impact_assessment

        # Step 4: Automated remediation attempts
        remediation_result = await incident_system.attempt_auto_remediation(incident_id)

        assert "remediation_steps" in remediation_result
        assert "success" in remediation_result

        # Step 5: If auto-remediation fails, escalate
        if not remediation_result["success"]:
            escalation_result = await incident_system.escalate_incident(
                incident_id,
                escalation_level="network_engineer"
            )

            assert escalation_result["status"] == "escalated"
            assert "assigned_engineer" in escalation_result

        # Step 6: Customer communication automation
        communication_result = await incident_system.notify_affected_customers(
            incident_id,
            message_template="service_disruption"
        )

        assert communication_result["notifications_sent"] == 2
        assert all(notification["status"] == "sent" for notification in communication_result["results"])

    async def test_capacity_planning_integration(self):
        """Test network capacity planning and forecasting integration."""
        try:
            from dotmac.networking.integration.capacity_planning import (
                CapacityPlanningIntegration,
            )
        except ImportError:
            pytest.skip("Capacity planning integration not available")

        capacity_planner = CapacityPlanningIntegration()

        # Step 1: Collect historical utilization data
        historical_data = await capacity_planner.collect_historical_utilization(
            time_range_days=90,
            devices=["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        )

        assert len(historical_data) > 0
        assert all("device_ip" in record for record in historical_data)
        assert all("utilization_data" in record for record in historical_data)

        # Step 2: Analyze growth trends
        growth_analysis = await capacity_planner.analyze_growth_trends(historical_data)

        assert "monthly_growth_rate" in growth_analysis
        assert "peak_utilization_trend" in growth_analysis
        assert "capacity_forecasts" in growth_analysis

        # Step 3: Predict future capacity requirements
        capacity_forecast = await capacity_planner.forecast_capacity_needs(
            growth_analysis,
            forecast_months=12
        )

        assert "predicted_peak_utilization" in capacity_forecast
        assert "capacity_exhaustion_date" in capacity_forecast
        assert "recommended_upgrades" in capacity_forecast

        # Step 4: Generate capacity planning reports
        planning_report = await capacity_planner.generate_capacity_report(
            capacity_forecast,
            budget_constraints={"max_capex": 100000}
        )

        assert "executive_summary" in planning_report
        assert "detailed_recommendations" in planning_report
        assert "budget_impact" in planning_report

        # Step 5: Automated capacity alerting
        capacity_alerts = await capacity_planner.check_capacity_thresholds(
            current_utilization=85,
            warning_threshold=80,
            critical_threshold=90
        )

        assert len(capacity_alerts) > 0  # Should have warning alert
        assert capacity_alerts[0]["severity"] == "warning"

    async def test_multi_vendor_device_integration(self):
        """Test integration across multiple network equipment vendors."""
        try:
            from dotmac.networking.integration.multi_vendor import (
                MultiVendorIntegration,
            )
        except ImportError:
            pytest.skip("Multi-vendor integration not available")

        integration = MultiVendorIntegration()

        # Test devices from different vendors
        test_devices = [
            {"ip": "192.168.1.10", "vendor": "cisco", "model": "ISR4321"},
            {"ip": "192.168.1.11", "vendor": "juniper", "model": "SRX300"},
            {"ip": "192.168.1.12", "vendor": "mikrotik", "model": "CCR1036"},
            {"ip": "192.168.1.13", "vendor": "huawei", "model": "AR6120"}
        ]

        # Step 1: Vendor-specific device discovery
        discovery_results = {}
        for device in test_devices:
            result = await integration.discover_device_capabilities(
                device["ip"], device["vendor"]
            )
            discovery_results[device["ip"]] = result

            assert "supported_features" in result
            assert "management_protocols" in result
            assert "configuration_methods" in result

        # Step 2: Normalized configuration deployment
        config_template = {
            "hostname": "test-device-{{ loop.index }}",
            "management_vlan": 10,
            "snmp_community": "monitoring",
            "ntp_servers": ["192.168.1.100", "192.168.1.101"]
        }

        deployment_results = {}
        for device in test_devices:
            result = await integration.deploy_normalized_config(
                device["ip"],
                device["vendor"],
                config_template
            )
            deployment_results[device["ip"]] = result

            assert result["status"] in ["success", "partial", "failed"]
            if result["status"] == "success":
                assert "vendor_specific_config" in result

        # Step 3: Unified monitoring across vendors
        monitoring_results = await integration.setup_unified_monitoring(test_devices)

        assert len(monitoring_results) == len(test_devices)
        assert all("monitoring_status" in result for result in monitoring_results)

        # Step 4: Cross-vendor performance comparison
        performance_comparison = await integration.compare_vendor_performance(
            test_devices,
            metrics=["cpu_utilization", "memory_usage", "throughput"]
        )

        assert "vendor_rankings" in performance_comparison
        assert "performance_metrics" in performance_comparison
        assert len(performance_comparison["vendor_rankings"]) > 0

    async def test_billing_integration_workflow(self):
        """Test integration with customer billing systems."""
        try:
            from dotmac.networking.integration.billing_integration import (
                BillingIntegration,
            )
        except ImportError:
            pytest.skip("Billing integration not available")

        billing = BillingIntegration()

        # Step 1: Collect usage data from RADIUS accounting
        customer_id = "CUST-2024-001"
        usage_data = await billing.collect_customer_usage(
            customer_id,
            period_start=datetime.now() - timedelta(days=30),
            period_end=datetime.now()
        )

        assert "total_data_usage" in usage_data
        assert "session_count" in usage_data
        assert "peak_concurrent_sessions" in usage_data
        assert usage_data["total_data_usage"]["bytes"] >= 0

        # Step 2: Apply billing rules and calculate charges
        billing_rules = {
            "base_monthly_fee": 99.99,
            "data_allowance_gb": 1000,
            "overage_rate_per_gb": 5.00,
            "peak_hour_multiplier": 1.5
        }

        billing_calculation = await billing.calculate_charges(
            usage_data,
            billing_rules
        )

        assert "base_charges" in billing_calculation
        assert "usage_charges" in billing_calculation
        assert "total_amount" in billing_calculation
        assert billing_calculation["total_amount"] >= billing_rules["base_monthly_fee"]

        # Step 3: Generate detailed billing report
        billing_report = await billing.generate_customer_bill(
            customer_id,
            billing_calculation,
            usage_data
        )

        assert "bill_id" in billing_report
        assert "line_items" in billing_report
        assert "usage_summary" in billing_report
        assert len(billing_report["line_items"]) >= 1

        # Step 4: Integration with payment processing
        payment_result = await billing.process_payment_integration(
            billing_report["bill_id"],
            payment_method="auto_pay_cc"
        )

        assert "payment_status" in payment_result
        assert payment_result["payment_status"] in ["processed", "pending", "failed"]

    async def test_compliance_and_reporting_integration(self):
        """Test regulatory compliance and reporting integration."""
        try:
            from dotmac.networking.integration.compliance_reporting import (
                ComplianceReporting,
            )
        except ImportError:
            pytest.skip("Compliance reporting not available")

        compliance = ComplianceReporting()

        # Step 1: Data retention compliance
        retention_policies = {
            "radius_logs": {"retention_days": 365, "archive_after_days": 90},
            "network_configs": {"retention_days": 2555, "versions_to_keep": 10},
            "security_events": {"retention_days": 2555, "archive_after_days": 365}
        }

        retention_status = await compliance.check_data_retention_compliance(retention_policies)

        assert "compliant" in retention_status
        assert "retention_summary" in retention_status
        assert "non_compliant_items" in retention_status

        # Step 2: Privacy compliance (GDPR, CCPA)
        privacy_audit = await compliance.audit_privacy_compliance([
            "CUST-2024-001", "CUST-2024-002"
        ])

        assert "gdpr_compliance" in privacy_audit
        assert "data_subject_rights" in privacy_audit
        assert "consent_records" in privacy_audit

        # Step 3: Security compliance reporting
        security_report = await compliance.generate_security_compliance_report(
            frameworks=["SOC2", "ISO27001", "NIST"]
        )

        assert len(security_report) == 3  # One report per framework
        assert all("framework" in report for report in security_report)
        assert all("compliance_score" in report for report in security_report)

        # Step 4: Automated compliance monitoring
        compliance_alerts = await compliance.monitor_compliance_violations(
            monitoring_period_days=7
        )

        # May or may not have violations
        assert isinstance(compliance_alerts, list)
        if len(compliance_alerts) > 0:
            assert all("violation_type" in alert for alert in compliance_alerts)
            assert all("severity" in alert for alert in compliance_alerts)


# Mock implementations for integration workflows
integration_mocks = {
    'CustomerProvisioningWorkflow': {
        'plan_network_resources': lambda self, data: {
            "status": "success", "vlan_assignment": 200, "ip_allocation": "203.0.113.0/29", "device_assignments": ["ont-1", "router-1"]
        },
        'allocate_ip_resources': lambda self, data: {
            "status": "allocated", "gateway_ip": "203.0.113.1", "usable_range": "203.0.113.2-203.0.113.6",
            "allocated_ips": ["203.0.113.2", "203.0.113.3", "203.0.113.4", "203.0.113.5", "203.0.113.6", "203.0.113.7"]
        },
        'provision_customer_equipment': lambda self, config: {
            "ont": {"status": "configured"}, "router": {"status": "configured", "configuration_backup_id": "backup-123"}
        },
        'configure_radius_authentication': lambda self, config: {"status": "user_created", "username": config["username"]},
        'setup_customer_monitoring': lambda self, config: {
            "status": "configured", "monitored_devices": [{"type": "ont"}, {"type": "router"}]
        },
        'complete_provisioning': lambda self, customer_id: {
            "status": "completed", "service_ready": True, "activation_timestamp": datetime.now()
        }
    },
    'TopologyIntegration': {
        'discover_network_devices': lambda self, range_cidr: [
            {"ip_address": f"192.168.1.{i}", "device_type": "router", "reachable": True} for i in range(1, 6)
        ],
        'map_device_connections': lambda self, ip: [{"neighbor": "192.168.1.2", "interface": "GigE0/1"}],
        'build_topology_graph': lambda self, connections: {
            "nodes": list(connections.keys()), "edges": [(k, v[0]["neighbor"]) for k, v in connections.items() if v]
        },
        'identify_network_segments': lambda self, graph: {
            "access_layer": graph["nodes"][:2], "distribution_layer": graph["nodes"][2:4], "core_layer": graph["nodes"][4:]
        },
        'generate_visualization_data': lambda self, graph, segments: {
            "positions": {node: [i*100, i*50] for i, node in enumerate(graph["nodes"])},
            "node_colors": dict.fromkeys(graph["nodes"], "blue"),
            "edge_weights": dict.fromkeys(graph["edges"], 1.0)
        }
    },
    'ServiceMonitoringIntegration': {
        'collect_snmp_metrics': lambda self, customer_id: {
            "device_health": 95, "interface_utilization": 65, "error_rates": 0.01
        },
        'collect_radius_metrics': lambda self, customer_id: {
            "active_sessions": 5, "authentication_success_rate": 99.5, "session_duration": 14400
        },
        'collect_network_performance': lambda self, customer_id: {
            "latency": 15.5, "packet_loss": 0.05, "jitter": 2.1
        },
        'correlate_service_metrics': lambda self, snmp, radius, network: {
            "service_health_score": 87.5, "performance_indicators": {"excellent": 3, "good": 2, "poor": 0},
            "anomaly_detection": {"anomalies_detected": 0}
        },
        'generate_sla_report': lambda self, customer_id, period_days: {
            "availability_percentage": 99.95, "performance_metrics": {"average_latency": 12.3},
            "sla_violations": []
        },
        'evaluate_service_alerts': lambda self, data, rules: []  # No alerts in mock
    },
    'IncidentAutomation': {
        'create_incident': lambda self, data: f"INC-{datetime.now().strftime('%Y%m%d')}-001",
        'assess_incident_impact': lambda self, incident_id: {
            "affected_customers": ["CUST-2024-001", "CUST-2024-002"], "service_degradation": "moderate"
        },
        'attempt_auto_remediation': lambda self, incident_id: {
            "remediation_steps": ["interface_restart", "routing_update"], "success": True
        },
        'escalate_incident': lambda self, incident_id, escalation_level: {
            "status": "escalated", "assigned_engineer": "john.doe@isp.com"
        },
        'notify_affected_customers': lambda self, incident_id, message_template: {
            "notifications_sent": 2, "results": [{"customer": "CUST-2024-001", "status": "sent"}, {"customer": "CUST-2024-002", "status": "sent"}]
        }
    }
}

# Additional integration mocks
additional_integration_mocks = {
    'CapacityPlanningIntegration': {
        'collect_historical_utilization': lambda self, time_range_days, devices: [
            {"device_ip": device, "utilization_data": [{"timestamp": datetime.now() - timedelta(days=i), "utilization": 50 + i} for i in range(10)]}
            for device in devices
        ],
        'analyze_growth_trends': lambda self, data: {
            "monthly_growth_rate": 2.5, "peak_utilization_trend": "increasing", "capacity_forecasts": {"6_months": 78, "12_months": 85}
        },
        'forecast_capacity_needs': lambda self, analysis, forecast_months: {
            "predicted_peak_utilization": 92, "capacity_exhaustion_date": datetime.now() + timedelta(days=180),
            "recommended_upgrades": ["upgrade_core_switches", "add_fiber_capacity"]
        },
        'generate_capacity_report': lambda self, forecast, budget_constraints: {
            "executive_summary": "Capacity adequate for 6 months", "detailed_recommendations": ["Upgrade in Q3"],
            "budget_impact": {"estimated_cost": 75000}
        },
        'check_capacity_thresholds': lambda self, current_utilization, warning_threshold, critical_threshold: [
            {"severity": "warning", "metric": "utilization", "current": current_utilization, "threshold": warning_threshold}
        ] if current_utilization > warning_threshold else []
    },
    'MultiVendorIntegration': {
        'discover_device_capabilities': lambda self, ip, vendor: {
            "supported_features": ["snmp", "ssh", "netconf"], "management_protocols": ["cli", "api"],
            "configuration_methods": ["template", "direct"]
        },
        'deploy_normalized_config': lambda self, ip, vendor, template: {
            "status": "success", "vendor_specific_config": f"{vendor}_specific_commands"
        },
        'setup_unified_monitoring': lambda self, devices: [
            {"device": device["ip"], "monitoring_status": "active"} for device in devices
        ],
        'compare_vendor_performance': lambda self, devices, metrics: {
            "vendor_rankings": {"cisco": 1, "juniper": 2, "mikrotik": 3, "huawei": 4},
            "performance_metrics": {metric: {"cisco": 85, "juniper": 82} for metric in metrics}
        }
    },
    'BillingIntegration': {
        'collect_customer_usage': lambda self, customer_id, period_start, period_end: {
            "total_data_usage": {"bytes": 50000000000}, "session_count": 120, "peak_concurrent_sessions": 3
        },
        'calculate_charges': lambda self, usage_data, billing_rules: {
            "base_charges": billing_rules["base_monthly_fee"], "usage_charges": 15.00,
            "total_amount": billing_rules["base_monthly_fee"] + 15.00
        },
        'generate_customer_bill': lambda self, customer_id, calculation, usage_data: {
            "bill_id": f"BILL-{customer_id}-{datetime.now().strftime('%Y%m')}",
            "line_items": [{"description": "Base Service", "amount": calculation["base_charges"]}],
            "usage_summary": usage_data
        },
        'process_payment_integration': lambda self, bill_id, payment_method: {"payment_status": "processed"}
    },
    'ComplianceReporting': {
        'check_data_retention_compliance': lambda self, policies: {
            "compliant": True, "retention_summary": {"total_policies": len(policies), "compliant_policies": len(policies)},
            "non_compliant_items": []
        },
        'audit_privacy_compliance': lambda self, customer_ids: {
            "gdpr_compliance": True, "data_subject_rights": {"fulfilled": len(customer_ids)},
            "consent_records": {"valid": len(customer_ids)}
        },
        'generate_security_compliance_report': lambda self, frameworks: [
            {"framework": fw, "compliance_score": 85, "findings": []} for fw in frameworks
        ],
        'monitor_compliance_violations': lambda self, monitoring_period_days: []
    }
}

# Create all integration mock classes
all_integration_mocks = {**integration_mocks, **additional_integration_mocks}

for class_name, methods in all_integration_mocks.items():
    if class_name not in globals():
        class_attrs = {'__init__': lambda self: None}

        for method_name, method_impl in methods.items():
            # Convert all methods to async
            def make_async_method(impl):
                async def async_method(self, *args, **kwargs):
                    return impl(self, *args, **kwargs)
                return async_method

            class_attrs[method_name] = make_async_method(method_impl)

        mock_class = type(f'Mock{class_name}', (), class_attrs)
        globals()[class_name] = mock_class
