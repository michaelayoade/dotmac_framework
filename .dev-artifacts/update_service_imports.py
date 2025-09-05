#!/usr/bin/env python3
"""
Update service imports to use the unified base service architecture.
"""

import os
import re
from pathlib import Path

# Define the mappings for import updates
IMPORT_MAPPINGS = [
    (r"from dotmac_isp\.shared\.base_service import (.*)", r"from dotmac_shared.services.base import \1"),
    (r"from dotmac_management\.shared\.base_service import (.*)", r"from dotmac_shared.services.base import \1"),
    (r"from \.\.shared\.base_service import (.*)", r"from dotmac_shared.services.base import \1"),
    (r"from \.\.\.shared\.base_service import (.*)", r"from dotmac_shared.services.base import \1"),
]

def update_file(file_path: Path) -> bool:
    """Update imports in a single file. Returns True if file was modified."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply each mapping
        for pattern, replacement in IMPORT_MAPPINGS:
            content = re.sub(pattern, replacement, content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def main():
    """Main function to update all service files."""
    src_root = Path("/home/dotmac_framework/src")
    
    # Find all Python files that might import base services
    python_files = []
    for pattern in ["**/*service*.py", "**/services/**/*.py", "**/shared/**/*.py"]:
        python_files.extend(src_root.glob(pattern))
    
    # Remove duplicates
    python_files = list(set(python_files))
    
    updated_count = 0
    total_count = len(python_files)
    
    print(f"🔍 Processing {total_count} Python files...")
    
    for file_path in python_files:
        if update_file(file_path):
            updated_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Total files processed: {total_count}")
    print(f"   Files updated: {updated_count}")
    print(f"   Files unchanged: {total_count - updated_count}")

if __name__ == "__main__":
    main()