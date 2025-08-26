#!/usr/bin/env python3
"""
Targeted fixes for critical syntax errors in Management Platform
"""
import re
from pathlib import Path
from typing import Dict, List

class CriticalSyntaxFixer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixes_applied = []
        
    def fix_dashboard_api(self):
        """Fix dashboard.py syntax errors"""
        file_path = self.root_dir / "app/api/dashboard.py"
        fixes = []
        
        if not file_path.exists():
            return fixes
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        original_content = content
        
        # Fix function definitions with missing parameters
        fixes_patterns = [
            # Fix async def functions missing parameters
            (r'^(@router\.\w+\([^)]+\)\s*\n)async def (\w+)\(\):\s*$', r'\1async def \2('),
            # Fix missing closing parentheses in function signatures
            (r'async def (\w+)\(\s*$', r'async def \1('),
            # Fix Form parameter definitions
            (r'(\w+: \w+) = Form\(\.\.\.\),\s*$', r'\1 = Form(...),'),
            # Fix observability record calls with missing closing paren
            (r'(observability\.record_\w+\([^)]+)\s*$', r'\1)'),
        ]
        
        for pattern, replacement in fixes_patterns:
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if new_content != content:
                fixes.append(f"Applied pattern fix: {pattern}")
                content = new_content
                
        # Manual fixes for specific issues
        lines = content.split('\n')
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix function definitions without proper parameter structure
            if 'async def' in line and '():' in line and '@router' in lines[i-1] if i > 0 else False:
                # This looks like a router function that should have parameters
                if 'create_tenant' in line:
                    line = line.replace('():', '(')
                elif 'list_tenants' in line:
                    line = line.replace('():', '(')
                elif 'delete_tenant' in line:
                    line = line.replace('():', '(')
                elif 'dashboard' in line:
                    line = line.replace('():', '(')
            
            # Fix missing closing parentheses after observability calls
            if 'observability.record_tenant_operation' in line and not line.rstrip().endswith(')'):
                line = line.rstrip() + ')'
                
            if line != original_line:
                fixes.append(f"Fixed line {i+1}: {original_line.strip()} -> {line.strip()}")
                
            lines[i] = line
            
        content = '\n'.join(lines)
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            fixes.append(f"Updated {file_path}")
            
        return fixes
    
    def fix_billing_api(self):
        """Fix billing.py API syntax errors"""
        file_path = self.root_dir / "app/api/v1/billing.py"
        fixes = []
        
        if not file_path.exists():
            return fixes
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        original_content = content
        
        # Fix missing closing parentheses in function signatures
        lines = content.split('\n')
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix function definitions with Depends() calls missing closing paren
            if 'current_user = Depends(require_billing_' in line and not line.rstrip().endswith(')'):
                if 'read()' in line or 'write()' in line:
                    line = line.rstrip() + ')'
                    
            # Fix async def lines that got cut off
            if 'async def' in line and ')' not in line and line.rstrip().endswith(':'):
                # Find the previous lines that contain parameters
                if i > 0:
                    prev_lines = lines[max(0, i-5):i]
                    # Look for function parameters in previous lines
                    param_lines = [l for l in prev_lines if ':' in l and '=' in l]
                    if param_lines:
                        # This function definition needs to be fixed
                        line = line.replace(':', '').rstrip()
                        if not line.endswith('('):
                            line += '('
                        fixes.append(f"Fixed async def at line {i+1}")
            
            if line != original_line:
                fixes.append(f"Fixed line {i+1}: {original_line.strip()} -> {line.strip()}")
                
            lines[i] = line
            
        content = '\n'.join(lines)
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            fixes.append(f"Updated {file_path}")
            
        return fixes
        
    def fix_ssh_plugin(self):
        """Fix SSH plugin syntax errors"""
        file_path = self.root_dir / "app/plugins/deployment/ssh_plugin.py"
        fixes = []
        
        if not file_path.exists():
            return fixes
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        original_content = content
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            original_line = line
            
            # Fix async function definitions with missing commas
            if 'async def' in line and 'Optional[str])' in line and ',' not in line:
                # This indicates a function signature that spans multiple lines incorrectly
                if 'key_path: Optional[str])' in line:
                    line = line.replace('Optional[str])', 'Optional[str],')
                    
            # Fix function definitions missing closing parenthesis
            if 'async def _' in line and line.rstrip().endswith(','):
                # Function definition continues, look ahead
                if i < len(lines) - 1:
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith('"""'):
                        # Add missing closing paren and colon
                        line = line.rstrip() + ') -> Dict[str, Any]:'
                        
            if line != original_line:
                fixes.append(f"Fixed line {i+1}: {original_line.strip()} -> {line.strip()}")
                
            lines[i] = line
            
        content = '\n'.join(lines)
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            fixes.append(f"Updated {file_path}")
            
        return fixes
    
    def fix_worker_tasks(self):
        """Fix worker task files"""
        fixes = []
        
        task_files = [
            "app/workers/tasks/billing_tasks.py",
            "app/workers/tasks/deployment_tasks.py", 
            "app/workers/tasks/monitoring_tasks.py",
            "app/workers/tasks/notification_tasks.py",
            "app/workers/tasks/plugin_tasks.py"
        ]
        
        for task_file in task_files:
            file_path = self.root_dir / task_file
            if not file_path.exists():
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            original_content = content
            
            # Fix common patterns in task files
            content = re.sub(r'(\w+)\.delay\(([^)]+)\)\.get\(\)', r'\1.delay(\2).get()', content)
            content = re.sub(r'logger\.\w+\(([^)]+)\s*$', r'logger.info(\1)', content, flags=re.MULTILINE)
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                original_line = line
                
                # Fix missing closing parentheses in logger calls
                if 'logger.' in line and '(' in line and not line.rstrip().endswith(')'):
                    if line.count('(') > line.count(')'):
                        line = line.rstrip() + ')'
                        
                # Fix async function definitions
                if '@task' in line and i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if 'async def' in next_line and not next_line.strip().endswith(':'):
                        if '(' in next_line and ')' not in next_line:
                            lines[i + 1] = next_line.rstrip() + '):'
                            
                if line != original_line:
                    fixes.append(f"Fixed {task_file} line {i+1}")
                    
                lines[i] = line
                
            content = '\n'.join(lines)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                fixes.append(f"Updated {task_file}")
                
        return fixes
    
    def fix_service_files(self):
        """Fix service files with syntax errors"""
        fixes = []
        
        service_files = [
            "app/services/notification_service.py",
            "app/services/user_management_service.py", 
            "app/services/plugin_version_manager.py",
            "app/services/tenant_service.py",
            "app/services/stripe_service.py",
            "app/services/plugin_security_scanner.py",
            "app/services/plugin_service.py",
            "app/services/provisioning_service.py",
            "app/services/billing_service.py",
            "app/services/dns_service.py",
            "app/services/analytics_service.py",
            "app/services/plugin_geo_analytics.py",
            "app/services/deployment_service.py"
        ]
        
        for service_file in service_files:
            file_path = self.root_dir / service_file
            if not file_path.exists():
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            original_content = content
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                original_line = line
                
                # Fix closing bracket/paren mismatches
                if line.strip() == '}' and i > 0:
                    # Look for opening parentheses in previous lines
                    for j in range(i-1, max(0, i-10), -1):
                        prev_line = lines[j]
                        if '(' in prev_line and prev_line.count('(') > prev_line.count(')'):
                            line = line.replace('}', ')')
                            break
                            
                # Fix missing closing parentheses in function calls
                if 'minor = int(match.group(2)' in line and not line.endswith(')'):
                    line = line + ')'
                    
                # Fix UUID function calls
                if 'UUID.uuid4(' in line and not line.rstrip().endswith(')'):
                    line = line.rstrip() + ')'
                    
                # Fix stripe usage record calls
                if 'stripe.UsageRecord.create(' in line and not line.rstrip().endswith(')'):
                    # This is likely a multi-line call, look ahead
                    if i < len(lines) - 5:
                        for k in range(i+1, min(len(lines), i+5)):
                            if lines[k].strip() and not lines[k].startswith(' '):
                                # Add closing paren before this line
                                if k > i+1:
                                    lines[k-1] = lines[k-1] + ')'
                                    break
                
                if line != original_line:
                    fixes.append(f"Fixed {service_file} line {i+1}")
                    
                lines[i] = line
                
            content = '\n'.join(lines)
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                fixes.append(f"Updated {service_file}")
                
        return fixes
    
    def fix_all(self):
        """Apply all critical fixes"""
        all_fixes = []
        
        print("Fixing dashboard API...")
        all_fixes.extend(self.fix_dashboard_api())
        
        print("Fixing billing API...")
        all_fixes.extend(self.fix_billing_api())
        
        print("Fixing SSH plugin...")  
        all_fixes.extend(self.fix_ssh_plugin())
        
        print("Fixing worker tasks...")
        all_fixes.extend(self.fix_worker_tasks())
        
        print("Fixing service files...")
        all_fixes.extend(self.fix_service_files())
        
        return all_fixes

if __name__ == "__main__":
    fixer = CriticalSyntaxFixer("/home/dotmac_framework/management-platform")
    
    print("Applying critical syntax fixes...")
    fixes = fixer.fix_all()
    
    print(f"\nApplied {len(fixes)} critical fixes:")
    for fix in fixes:
        print(f"  - {fix}")
    
    print("\nCritical fixes completed!")