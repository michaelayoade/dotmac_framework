#!/usr/bin/env python3
"""
Consolidate billing service duplicates by removing redundant files
and updating references.
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict

# Consolidation plan based on analysis
CONSOLIDATION_PLAN = [
    {
        'name': 'service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.service import', 'from dotmac_isp.modules.billing.service import'),
            ('dotmac_business_logic.billing.isp.service', 'dotmac_isp.modules.billing.service'),
        ]
    },
    {
        'name': 'calculation_service', 
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/domain/calculation_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/domain/calculation_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.domain.calculation_service import', 'from dotmac_isp.modules.billing.domain.calculation_service import'),
            ('dotmac_business_logic.billing.isp.domain.calculation_service', 'dotmac_isp.modules.billing.domain.calculation_service'),
        ]
    },
    {
        'name': 'tax_service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/services/tax_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/tax_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.services.tax_service import', 'from dotmac_isp.modules.billing.services.tax_service import'),
            ('dotmac_business_logic.billing.isp.services.tax_service', 'dotmac_isp.modules.billing.services.tax_service'),
        ]
    },
    {
        'name': 'credit_service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/services/credit_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/credit_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.services.credit_service import', 'from dotmac_isp.modules.billing.services.credit_service import'),
            ('dotmac_business_logic.billing.isp.services.credit_service', 'dotmac_isp.modules.billing.services.credit_service'),
        ]
    },
    {
        'name': 'payment_service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/services/payment_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/payment_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.services.payment_service import', 'from dotmac_isp.modules.billing.services.payment_service import'),
            ('dotmac_business_logic.billing.isp.services.payment_service', 'dotmac_isp.modules.billing.services.payment_service'),
        ]
    },
    {
        'name': 'recurring_billing_service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/services/recurring_billing_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/recurring_billing_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.services.recurring_billing_service import', 'from dotmac_isp.modules.billing.services.recurring_billing_service import'),
            ('dotmac_business_logic.billing.isp.services.recurring_billing_service', 'dotmac_isp.modules.billing.services.recurring_billing_service'),
        ]
    },
    {
        'name': 'subscription_service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/services/subscription_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/subscription_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.services.subscription_service import', 'from dotmac_isp.modules.billing.services.subscription_service import'),
            ('dotmac_business_logic.billing.isp.services.subscription_service', 'dotmac_isp.modules.billing.services.subscription_service'),
        ]
    },
    {
        'name': 'invoice_service',
        'keep': '/home/dotmac_framework/src/dotmac_isp/modules/billing/services/invoice_service.py',
        'remove': ['/home/dotmac_framework/packages/dotmac-business-logic/src/dotmac_business_logic/billing/isp/services/invoice_service.py'],
        'update_imports': [
            ('from dotmac_business_logic.billing.isp.services.invoice_service import', 'from dotmac_isp.modules.billing.services.invoice_service import'),
            ('dotmac_business_logic.billing.isp.services.invoice_service', 'dotmac_isp.modules.billing.services.invoice_service'),
        ]
    }
]

def find_import_references(file_to_remove: str) -> List[Path]:
    """Find files that import from the file to be removed."""
    root = Path("/home/dotmac_framework")
    
    # Extract the module path for searching
    rel_path = Path(file_to_remove).relative_to(root)
    
    # Convert file path to module path
    module_parts = []
    for part in rel_path.parts:
        if part == 'src':
            continue
        if part.endswith('.py'):
            module_parts.append(part[:-3])  # Remove .py extension
        else:
            module_parts.append(part)
    
    module_path = '.'.join(module_parts)
    
    print(f"🔍 Searching for imports of: {module_path}")
    
    # Search for import references
    references = []
    for py_file in root.rglob("*.py"):
        if '.dev-artifacts' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Look for imports
                if module_path in content:
                    references.append(py_file)
        except Exception:
            continue
    
    return references

def update_imports_in_file(file_path: Path, import_mappings: List[tuple]) -> bool:
    """Update imports in a file based on mapping rules."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_import, new_import in import_mappings:
            content = content.replace(old_import, new_import)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
        return False
        
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def backup_file(file_path: str) -> str:
    """Create a backup of the file before removal."""
    backup_path = file_path + '.backup'
    shutil.copy2(file_path, backup_path)
    return backup_path

def consolidate_service(plan_item: Dict) -> bool:
    """Consolidate a single service based on the plan."""
    print(f"\n🔧 Consolidating: {plan_item['name']}")
    
    # Check if files exist
    keep_file = Path(plan_item['keep'])
    if not keep_file.exists():
        print(f"❌ Keep file not found: {keep_file}")
        return False
    
    files_removed = 0
    files_updated = 0
    
    for remove_file in plan_item['remove']:
        remove_path = Path(remove_file)
        
        if not remove_path.exists():
            print(f"⚠️  File to remove not found (already removed?): {remove_path}")
            continue
        
        print(f"📋 Processing: {remove_path.name}")
        
        # Find import references
        references = find_import_references(remove_file)
        
        if references:
            print(f"📝 Found {len(references)} files with import references")
            
            # Update imports in referencing files
            for ref_file in references:
                if update_imports_in_file(ref_file, plan_item['update_imports']):
                    print(f"  ✅ Updated imports in: {ref_file.relative_to('/home/dotmac_framework')}")
                    files_updated += 1
        
        # Create backup and remove
        try:
            backup_path = backup_file(remove_file)
            print(f"💾 Backup created: {Path(backup_path).name}")
            
            os.remove(remove_file)
            print(f"🗑️  Removed: {remove_path.relative_to('/home/dotmac_framework')}")
            files_removed += 1
            
        except Exception as e:
            print(f"❌ Error removing {remove_file}: {e}")
            return False
    
    print(f"✅ {plan_item['name']}: {files_removed} files removed, {files_updated} imports updated")
    return True

def main():
    """Main consolidation function."""
    print("🚀 Consolidating Billing Service Duplicates")
    print("=" * 60)
    
    total_files_removed = 0
    total_imports_updated = 0
    successful_consolidations = 0
    
    for plan_item in CONSOLIDATION_PLAN:
        if consolidate_service(plan_item):
            successful_consolidations += 1
            total_files_removed += len(plan_item['remove'])
        else:
            print(f"❌ Failed to consolidate: {plan_item['name']}")
    
    print("\n" + "=" * 60)
    print(f"📊 Consolidation Summary:")
    print(f"   Services processed: {len(CONSOLIDATION_PLAN)}")
    print(f"   Successful consolidations: {successful_consolidations}")
    print(f"   Total files removed: {total_files_removed}")
    print(f"   Import references updated: {total_imports_updated}")
    
    if successful_consolidations == len(CONSOLIDATION_PLAN):
        print("🎉 All billing service consolidations completed successfully!")
        return True
    else:
        print("⚠️  Some consolidations failed. Check output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)