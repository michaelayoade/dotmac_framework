#!/usr/bin/env python3
"""
Strategic cleanup to reduce 6,417 files to manageable size
"""

import os
from pathlib import Path

def analyze_cleanup_potential():
    """Identify files that can be safely removed/consolidated."""
    root = Path('/home/dotmac_framework')
    
    # Files we can immediately consolidate/remove
    cleanup_targets = {
        'duplicate_configs': [],
        'duplicate_requirements': [], 
        'test_artifacts': [],
        'build_artifacts': [],
        'redundant_utilities': []
    }
    
    # Find duplicate requirement files
    for req_file in root.rglob('requirements*.txt'):
        if 'consolidated' not in req_file.name:
            cleanup_targets['duplicate_requirements'].append(req_file)
    
    # Find test artifacts 
    for test_dir in ['test-results', 'coverage', '_build', 'htmlcov', '__pycache__']:
        for artifact in root.rglob(test_dir):
            cleanup_targets['test_artifacts'].append(artifact)
    
    # Find duplicate docker configs
    for compose_file in root.rglob('docker-compose*.yml'):
        cleanup_targets['duplicate_configs'].append(compose_file)
    
    # Find redundant utility files
    util_patterns = ['utils.py', 'helpers.py', 'common.py']
    for pattern in util_patterns:
        utils = list(root.rglob(pattern))
        if len(utils) > 1:
            cleanup_targets['redundant_utilities'].extend(utils)
    
    return cleanup_targets

def main():
    print("🧹 Strategic Cleanup Analysis")
    print("=" * 40)
    
    targets = analyze_cleanup_potential()
    
    total_files = 0
    for category, files in targets.items():
        count = len(files)
        total_files += count
        print(f"\n{category.replace('_', ' ').title()}: {count} files")
        for file in files[:5]:  # Show first 5
            print(f"  - {file}")
        if count > 5:
            print(f"  ... and {count - 5} more")
    
    print(f"\n💡 Cleanup Potential:")
    print(f"  Files to remove/consolidate: {total_files}")
    print(f"  Estimated reduction: {total_files / 6417 * 100:.1f}%")
    
    print(f"\n🎯 Recommended Actions:")
    print(f"  1. Replace {len(targets['duplicate_requirements'])} requirement files with 1")
    print(f"  2. Clean {len(targets['test_artifacts'])} test artifacts")  
    print(f"  3. Consolidate {len(targets['duplicate_configs'])} config files")
    print(f"  4. Merge {len(targets['redundant_utilities'])} utility files")

if __name__ == "__main__":
    main()