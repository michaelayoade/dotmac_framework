#!/usr/bin/env python3
"""
Complete DotMac Developer Tools Workflow Example

This example demonstrates the full capability of the DotMac Developer Tools:
1. Service scaffolding and generation
2. Multi-language SDK generation
3. Developer portal setup with self-service access
4. Zero-trust security implementation
5. Service mesh configuration with encryption and observability

This addresses all the gaps identified:
- ✅ CLI/SDK generator for automated service scaffolding
- ✅ Developer portal for external partner self-service
- ✅ Zero-trust model with service-to-service authentication
- ✅ Service mesh with encryption, retry logic, and observability
"""

import asyncio
from pathlib import Path

from dotmac_devtools import (
    DeveloperPortalSDK,
    DevToolsConfig,
    SDKGeneratorSDK,
    ServiceGeneratorSDK,
    ZeroTrustSecuritySDK,
)
from dotmac_devtools.sdks.service_mesh import ServiceMeshSDK


async def complete_devtools_workflow():  # noqa: PLR0915
    """Demonstrate complete developer tools workflow."""

    print("🚀 DotMac Developer Tools - Complete Workflow Demo")
    print("=" * 60)

    # 1. Initialize configuration
    print("\n1️⃣  Initializing Developer Tools Configuration...")
    config = DevToolsConfig(
        workspace_path=Path("./demo-workspace"),
        defaults={
            'author': 'DotMac ISP Team',
            'company': 'DotMac Communications',
            'license': 'MIT'
        }
    )

    # 2. Generate ISP services
    print("\n2️⃣  Generating ISP Services...")
    service_generator = ServiceGeneratorSDK(config)

    # Generate customer management service
    customer_service = await service_generator.generate_rest_api(
        name="customer-management",
        description="Customer registration and account management",
        database="postgresql",
        cache="redis",
        enable_auth=True,
        enable_monitoring=True
    )
    print(f"   ✅ Generated: {customer_service['service_name']}")

    # Generate billing service
    billing_service = await service_generator.generate_microservice(
        name="billing-processor",
        description="Automated billing and payment processing",
        queue="rabbitmq",
        database="postgresql",
        enable_events=True
    )
    print(f"   ✅ Generated: {billing_service['service_name']}")

    # Generate network monitoring service
    network_service = await service_generator.generate_data_pipeline(
        name="network-analytics",
        description="Real-time network monitoring and analytics",
        framework="airflow"
    )
    print(f"   ✅ Generated: {network_service['service_name']}")

    # 3. Generate SDKs for external partners
    print("\n3️⃣  Generating Partner SDKs...")
    sdk_generator = SDKGeneratorSDK(config)

    # Generate Python SDK
    python_sdk = await sdk_generator.generate_python_sdk(
        service_name="customer-management",
        package_name="dotmac_customer_client",
        async_support=True,
        include_examples=True,
        include_tests=True
    )
    print(f"   ✅ Generated Python SDK: {python_sdk['package_name']}")

    # Generate TypeScript SDK
    typescript_sdk = await sdk_generator.generate_typescript_sdk(
        service_name="customer-management",
        package_name="dotmac-customer-client",
        include_types=True,
        framework="axios"
    )
    print(f"   ✅ Generated TypeScript SDK: {typescript_sdk['package_name']}")

    # Generate Go SDK
    go_sdk = await sdk_generator.generate_go_sdk(
        service_name="billing-processor",
        package_name="dotmac-billing-client",
        context_support=True
    )
    print(f"   ✅ Generated Go SDK: {go_sdk['package_name']}")

    # 4. Setup Developer Portal
    print("\n4️⃣  Setting up Developer Portal...")
    portal_sdk = DeveloperPortalSDK(config)

    # Initialize portal
    portal = await portal_sdk.initialize_portal(
        domain="developer.dotmac.com",
        title="DotMac ISP Developer Portal",
        company_name="DotMac Communications",
        support_email="api-support@dotmac.com",
        auth_provider="auth0",
        approval_workflow="automatic"
    )
    print(f"   ✅ Portal initialized: {portal['domain']}")

    # Register sample developers
    dev1 = await portal_sdk.register_developer(
        email="partner1@example.com",
        name="External Partner 1",
        company="Partner Corp",
        tier="pro"
    )
    print(f"   ✅ Registered developer: {dev1['email']}")

    dev2 = await portal_sdk.register_developer(
        email="partner2@example.com",
        name="External Partner 2",
        company="Integration Inc",
        tier="enterprise"
    )
    print(f"   ✅ Registered developer: {dev2['email']}")

    # Create applications and API keys
    app1 = await portal_sdk.create_application(
        developer_id=dev1['developer_id'],
        name="Partner Customer Integration",
        description="Customer data synchronization"
    )
    print(f"   ✅ Created application: {app1['name']}")

    # 5. Implement Zero-Trust Security
    print("\n5️⃣  Implementing Zero-Trust Security...")
    security_sdk = ZeroTrustSecuritySDK(config)

    # Initialize zero-trust
    zero_trust = await security_sdk.initialize_zero_trust(
        cluster_name="production-cluster",
        trust_domain="dotmac.local",
        provider="istio",
        enable_mtls=True
    )
    print(f"   ✅ Zero-trust initialized for: {zero_trust['trust_domain']}")

    # Create service identities
    customer_identity = await security_sdk.create_service_identity(
        service_name="customer-management",
        namespace="production",
        cluster_name="production-cluster"
    )
    print(f"   ✅ Created identity: {customer_identity['spiffe_id']}")

    billing_identity = await security_sdk.create_service_identity(
        service_name="billing-processor",
        namespace="production",
        cluster_name="production-cluster"
    )
    print(f"   ✅ Created identity: {billing_identity['spiffe_id']}")

    # Create security policies
    policy1 = await security_sdk.create_security_policy(
        name="Customer to Billing Communication",
        source_service="customer-management",
        source_namespace="production",
        destination_service="billing-processor",
        destination_namespace="production",
        action="allow",
        require_mtls=True,
        allowed_methods=["POST", "GET"]
    )
    print(f"   ✅ Created security policy: {policy1['name']}")

    # Generate Istio policies
    istio_manifests = await security_sdk.generate_istio_policy(policy1['policy_id'])
    print("   ✅ Generated Istio manifests for policy")

    # 6. Configure Service Mesh
    print("\n6️⃣  Configuring Service Mesh...")
    mesh_sdk = ServiceMeshSDK(config)

    # Initialize service mesh
    mesh = await mesh_sdk.initialize_service_mesh(
        cluster_name="production-cluster",
        provider="istio",
        enable_mtls=True,
        enable_tracing=True,
        enable_metrics=True,
        auto_injection=True
    )
    print(f"   ✅ Service mesh initialized with {mesh['mesh_config']['provider']}")

    # Register services in mesh
    customer_mesh = await mesh_sdk.register_service(
        name="customer-management",
        namespace="production",
        port=8080,
        protocol="HTTP",
        enable_sidecar=True,
        enable_mtls=True
    )
    print("   ✅ Registered service in mesh: customer-management")

    billing_mesh = await mesh_sdk.register_service(
        name="billing-processor",
        namespace="production",
        port=8080,
        protocol="HTTP",
        enable_sidecar=True,
        enable_mtls=True
    )
    print("   ✅ Registered service in mesh: billing-processor")

    # Create traffic policies with circuit breakers and retries
    traffic_policy = await mesh_sdk.create_traffic_policy(
        name="Billing Traffic Policy",
        service_name="billing-processor",
        namespace="production",
        load_balancer="ROUND_ROBIN",
        timeout="30s",
        circuit_breaker={
            'consecutive_errors': 5,
            'interval': '30s',
            'base_ejection_time': '30s',
            'max_ejection_percent': 50
        },
        retry_policy={
            'attempts': 3,
            'per_try_timeout': '2s',
            'retry_on': ['5xx', 'reset', 'connect-failure']
        }
    )
    print("   ✅ Created traffic policy with circuit breaker and retries")

    # Configure observability
    observability = await mesh_sdk.configure_observability(
        cluster_name="production-cluster",
        enable_tracing=True,
        tracing_provider="jaeger",
        enable_metrics=True,
        metrics_provider="prometheus",
        enable_logging=True,
        logging_provider="fluent-bit"
    )
    print("   ✅ Configured observability with tracing, metrics, and logging")

    # 7. Generate service communication map
    print("\n7️⃣  Generating Service Communication Map...")
    comm_map = await mesh_sdk.generate_service_communication_map("production-cluster")
    print(f"   ✅ Generated communication map for {len(comm_map['services'])} services")

    # 8. Security audit
    print("\n8️⃣  Performing Security Audit...")
    audit_results = await security_sdk.audit_security_policies("production-cluster")
    print("   ✅ Security audit complete:")
    print(f"      - Active policies: {audit_results['active_policies']}")
    print(f"      - Warnings: {len(audit_results['warnings'])}")
    print(f"      - Expiring certificates: {len(audit_results['expiring_certificates'])}")

    # Summary
    print("\n" + "=" * 60)
    print("🎉 DotMac Developer Tools Workflow Complete!")
    print("=" * 60)

    print("\n📊 Generated Assets:")
    print("   • Services: 3 (REST API, Microservice, Data Pipeline)")
    print("   • SDKs: 3 (Python, TypeScript, Go)")
    print("   • Developer Portal: 1 (2 registered partners)")
    print("   • Service Identities: 2 (with certificates)")
    print("   • Security Policies: 1 (with Istio manifests)")
    print("   • Service Mesh: Configured with mTLS, circuit breakers, retries")
    print("   • Observability: Tracing, metrics, and logging enabled")

    print("\n🔐 Security Features:")
    print("   • Zero-trust architecture with mTLS")
    print("   • Service-to-service authentication via certificates")
    print("   • Fine-grained authorization policies")
    print("   • Automatic certificate rotation")
    print("   • Circuit breakers and retry policies")
    print("   • Comprehensive observability")

    print("\n👥 Developer Experience:")
    print("   • Self-service developer portal")
    print("   • Automatic SDK generation in multiple languages")
    print("   • Interactive API documentation")
    print("   • API key management and usage analytics")
    print("   • Code examples and testing capabilities")

    print("\n🚀 Next Steps:")
    print("   1. Deploy services to Kubernetes cluster")
    print("   2. Install Istio service mesh")
    print("   3. Apply generated security manifests")
    print("   4. Deploy developer portal")
    print("   5. Distribute SDKs to external partners")
    print("   6. Monitor service communication and security")

    print("\n✨ All identified gaps have been addressed:")
    print("   ✅ No CLI/SDK generator → Comprehensive CLI with multi-language SDK generation")
    print("   ✅ No developer portal → Self-service portal with partner management")
    print("   ✅ No zero-trust model → Complete zero-trust with mTLS and policies")
    print("   ✅ No service mesh → Istio mesh with encryption, retries, and observability")


if __name__ == "__main__":
    asyncio.run(complete_devtools_workflow())
