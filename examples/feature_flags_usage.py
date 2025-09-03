"""
Feature Flags Usage Examples for DotMac Framework
Demonstrates common patterns and best practices
"""
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Request
from typing import Dict, Any

from dotmac_shared.feature_flags import (
    FeatureFlagClient, FeatureFlagManager, FeatureFlagMiddleware,
    feature_flag, requires_feature, ab_test, create_feature_flag_router
)
from dotmac_shared.feature_flags.decorators import set_global_manager, fastapi_context_extractor

# Example 1: Basic Setup
async def basic_setup_example():
    """Basic feature flag client setup"""
    
    # Create client with Redis storage
    async with FeatureFlagClient(
        storage_type="redis",
        storage_config={"redis_url": "redis://localhost:6379"},
        environment="development",
        service_name="isp-service"
    ) as client:
        
        # Create a simple on/off flag
        await client.create_simple_flag(
            key="new_dashboard",
            name="New Dashboard UI",
            description="Enable the redesigned dashboard interface",
            enabled=False,
            tags=["ui", "dashboard"]
        )
        
        # Create a percentage rollout flag
        await client.create_percentage_flag(
            key="performance_optimization",
            name="Performance Optimizations",
            percentage=25.0,  # 25% of users
            description="Enable new performance optimizations",
            tags=["performance"]
        )
        
        # Check if feature is enabled
        context = {"user_id": "user_123", "tenant_id": "tenant_abc"}
        is_enabled = await client.is_enabled("new_dashboard", context)
        print(f"New dashboard enabled for user: {is_enabled}")


# Example 2: Gradual Rollout
async def gradual_rollout_example():
    """Demonstrate gradual rollout functionality"""
    
    async with FeatureFlagClient(storage_type="memory") as client:
        
        # Create a gradual rollout flag
        await client.create_gradual_rollout_flag(
            key="new_billing_system",
            name="New Billing System",
            duration_hours=48,  # 48 hour rollout
            start_percentage=0.0,
            end_percentage=100.0,
            description="Gradual rollout of new billing system",
            tags=["billing", "backend"]
        )
        
        # Check current rollout status
        flag_info = await client.get_flag_info("new_billing_system")
        if flag_info and flag_info.get("gradual_rollout"):
            rollout = flag_info["gradual_rollout"]
            current_pct = rollout.get("current_percentage", 0)
            print(f"Current rollout percentage: {current_pct:.1f}%")


# Example 3: A/B Testing
async def ab_testing_example():
    """Demonstrate A/B testing functionality"""
    
    async with FeatureFlagClient(storage_type="memory") as client:
        
        # Create an A/B test with multiple variants
        await client.create_ab_test_flag(
            key="checkout_flow_test",
            name="Checkout Flow A/B Test",
            variants=[
                {
                    "name": "control",
                    "percentage": 50.0,
                    "payload": {"flow_type": "original", "steps": 3}
                },
                {
                    "name": "simplified",
                    "percentage": 30.0,
                    "payload": {"flow_type": "simplified", "steps": 2}
                },
                {
                    "name": "enhanced", 
                    "percentage": 20.0,
                    "payload": {"flow_type": "enhanced", "steps": 4, "upsells": True}
                }
            ],
            description="Test different checkout flows",
            tags=["checkout", "conversion"]
        )
        
        # Test variant assignment for different users
        for user_id in ["user_1", "user_2", "user_3", "user_4"]:
            context = {"user_id": user_id}
            variant = await client.get_variant("checkout_flow_test", context)
            payload = await client.get_payload("checkout_flow_test", context)
            print(f"User {user_id}: variant={variant}, payload={payload}")


# Example 4: FastAPI Integration
def create_fastapi_app():
    """Create FastAPI app with feature flag integration"""
    
    app = FastAPI(title="Feature Flag Demo")
    
    # Initialize feature flag client
    client = None
    
    @app.on_event("startup")
    async def startup():
        nonlocal client
        client = await FeatureFlagClient(
            storage_type="redis",
            environment="development"
        ).__aenter__()
        
        # Set global manager for decorators
        set_global_manager(client.manager)
        
        # Add middleware
        app.add_middleware(
            FeatureFlagMiddleware,
            manager=client.manager,
            context_extractor=fastapi_context_extractor
        )
    
    @app.on_event("shutdown")
    async def shutdown():
        if client:
            await client.__aexit__(None, None, None)
    
    # Add feature flag management routes
    app.include_router(create_feature_flag_router(client))
    
    # Example endpoint using decorators
    @app.get("/dashboard")
    @feature_flag("new_dashboard", fallback_enabled=False)
    async def get_dashboard():
        return {"dashboard": "new_design", "version": "2.0"}
    
    @app.get("/premium-feature")
    @requires_feature("premium_features", error_message="Premium feature not available")
    async def premium_feature():
        return {"feature": "premium", "available": True}
    
    # A/B test endpoint
    @app.get("/checkout")
    @ab_test(
        "checkout_flow_test",
        variants={
            "control": lambda: {"flow": "original", "steps": 3},
            "simplified": lambda: {"flow": "simplified", "steps": 2},
            "enhanced": lambda: {"flow": "enhanced", "steps": 4}
        },
        default_variant="control"
    )
    async def checkout():
        # This will never be called directly - variants handle the response
        pass
    
    return app


# Example 5: Manual Feature Flag Checks
async def manual_checks_example():
    """Demonstrate manual feature flag checking"""
    
    async with FeatureFlagClient(storage_type="memory") as client:
        
        # Create flags for testing
        await client.create_simple_flag("feature_a", "Feature A", enabled=True)
        await client.create_percentage_flag("feature_b", "Feature B", percentage=50.0)
        
        # Create user list flag
        await client.create_user_list_flag(
            "beta_features", 
            "Beta Features",
            user_list=["beta_user_1", "beta_user_2", "power_user_123"]
        )
        
        # Test different contexts
        contexts = [
            {"user_id": "regular_user"},
            {"user_id": "beta_user_1"},
            {"user_id": "power_user_123", "user_tier": "premium"},
        ]
        
        for context in contexts:
            print(f"\nContext: {context}")
            
            # Check each flag
            for flag_key in ["feature_a", "feature_b", "beta_features"]:
                enabled = await client.is_enabled(flag_key, context)
                print(f"  {flag_key}: {enabled}")


# Example 6: Advanced Targeting Rules
async def targeting_rules_example():
    """Demonstrate advanced targeting rules"""
    
    async with FeatureFlagClient(storage_type="memory") as client:
        
        # Create a flag with complex targeting
        await client.create_simple_flag(
            "enterprise_features",
            "Enterprise Features",
            enabled=False  # Start disabled
        )
        
        # Add targeting rules
        await client.add_targeting_rule(
            "enterprise_features",
            attribute="user_tier",
            operator="equals",
            value="enterprise",
            description="Enable for enterprise tier users"
        )
        
        await client.add_targeting_rule(
            "enterprise_features", 
            attribute="signup_date",
            operator="less_than",
            value="2024-01-01",
            description="Enable for users who signed up before 2024"
        )
        
        # Test targeting
        contexts = [
            {"user_id": "user1", "user_tier": "basic"},
            {"user_id": "user2", "user_tier": "enterprise"},
            {"user_id": "user3", "user_tier": "enterprise", "signup_date": "2023-06-15"},
            {"user_id": "user4", "user_tier": "premium", "signup_date": "2023-12-01"},
        ]
        
        for context in contexts:
            enabled = await client.is_enabled("enterprise_features", context)
            print(f"Enterprise features for {context}: {enabled}")


# Example 7: Flag Management Operations
async def management_operations_example():
    """Demonstrate flag management operations"""
    
    async with FeatureFlagClient(storage_type="memory") as client:
        
        # Create some test flags
        flags_config = {
            "ui_refresh": {
                "name": "UI Refresh",
                "description": "New UI design",
                "strategy": "percentage",
                "percentage": 10.0,
                "tags": ["ui"]
            },
            "api_v2": {
                "name": "API v2",
                "description": "New API version",
                "strategy": "user_list",
                "user_list": ["dev_user_1", "dev_user_2"],
                "tags": ["api", "backend"]
            }
        }
        
        # Bulk create flags
        results = await client.create_flags_from_config(flags_config)
        print(f"Bulk creation results: {results}")
        
        # List all flags
        all_flags = await client.list_flags()
        print(f"\nAll flags ({len(all_flags)}):")
        for flag in all_flags:
            print(f"  {flag['key']}: {flag['strategy']} ({flag['status']})")
        
        # List flags by tag
        ui_flags = await client.list_flags(tags=["ui"])
        print(f"\nUI flags: {[f['key'] for f in ui_flags]}")
        
        # Update flag percentage
        await client.update_flag_percentage("ui_refresh", 25.0)
        
        # Enable/disable flags
        await client.enable_flag("api_v2")
        await client.disable_flag("ui_refresh")
        
        # Export configuration
        config = await client.export_flags()
        print(f"\nExported config has {len(config['flags'])} flags")


# Example 8: Testing with Feature Flags
async def testing_example():
    """Demonstrate testing patterns with feature flags"""
    
    async with FeatureFlagClient(storage_type="memory") as client:
        
        # Create a flag for testing
        await client.create_simple_flag("test_feature", "Test Feature", enabled=False)
        
        # Test with feature disabled
        context = {"user_id": "test_user"}
        enabled = await client.is_enabled("test_feature", context)
        print(f"Feature initially disabled: {enabled}")
        
        # Use override for testing
        async with client.override_flag_for_testing("test_feature", enabled=True):
            enabled = await client.is_enabled("test_feature", context)
            print(f"Feature overridden to enabled: {enabled}")
        
        # After override, back to original state
        enabled = await client.is_enabled("test_feature", context)
        print(f"Feature after override: {enabled}")


# Run examples
async def main():
    """Run all examples"""
    print("=== Feature Flags Usage Examples ===\n")
    
    print("1. Basic Setup Example:")
    await basic_setup_example()
    
    print("\n2. Gradual Rollout Example:")
    await gradual_rollout_example()
    
    print("\n3. A/B Testing Example:")
    await ab_testing_example()
    
    print("\n4. Manual Checks Example:")
    await manual_checks_example()
    
    print("\n5. Targeting Rules Example:")
    await targeting_rules_example()
    
    print("\n6. Management Operations Example:")
    await management_operations_example()
    
    print("\n7. Testing Example:")
    await testing_example()


if __name__ == "__main__":
    asyncio.run(main())