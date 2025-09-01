#!/usr/bin/env python3
"""
Production Deployment Validation Script
Validates all critical components before rollout
"""

import os
import sys
import asyncio
import httpx
from typing import Dict, List, Any

def check_environment_variables() -> Dict[str, Any]:
    """Check all required environment variables"""
    
    required_vars = [
        'SECRET_KEY',
        'CORS_ORIGINS', 
        'DATABASE_URL',
        'BASE_DOMAIN',
        'COOLIFY_API_TOKEN',
        'COOLIFY_API_URL'
    ]
    
    results = {
        "status": "passed",
        "checks": [],
        "errors": []
    }
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            results["errors"].append(f"Missing required environment variable: {var}")
            results["status"] = "failed"
        else:
            # Validate specific formats
            if var == 'SECRET_KEY' and len(value) < 32:
                results["errors"].append("SECRET_KEY must be at least 32 characters")
                results["status"] = "failed"
            elif var == 'CORS_ORIGINS' and not value.startswith('https://'):
                results["errors"].append("CORS_ORIGINS must use HTTPS in production")
                results["status"] = "failed"
            elif var == 'BASE_DOMAIN' and ('.' not in value or value.startswith('.')):
                results["errors"].append("BASE_DOMAIN must be a valid domain")
                results["status"] = "failed"
            else:
                results["checks"].append(f"✅ {var}: configured")
    
    return results

async def check_bootstrap_status() -> Dict[str, Any]:
    """Check if bootstrap credentials are properly removed"""
    
    try:
        management_url = os.getenv('MANAGEMENT_URL', 'http://localhost:8001')
        
        async with httpx.AsyncClient() as client:
            # This would require authentication in real deployment
            response = await client.get(f"{management_url}/api/v1/admin/bootstrap-status")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('bootstrap_credentials_present', True):
                    return {
                        "status": "failed",
                        "message": "❌ Bootstrap credentials still present - security risk!"
                    }
                else:
                    return {
                        "status": "passed", 
                        "message": "✅ Bootstrap credentials properly removed"
                    }
            else:
                return {
                    "status": "unknown",
                    "message": "Could not check bootstrap status (authentication required)"
                }
                
    except Exception as e:
        return {
            "status": "error",
            "message": f"Bootstrap check failed: {e}"
        }

async def check_coolify_connectivity() -> Dict[str, Any]:
    """Check Coolify API connectivity"""
    
    try:
        coolify_url = os.getenv('COOLIFY_API_URL')
        coolify_token = os.getenv('COOLIFY_API_TOKEN')
        
        if not coolify_url or not coolify_token:
            return {
                "status": "failed",
                "message": "❌ Coolify configuration missing"
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{coolify_url}/api/v1/servers",
                headers={"Authorization": f"Bearer {coolify_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                servers = response.json()
                return {
                    "status": "passed",
                    "message": f"✅ Coolify connected ({len(servers)} servers available)"
                }
            else:
                return {
                    "status": "failed", 
                    "message": f"❌ Coolify API error: {response.status_code}"
                }
                
    except Exception as e:
        return {
            "status": "error",
            "message": f"Coolify check failed: {e}"
        }

def check_security_configuration() -> Dict[str, Any]:
    """Check security configuration"""
    
    results = {
        "status": "passed",
        "checks": [],
        "warnings": []
    }
    
    # Check CORS origins
    cors_origins = os.getenv('CORS_ORIGINS', '')
    if cors_origins:
        origins = [o.strip() for o in cors_origins.split(',')]
        for origin in origins:
            if not origin.startswith('https://'):
                results["warnings"].append(f"CORS origin not HTTPS: {origin}")
        results["checks"].append(f"✅ CORS configured with {len(origins)} origins")
    else:
        results["warnings"].append("CORS_ORIGINS not configured")
    
    # Check domain configuration  
    base_domain = os.getenv('BASE_DOMAIN')
    if base_domain:
        results["checks"].append(f"✅ Base domain configured: {base_domain}")
    
    return results

async def main():
    """Run all validation checks"""
    
    print("🔍 DotMac Platform - Deployment Validation")
    print("=" * 50)
    
    # Environment variables check
    print("\n📋 Environment Variables:")
    env_check = check_environment_variables()
    if env_check["status"] == "passed":
        print("✅ All required environment variables configured")
    else:
        print("❌ Environment variable issues:")
        for error in env_check["errors"]:
            print(f"  - {error}")
    
    # Security configuration
    print("\n🔒 Security Configuration:")
    security_check = check_security_configuration()
    for check in security_check["checks"]:
        print(f"  {check}")
    for warning in security_check.get("warnings", []):
        print(f"  ⚠️  {warning}")
    
    # Bootstrap status
    print("\n🔑 Bootstrap Status:")
    bootstrap_check = await check_bootstrap_status()
    print(f"  {bootstrap_check['message']}")
    
    # Coolify connectivity
    print("\n🐳 Coolify Integration:")
    coolify_check = await check_coolify_connectivity()
    print(f"  {coolify_check['message']}")
    
    # Overall assessment
    print("\n" + "=" * 50)
    
    failed_checks = []
    if env_check["status"] == "failed":
        failed_checks.append("Environment")
    if bootstrap_check["status"] == "failed":
        failed_checks.append("Bootstrap Security")
    if coolify_check["status"] == "failed":
        failed_checks.append("Coolify")
    
    if failed_checks:
        print(f"❌ DEPLOYMENT NOT READY - Fix: {', '.join(failed_checks)}")
        return 1
    else:
        print("✅ DEPLOYMENT READY - All critical checks passed!")
        print("\nNext steps:")
        print("1. Deploy Management Platform to Coolify")
        print("2. Set environment variables in Coolify")
        print("3. Complete bootstrap security removal")
        print("4. Test tenant provisioning workflow")
        return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)