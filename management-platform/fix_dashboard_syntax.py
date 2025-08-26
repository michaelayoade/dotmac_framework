#!/usr/bin/env python3
"""
Fix specific syntax errors in dashboard.py
"""

import re
from pathlib import Path

def fix_dashboard_syntax():
    """Fix dashboard.py syntax errors"""
    file_path = Path("/home/dotmac_framework/management-platform/app/api/dashboard.py")
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix specific patterns in dashboard.py
    fixes = [
        # Fix create_tenant function parameters
        (r'# Create tenant\s+tenant = await tenant_service\.create_tenant\(\)\s+tenant_id=tenant_id,',
         '# Create tenant\n            tenant = await tenant_service.create_tenant(\n                tenant_id=tenant_id,'),
        
        # Fix observability call
        (r'observability\.record_tenant_operation\("create", tenant_id, success=True\)\s+company_name=tenant_name\)',
         'observability.record_tenant_operation("create", tenant_id, success=True,\n                                                company_name=tenant_name)'),
        
        # Fix infrastructure provision call
        (r'infrastructure_result = await service_integration\.provision_infrastructure_via_plugin\(\)\s+provider="ssh",',
         'infrastructure_result = await service_integration.provision_infrastructure_via_plugin(\n                        provider="ssh",'),
        
        # Fix app deploy call  
        (r'app_result = await service_integration\.deploy_application_via_plugin\(\)\s+provider="ssh",',
         'app_result = await service_integration.deploy_application_via_plugin(\n                        provider="ssh",'),
        
        # Fix logs extend
        (r'deployment_logs\[deployment_id\]\.extend\(\[\)\s+"✅ Infrastructure provisioned successfully",',
         'deployment_logs[deployment_id].extend([\n                        "✅ Infrastructure provisioned successfully",'),
        
        # Fix metrics function signature
        (r'@router\.get\("/metrics"\)\s+async def get_platform_metrics\(db: AsyncSession = Depends\(get_db\):',
         '@router.get("/metrics")\nasync def get_platform_metrics(db: AsyncSession = Depends(get_db)):'),
        
        # Fix timezone references
        (r'datetime\.now\(timezone\.utc\)', 'datetime.now()'),
        
        # Fix deployment logs list comprehension
        (r'deployments_today = len\(\[\)\s+log for log_id, log in deployment_logs\.items\(\)',
         'deployments_today = len([\n            log for log_id, log in deployment_logs.items()'),
        
        # Fix plugin count
        (r'plugin_count = len\(service_integration\.get_available_providers\("deployment_provider"\)',
         'plugin_count = len(service_integration.get_available_providers("deployment_provider"))'),
        
        # Fix list_tenants function
        (r'@router\.get\("/tenants"\)\s+async def list_tenants\(\)\s+limit: int = 20,\s+skip: int = 0,\s+db: AsyncSession = Depends\(get_db\):\s+\s+\s+\s+\):',
         '@router.get("/tenants")\nasync def list_tenants(\n    limit: int = 20,\n    skip: int = 0,\n    db: AsyncSession = Depends(get_db)\n):'),
        
        # Fix delete_tenant function
        (r'@router\.delete\("/tenants/\{tenant_id\}"\)\s+async def delete_tenant\(\)\s+db: AsyncSession = Depends\(get_db\):\s+\s+db: AsyncSession = Depends\(get_db\)\s+\):',
         '@router.delete("/tenants/{tenant_id}")\nasync def delete_tenant(\n    tenant_id: str,\n    db: AsyncSession = Depends(get_db)\n):'),
        
        # Fix list_plugins function
        (r'@router\.get\("/plugins"\)\s+async def list_plugins\(\)',
         '@router.get("/plugins")\nasync def list_plugins():'),
        
        # Fix dashboard_health function
        (r'@router\.get\("/health"\)\s+async def dashboard_health\(\)',
         '@router.get("/health")\nasync def dashboard_health():'),
    ]
    
    # Apply fixes
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed dashboard.py syntax errors")

if __name__ == "__main__":
    fix_dashboard_syntax()