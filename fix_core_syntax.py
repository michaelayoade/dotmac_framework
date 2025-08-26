#!/usr/bin/env python3
"""
Fix syntax errors in dotmac_isp/core/ module specifically.
"""
import ast
import re
import os

def fix_core_syntax():
    """Fix syntax errors in core module."""
    fixed_count = 0
    core_dir = './isp-framework/src/dotmac_isp/core'
    
    # Common patterns to fix
    fixes = [
        # Missing closing parentheses
        (r'\.startswith\(\("postgresql", "postgres"\)$', r'.startswith(("postgresql", "postgres"))'),
        (r'uuid\.uuid4\(\)\[:8\]$', r'str(uuid.uuid4())[:8]'),
        (r'init_config_backup\(encryption_key=os\.getenv\("BACKUP_ENCRYPTION_KEY"\)$', r'init_config_backup(encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY"))'),
        (r'bcrypt\.checkpw\([^)]+, [^)]+\)$', r'\g<0>)'),  # Fix missing ) in bcrypt calls
        (r'handlers\.keys\"\}$', r'handlers.keys())'),
        
        # Missing ) in function calls
        (r'([a-zA-Z_][a-zA-Z0-9_]*\([^)]*[^)])$', r'\1)'),
        
        # Fix common missing commas in parameters  
        (r'(\w+)=([^,\s]+)\s+(\w+)=', r'\1=\2, \3='),
    ]
    
    for root, dirs, files in os.walk(core_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                try:
                    # Check if file has syntax errors
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        ast.parse(content, filename=file_path)
                        continue  # Skip files without syntax errors
                    except SyntaxError:
                        pass  # Has syntax errors, try to fix
                    
                    original_content = content
                    
                    # Apply common fixes
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        original_line = line
                        
                        # Fix specific patterns
                        if 'uuid.uuid4(' in line and line.count('(') > line.count(')'):
                            if line.strip().endswith('[:8]'):
                                lines[i] = line.replace('uuid.uuid4()[:8]', 'str(uuid.uuid4())[:8]')
                                continue
                            # Add missing closing parenthesis
                            open_parens = line.count('(')
                            close_parens = line.count(')')
                            if open_parens > close_parens:
                                lines[i] = line + ')' * (open_parens - close_parens)
                        
                        # Fix bcrypt.checkpw calls
                        elif 'bcrypt.checkpw(' in line and line.count('(') > line.count(')'):
                            lines[i] = line + ')'
                        
                        # Fix .startswith calls
                        elif '.startswith((' in line and line.count('(') > line.count(')'):
                            lines[i] = line + ')'
                        
                        # Fix .encode() calls
                        elif '.encode(' in line and line.count('(') > line.count(')'):
                            lines[i] = line + ')'
                        
                        # Fix init_config_backup calls
                        elif 'init_config_backup(' in line and line.count('(') > line.count(')'):
                            lines[i] = line + ')'
                        
                        # Fix handlers.keys"}
                        elif 'handlers.keys"}' in line:
                            lines[i] = line.replace('handlers.keys"}', 'handlers.keys()}')
                        
                        # Fix missing commas in parameter lists
                        if re.search(r'(\w+)=([^,\s]+)\s+(\w+)=', line):
                            lines[i] = re.sub(r'(\w+)=([^,\s]+)\s+(\w+)=', r'\1=\2, \3=', line)
                    
                    fixed_content = '\n'.join(lines)
                    
                    # Only write if changed and valid
                    if fixed_content != original_content:
                        try:
                            ast.parse(fixed_content, filename=file_path)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                            print(f"Fixed: {file_path}")
                            fixed_count += 1
                        except SyntaxError:
                            # Still has errors, skip
                            pass
                
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    print(f"\nFixed {fixed_count} core module files")

if __name__ == "__main__":
    fix_core_syntax()