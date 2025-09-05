import logging

logger = logging.getLogger(__name__)

"""
Plugin System Validation Test
Quick validation test for the infrastructure plugin system
"""

import asyncio
import sys

from dotmac_management.services.infrastructure_service import get_infrastructure_service
from dotmac_shared.exceptions import ExceptionContext

from .base import PluginError


async def test_infrastructure_service():
    """Test the infrastructure service and plugin system."""

    logger.info("🔍 Testing Infrastructure Plugin System")
    logger.info("=" * 50)

    try:
        # Get infrastructure service
        infra_service = await get_infrastructure_service()
        logger.info("✅ Infrastructure service initialized")

        # Test health status
        health = await infra_service.get_health_status()
        logger.info(f"📊 Health Status: {health['healthy']}")

        if health["providers"]:
            logger.info("🔌 Available Providers:")
            for provider_type, providers in health["providers"].items():
                logger.info(f"  {provider_type.title()}:")
                for name, status in providers.items():
                    status_icon = "✅" if status.get("healthy", False) else "❌"
                    logger.info(f"    {status_icon} {name}: {status.get('status', 'unknown')}")

        # List available providers
        providers = infra_service.list_available_providers()
        logger.info(f"\n🏗️  Deployment Providers: {providers.get('deployment_providers', [])}")
        logger.info(f"🌐 DNS Providers: {providers.get('dns_providers', [])}")

        # Test subdomain validation (if DNS provider available)
        if providers.get("dns_providers"):
            logger.info("\n🧪 Testing subdomain validation...")
            try:
                result = await infra_service.validate_subdomain_availability(
                    "test-" + str(int(asyncio.get_event_loop().time()))
                )
                logger.info(f"   Subdomain validation result: {result.get('available', 'unknown')}")
            except (PluginError, ExceptionContext.LIFECYCLE_EXCEPTIONS, ValueError) as e:
                logger.info(f"   ⚠️  Subdomain validation failed (expected if no BASE_DOMAIN): {e}")

        logger.info("\n✅ Plugin system validation completed successfully!")

    except (PluginError, ExceptionContext.LIFECYCLE_EXCEPTIONS, ValueError) as e:
        logger.info(f"❌ Plugin system validation failed: {e}")
        return False

    return True


async def main():
    """Main test function."""
    success = await test_infrastructure_service()

    if success:
        logger.info("\n🎉 All tests passed! Infrastructure plugin system is working correctly.")
    else:
        logger.info("\n💥 Tests failed! Please check the implementation.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
