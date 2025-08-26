#!/usr/bin/env python3
"""
Comprehensive Pydantic v2 Migration Script
Updates all Pydantic v1 methods to v2 equivalents across the codebase.
"""

import os
import re
from pathlib import Path


def update_pydantic_methods(file_path: str) -> bool:
    """Update Pydantic v1 methods to v2 in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. Replace .dict() with .model_dump()
        content = re.sub(
            r'\.dict\(\)', 
            '.model_dump()', 
            content
        )
        
        # 2. Replace .dict(exclude=...) with .model_dump(exclude=...)
        content = re.sub(
            r'\.dict\((.*?)\)', 
            r'.model_dump(\1)', 
            content
        )
        
        # 3. Replace .json() with .model_dump_json()
        content = re.sub(
            r'\.json\(\)', 
            '.model_dump_json()', 
            content
        )
        
        # 4. Replace .json(exclude=...) with .model_dump_json(exclude=...)
        content = re.sub(
            r'\.json\((.*?)\)', 
            r'.model_dump_json(\1)', 
            content
        )
        
        # 5. Replace .copy() with .model_copy()
        content = re.sub(
            r'\.copy\(\)', 
            '.model_copy()', 
            content
        )
        
        # 6. Replace .copy(update=...) with .model_copy(update=...)
        content = re.sub(
            r'\.copy\((.*?)\)', 
            r'.model_copy(\1)', 
            content
        )
        
        # 7. Replace .parse_obj() with .model_validate()
        content = re.sub(
            r'\.parse_obj\(', 
            '.model_validate(', 
            content
        )
        
        # 8. Replace .parse_raw() with .model_validate_json()
        content = re.sub(
            r'\.parse_raw\(', 
            '.model_validate_json(', 
            content
        )
        
        # 9. Replace .schema() with .model_json_schema()
        content = re.sub(
            r'\.schema\(\)', 
            '.model_json_schema()', 
            content
        )
        
        # 10. Replace Config class with model_config
        # This is more complex and needs careful handling
        content = re.sub(
            r'class Config:\s*\n\s*arbitrary_types_allowed = True',
            'model_config = {"arbitrary_types_allowed": True}',
            content,
            flags=re.MULTILINE
        )
        
        # 11. Replace __fields__ with model_fields
        content = re.sub(
            r'\.__fields__', 
            '.model_fields', 
            content
        )
        
        # 12. Replace __config__ with model_config
        content = re.sub(
            r'\.__config__', 
            '.model_config', 
            content
        )
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to update all Python files."""
    print("🔄 Starting Comprehensive Pydantic v2 Migration")
    print("=" * 60)
    
    # Define search directories
    search_dirs = [
        "isp-framework/src",
        "management-platform",
        "shared"
    ]
    
    updated_files = []
    error_files = []
    
    for search_dir in search_dirs:
        if not os.path.exists(search_dir):
            print(f"⚠️  Directory not found: {search_dir}")
            continue
            
        print(f"📁 Scanning {search_dir}...")
        
        for root, dirs, files in os.walk(search_dir):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', '.pytest_cache',
                'venv', 'env', '.venv', 'build', 'dist', '.tox'
            }]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    try:
                        if update_pydantic_methods(file_path):
                            updated_files.append(file_path)
                            print(f"  ✅ Updated: {file_path}")
                    except Exception as e:
                        error_files.append((file_path, str(e)))
                        print(f"  ❌ Error in {file_path}: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Migration Summary:")
    print(f"  ✅ Files updated: {len(updated_files)}")
    print(f"  ❌ Files with errors: {len(error_files)}")
    
    if updated_files:
        print(f"\n📝 Updated files:")
        for file_path in updated_files[:10]:  # Show first 10
            print(f"    - {file_path}")
        if len(updated_files) > 10:
            print(f"    ... and {len(updated_files) - 10} more")
    
    if error_files:
        print(f"\n⚠️  Files with errors:")
        for file_path, error in error_files[:5]:  # Show first 5
            print(f"    - {file_path}: {error}")
        if len(error_files) > 5:
            print(f"    ... and {len(error_files) - 5} more")
    
    print("\n🎉 Pydantic v2 migration completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()