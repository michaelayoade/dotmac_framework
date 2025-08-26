#!/usr/bin/env python3
"""Fix unreachable code after raise statements causing syntax errors."""

import re
from pathlib import Path

def fix_unreachable_code(file_path: Path):
    """Remove unreachable code after raise statements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        in_unreachable = False
        raise_line_indent = 0
        new_lines = []
        
        for i, line in enumerate(lines):
            if in_unreachable:
                # Check if we're at a new function/class or same/higher indentation
                current_indent = len(line) - len(line.lstrip())
                if (line.strip() and 
                    (current_indent <= raise_line_indent or 
                     line.strip().startswith(('def ', 'class ', 'async def ')) or
                     line.strip().startswith('@'))):
                    # End of unreachable section
                    in_unreachable = False
                    new_lines.append(line)
                else:
                    # Skip this unreachable line
                    modified = True
                    continue
            else:
                new_lines.append(line)
                # Check if this line has a raise statement
                if ('raise ' in line and 
                    not line.strip().startswith('#') and
                    not line.strip().startswith('"""') and
                    not line.strip().startswith("'")):
                    # Start tracking unreachable code
                    in_unreachable = True
                    raise_line_indent = len(line) - len(line.lstrip())
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    # Fix the specific file we're working on
    file_path = Path("/home/dotmac_framework/isp-framework/src/dotmac_isp/modules/identity/services/customer_service.py")
    
    if fix_unreachable_code(file_path):
        print(f"Fixed unreachable code in: {file_path}")
    else:
        print(f"No changes needed in: {file_path}")

if __name__ == "__main__":
    main()