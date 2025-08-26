#!/usr/bin/env python3
"""
Systematically fix router syntax errors
"""

import os
import re
import sys
from pathlib import Path

def fix_stray_timezone_imports(file_path):
    """Fix stray ', timezone)' import errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove stray ', timezone)' lines
        content = re.sub(r'^, timezone\)\s*$', '', content, flags=re.MULTILINE)
        
        # Add timezone import where needed if timezone.utc is used
        if 'timezone.utc' in content and 'from datetime import' in content:
            # Find existing datetime imports and add timezone if missing
            datetime_import_pattern = r'from datetime import ([^)]+)'
            match = re.search(datetime_import_pattern, content)
            if match:
                imports = match.group(1)
                if 'timezone' not in imports:
                    new_imports = f"{imports}, timezone"
                    content = re.sub(datetime_import_pattern, f"from datetime import {new_imports}", content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def fix_missing_parentheses(file_path):
    """Fix common missing parentheses patterns."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix HTTPException without closing paren
            if 'HTTPException(status_code=' in line and not line.strip().endswith(')'):
                if 'detail=' in line and not line.count('(') == line.count(')'):
                    line = line.rstrip() + ')\n'
            
            # Fix UUID calls without closing paren
            if 'UUID(' in line and line.count('(') > line.count(')'):
                if not line.strip().endswith(')'):
                    line = line.rstrip() + ')\n'
            
            # Fix logger.error calls
            if 'logger.error(' in line and line.count('(') > line.count(')'):
                if not line.strip().endswith(')'):
                    line = line.rstrip() + ')\n'
            
            if line != original_line:
                lines[i] = line
                modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def fix_function_signature_errors(file_path):
    """Fix common function signature errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix function signatures with misplaced return type annotations
        # def func(param = Depends(something) -> ReturnType:
        pattern = r'def ([^(]+)\(([^)]*) -> ([^:]+):'
        def fix_signature(match):
            func_name = match.group(1)
            params = match.group(2)
            return_type = match.group(3)
            return f"def {func_name}({params}) -> {return_type}:"
        
        content = re.sub(pattern, fix_signature, content)
        
        # Fix missing closing parentheses in function calls within function signatures
        content = re.sub(r'= Depends\(([^)]+)$', r'= Depends(\1)', content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def fix_bracket_mismatches(file_path):
    """Fix bracket mismatches like { vs ( errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix common bracket mismatches in return statements
        # Look for patterns like },\n that should be ),
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Fix closing brace that should be closing paren
            if line.strip() == '},' and i > 0:
                # Check if previous lines suggest this should be a paren
                context = '\n'.join(lines[max(0, i-5):i])
                if '(' in context and context.count('(') > context.count(')'):
                    lines[i] = line.replace('},', '),')
            elif line.strip() == '}' and i > 0:
                # Check if this should be a closing paren
                context = '\n'.join(lines[max(0, i-5):i])
                if '(' in context and context.count('(') > context.count(')'):
                    lines[i] = line.replace('}', ')')
        
        content = '\n'.join(lines)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix router syntax errors."""
    os.chdir("/home/dotmac_framework")
    
    print("🔧 Fixing router syntax errors systematically...")
    
    # Get list of router files with errors from our previous analysis
    router_files = [
        "isp-framework/src/dotmac_isp/api/file_router.py",
        "isp-framework/src/dotmac_isp/api/plugins_endpoints.py",
        "isp-framework/src/dotmac_isp/api/security_endpoints.py",
        "isp-framework/src/dotmac_isp/api/websocket_router.py",
        "isp-framework/src/dotmac_isp/integrations/ansible/router.py",
        "isp-framework/src/dotmac_isp/modules/analytics/router.py",
        "isp-framework/src/dotmac_isp/modules/compliance/router.py",
        "isp-framework/src/dotmac_isp/modules/field_ops/router.py",
        "isp-framework/src/dotmac_isp/modules/identity/router.py",
        "isp-framework/src/dotmac_isp/modules/inventory/router.py",
        "isp-framework/src/dotmac_isp/modules/licensing/router.py",
        "isp-framework/src/dotmac_isp/modules/network_integration/router.py",
        "isp-framework/src/dotmac_isp/modules/network_monitoring/router.py",
        "isp-framework/src/dotmac_isp/modules/network_visualization/router.py",
        "isp-framework/src/dotmac_isp/modules/notifications/router.py",
        "isp-framework/src/dotmac_isp/modules/omnichannel/router.py",
        "isp-framework/src/dotmac_isp/modules/portal_management/router.py",
        "isp-framework/src/dotmac_isp/modules/projects/router.py",
        "isp-framework/src/dotmac_isp/modules/resellers/router.py",
        "isp-framework/src/dotmac_isp/modules/sales/router.py",
        "isp-framework/src/dotmac_isp/modules/services/router.py",
        "isp-framework/src/dotmac_isp/modules/support/router.py",
        "management-platform/app/api/v1/auth.py",
        "management-platform/app/api/v1/billing.py",
        "management-platform/app/api/v1/deployment.py",
        "management-platform/app/api/v1/monitoring.py",
        "management-platform/app/api/v1/plugin.py",
        "management-platform/app/api/v1/tenant.py",
        "management-platform/app/api/dashboard.py",
    ]
    
    fixed_count = 0
    
    for file_path in router_files:
        if os.path.exists(file_path):
            print(f"🔧 Fixing {file_path}...")
            
            fixes_applied = []
            
            if fix_stray_timezone_imports(file_path):
                fixes_applied.append("timezone imports")
            
            if fix_missing_parentheses(file_path):
                fixes_applied.append("parentheses")
            
            if fix_function_signature_errors(file_path):
                fixes_applied.append("function signatures")
            
            if fix_bracket_mismatches(file_path):
                fixes_applied.append("bracket mismatches")
            
            if fixes_applied:
                print(f"   ✅ Fixed: {', '.join(fixes_applied)}")
                fixed_count += 1
            else:
                print(f"   ⚠️ No automatic fixes applied")
        else:
            print(f"   ❌ File not found: {file_path}")
    
    print(f"\n📊 Summary: Applied fixes to {fixed_count} files")
    print("🔍 Run check_router_syntax.py to verify fixes")

if __name__ == "__main__":
    main()