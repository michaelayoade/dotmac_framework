#!/usr/bin/env python3
"""
Demo Tenant Cleanup Service
Nightly job to deprovision expired demo tenants
"""

import asyncio
import os
from datetime import datetime
from typing import Any

import httpx

# Configuration
MANAGEMENT_API_URL = os.getenv("MANAGEMENT_API_URL", "https://mgmt.yourdomain.com")
MANAGEMENT_SERVICE_TOKEN = os.getenv("MANAGEMENT_SERVICE_TOKEN")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


async def get_expired_demos() -> list[dict[str, Any]]:
    """Get list of expired demo tenants"""

    try:
        async with httpx.AsyncClient() as client:
            # Get all demo tenants
            response = await client.get(
                f"{MANAGEMENT_API_URL}/api/v1/tenants?plan=demo&status=ACTIVE",
                headers={"Authorization": f"Bearer {MANAGEMENT_SERVICE_TOKEN}", "X-Service": "demo-cleanup"},
                timeout=30,
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")

            result = response.json()
            tenants = result.get("data", [])

            # Filter expired demos
            expired = []
            now = datetime.utcnow()

            for tenant in tenants:
                settings = tenant.get("settings", {})
                expires_str = settings.get("expires_at")

                if expires_str:
                    try:
                        expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                        if expires_at <= now:
                            expired.append(
                                {
                                    "tenant_id": tenant["tenant_id"],
                                    "subdomain": tenant["subdomain"],
                                    "company_name": tenant["company_name"],
                                    "expired_hours": int((now - expires_at).total_seconds() / 3600),
                                }
                            )
                    except ValueError:
                        # Invalid date format - consider expired for safety
                        expired.append(
                            {
                                "tenant_id": tenant["tenant_id"],
                                "subdomain": tenant["subdomain"],
                                "company_name": tenant["company_name"],
                                "expired_hours": -1,
                            }
                        )

            return expired

    except Exception as e:
        print(f"❌ Failed to get expired demos: {e}")
        return []


async def deprovision_demo(tenant_id: str, subdomain: str) -> bool:
    """Deprovision a single demo tenant"""

    if DRY_RUN:
        print(f"🧪 DRY RUN: Would deprovision {tenant_id} ({subdomain})")
        return True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{MANAGEMENT_API_URL}/api/v1/tenants/{tenant_id}",
                headers={"Authorization": f"Bearer {MANAGEMENT_SERVICE_TOKEN}", "X-Service": "demo-cleanup"},
                timeout=60,  # Deprovisioning can take time
            )

            if response.status_code in [200, 204]:
                print(f"✅ Deprovisioned demo: {tenant_id} ({subdomain})")
                return True
            else:
                print(f"❌ Failed to deprovision {tenant_id}: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"❌ Error deprovisioning {tenant_id}: {e}")
        return False


async def cleanup_expired_demos():
    """Main cleanup function"""

    print(f"🧹 Demo Cleanup Service - {datetime.utcnow().isoformat()}")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"Management API: {MANAGEMENT_API_URL}")
    print("=" * 60)

    # Get expired demos
    print("📋 Checking for expired demo tenants...")
    expired_demos = await get_expired_demos()

    if not expired_demos:
        print("✅ No expired demos found")
        return

    print(f"🔍 Found {len(expired_demos)} expired demo(s):")
    for demo in expired_demos:
        hours = demo["expired_hours"]
        if hours >= 0:
            print(f"  • {demo['tenant_id']} ({demo['subdomain']}) - expired {hours}h ago")
        else:
            print(f"  • {demo['tenant_id']} ({demo['subdomain']}) - invalid expiry date")

    # Deprovision expired demos
    print(f"\n🗑️  {'Simulating' if DRY_RUN else 'Starting'} deprovisioning...")

    success_count = 0
    for demo in expired_demos:
        if await deprovision_demo(demo["tenant_id"], demo["subdomain"]):
            success_count += 1

        # Small delay between operations
        await asyncio.sleep(2)

    # Summary
    print("\n📊 Cleanup Summary:")
    print(f"  • Expired demos found: {len(expired_demos)}")
    print(f"  • Successfully processed: {success_count}")
    print(f"  • Failed: {len(expired_demos) - success_count}")

    if DRY_RUN:
        print("\n💡 This was a dry run. Set DRY_RUN=false to actually deprovision.")


async def main():
    """Main entry point"""

    if not MANAGEMENT_SERVICE_TOKEN:
        print("❌ MANAGEMENT_SERVICE_TOKEN environment variable is required")
        return 1

    try:
        await cleanup_expired_demos()
        return 0
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
