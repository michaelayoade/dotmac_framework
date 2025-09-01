#!/usr/bin/env python3
"""
Validate ISP Framework API endpoint availability and completeness.
This script tests the core finding from gap analysis that APIs are missing.
"""

import os
import sys
import importlib
from typing import Dict, List, Any
import json
from pathlib import Path


def validate_router_endpoints():
    """Validate all router endpoints are properly defined."""
    results = {
        "modules_checked": [],
        "endpoints_found": {},
        "missing_modules": [],
        "validation_summary": {}
    }
    
    # Core modules to validate
    modules_to_check = [
        ("dotmac_isp.modules.identity.router", "router", "Identity/Auth"),
        ("dotmac_isp.modules.services.router", "services_router", "Services"),
        ("dotmac_isp.modules.billing.router", "billing_router", "Billing"), 
        ("dotmac_isp.modules.captive_portal.router", "router", "Customer Portal")
    ]
    
    sys.path.insert(0, "/home/dotmac_framework/src")
    
    for module_path, router_name, description in modules_to_check:
        try:
            # Import module
            module = importlib.import_module(module_path)
            router = getattr(module, router_name, None)
            
            if router:
                # Count endpoints
                endpoint_count = len([route for route in router.routes])
                
                results["modules_checked"].append({
                    "module": module_path,
                    "description": description,
                    "router_name": router_name,
                    "status": "✅ FOUND",
                    "endpoint_count": endpoint_count
                })
                
                # Extract route details
                endpoints = []
                for route in router.routes:
                    if hasattr(route, 'methods') and hasattr(route, 'path'):
                        for method in route.methods:
                            if method != 'HEAD':
                                endpoints.append(f"{method} {route.path}")
                
                results["endpoints_found"][description] = endpoints
                
            else:
                results["modules_checked"].append({
                    "module": module_path,
                    "description": description, 
                    "router_name": router_name,
                    "status": "❌ ROUTER NOT FOUND",
                    "endpoint_count": 0
                })
                
        except ImportError as e:
            results["missing_modules"].append({
                "module": module_path,
                "description": description,
                "error": str(e)
            })
            results["modules_checked"].append({
                "module": module_path,
                "description": description,
                "router_name": router_name, 
                "status": "❌ MODULE NOT FOUND",
                "endpoint_count": 0
            })
        except Exception as e:
            results["modules_checked"].append({
                "module": module_path,
                "description": description,
                "router_name": router_name,
                "status": f"❌ ERROR: {e}",
                "endpoint_count": 0
            })
    
    # Generate summary
    total_modules = len(modules_to_check)
    working_modules = len([m for m in results["modules_checked"] if "✅" in m["status"]])
    total_endpoints = sum([m.get("endpoint_count", 0) for m in results["modules_checked"]])
    
    results["validation_summary"] = {
        "total_modules_checked": total_modules,
        "working_modules": working_modules,
        "module_success_rate": f"{(working_modules/total_modules)*100:.1f}%",
        "total_endpoints_found": total_endpoints,
        "overall_status": "✅ APIS IMPLEMENTED" if working_modules == total_modules else "❌ MISSING APIS"
    }
    
    return results


def check_registration_in_main_router():
    """Check if routers are properly registered in main app."""
    try:
        from dotmac_isp.api.routers import register_routers
        return {"status": "✅ Router registration function exists"}
    except ImportError as e:
        return {"status": f"❌ Router registration missing: {e}"}


def main():
    print("🔍 ISP Framework API Endpoint Validation")
    print("=" * 50)
    
    # Validate individual routers
    router_results = validate_router_endpoints()
    
    print("\n📋 Module Validation Results:")
    for module in router_results["modules_checked"]:
        status_icon = "✅" if "✅" in module["status"] else "❌" 
        print(f"{status_icon} {module['description']}: {module['endpoint_count']} endpoints")
        if "❌" in module["status"]:
            print(f"   └── {module['status']}")
    
    print(f"\n📊 Summary:")
    summary = router_results["validation_summary"]
    print(f"   • Modules Working: {summary['working_modules']}/{summary['total_modules_checked']} ({summary['module_success_rate']})")
    print(f"   • Total Endpoints: {summary['total_endpoints_found']}")
    print(f"   • Overall Status: {summary['overall_status']}")
    
    # Check router registration
    registration_result = check_registration_in_main_router()
    print(f"\n🔗 Router Registration: {registration_result['status']}")
    
    # Show some sample endpoints
    if router_results["endpoints_found"]:
        print(f"\n🛠️  Sample API Endpoints Found:")
        for module_name, endpoints in router_results["endpoints_found"].items():
            print(f"\n   {module_name}:")
            for endpoint in endpoints[:5]:  # Show first 5
                print(f"     • {endpoint}")
            if len(endpoints) > 5:
                print(f"     ... and {len(endpoints)-5} more")
    
    # Save detailed results
    output_file = "/home/dotmac_framework/.dev-artifacts/api_validation_results.json"
    with open(output_file, 'w') as f:
        json.dump(router_results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Final verdict
    if router_results["validation_summary"]["working_modules"] == router_results["validation_summary"]["total_modules_checked"]:
        print(f"\n🎉 CONCLUSION: ISP Framework APIs are actually IMPLEMENTED!")
        print(f"   The gap analysis may have been incorrect about missing APIs.")
        return True
    else:
        print(f"\n⚠️  CONCLUSION: Some APIs are indeed missing.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)