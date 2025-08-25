#!/usr/bin/env python3
"""
Strategic Dependency Consolidation Tool
Analyzes and consolidates duplicate dependencies across the project.
"""

import os
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, Set, List, Tuple

def find_requirement_files(root_path: Path) -> List[Path]:
    """Find all requirements files in the project."""
    req_files = []
    for pattern in ['requirements*.txt', 'pyproject.toml', 'package.json']:
        if '*' in pattern:
            for file in root_path.rglob(pattern):
                if 'node_modules' not in str(file) and '.git' not in str(file):
                    req_files.append(file)
    return req_files

def parse_requirements(file_path: Path) -> Dict[str, str]:
    """Parse a requirements.txt file into package->version mapping."""
    packages = {}
    
    if not file_path.exists():
        return packages
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Handle various requirement formats
                    if '==' in line:
                        name, version = line.split('==', 1)
                        packages[name.split('[')[0].strip()] = version.strip()
                    elif '>=' in line:
                        name = line.split('>=')[0].split('[')[0].strip()
                        version = line.split('>=')[1].strip()
                        packages[name] = f">={version}"
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
    
    return packages

def analyze_duplicates(root_path: Path) -> Dict:
    """Analyze duplicate dependencies across all files."""
    req_files = find_requirement_files(root_path)
    all_packages = defaultdict(list)  # package -> [(file, version)]
    file_packages = {}  # file -> {package: version}
    
    print(f"🔍 Analyzing {len(req_files)} dependency files...")
    
    for file_path in req_files:
        if file_path.suffix == '.txt':
            packages = parse_requirements(file_path)
            file_packages[file_path] = packages
            
            for package, version in packages.items():
                all_packages[package].append((file_path, version))
    
    # Find duplicates and conflicts
    duplicates = {}
    conflicts = {}
    
    for package, occurrences in all_packages.items():
        if len(occurrences) > 1:
            duplicates[package] = occurrences
            versions = [version for _, version in occurrences]
            if len(set(versions)) > 1:
                conflicts[package] = occurrences
    
    return {
        'files': req_files,
        'file_packages': file_packages,
        'duplicates': duplicates,
        'conflicts': conflicts,
        'all_packages': dict(all_packages)
    }

def generate_consolidated_requirements(analysis: Dict) -> str:
    """Generate a consolidated requirements.txt."""
    # Count package usage and pick most common versions
    package_versions = Counter()
    
    for package, occurrences in analysis['duplicates'].items():
        for file_path, version in occurrences:
            package_versions[f"{package}=={version}"] += 1
    
    # Build consolidated file
    consolidated = []
    consolidated.append("# CONSOLIDATED REQUIREMENTS")
    consolidated.append("# Auto-generated from dependency analysis")
    consolidated.append("")
    
    # Group by category
    web_frameworks = []
    databases = []
    testing = []
    utilities = []
    other = []
    
    for package, occurrences in analysis['duplicates'].items():
        # Pick most common version
        versions = [version for _, version in occurrences]
        most_common_version = Counter(versions).most_common(1)[0][0]
        
        entry = f"{package}=={most_common_version}"
        
        # Categorize
        if package.lower() in ['fastapi', 'uvicorn', 'starlette', 'flask', 'django']:
            web_frameworks.append(entry)
        elif package.lower() in ['sqlalchemy', 'asyncpg', 'psycopg2', 'redis', 'aioredis']:
            databases.append(entry)
        elif package.lower() in ['pytest', 'pytest-asyncio', 'pytest-cov', 'coverage']:
            testing.append(entry)
        elif package.lower() in ['pydantic', 'click', 'typer', 'python-dotenv']:
            utilities.append(entry)
        else:
            other.append(entry)
    
    # Add categorized sections
    if web_frameworks:
        consolidated.append("# Web Frameworks")
        consolidated.extend(sorted(web_frameworks))
        consolidated.append("")
        
    if databases:
        consolidated.append("# Databases & Caching") 
        consolidated.extend(sorted(databases))
        consolidated.append("")
        
    if utilities:
        consolidated.append("# Core Utilities")
        consolidated.extend(sorted(utilities))
        consolidated.append("")
        
    if testing:
        consolidated.append("# Testing")
        consolidated.extend(sorted(testing))
        consolidated.append("")
        
    if other:
        consolidated.append("# Other Dependencies")
        consolidated.extend(sorted(other))
    
    return '\n'.join(consolidated)

def main():
    """Main analysis function."""
    root = Path('/home/dotmac_framework')
    
    print("🚀 DotMac Dependency Consolidation Analysis")
    print("=" * 50)
    
    analysis = analyze_duplicates(root)
    
    print(f"\n📊 Analysis Results:")
    print(f"  Total dependency files: {len(analysis['files'])}")
    print(f"  Duplicate packages: {len(analysis['duplicates'])}")
    print(f"  Version conflicts: {len(analysis['conflicts'])}")
    
    print(f"\n🔥 Top Duplicate Packages:")
    for package, occurrences in sorted(analysis['duplicates'].items(), 
                                      key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {package}: {len(occurrences)} files")
        for file_path, version in occurrences[:3]:  # Show first 3
            rel_path = file_path.relative_to(root)
            print(f"    - {rel_path}: {version}")
        if len(occurrences) > 3:
            print(f"    ... and {len(occurrences) - 3} more")
    
    print(f"\n⚠️  Version Conflicts:")
    if not analysis['conflicts']:
        print("  ✅ No version conflicts found!")
    else:
        for package, occurrences in analysis['conflicts'].items():
            versions = [version for _, version in occurrences]
            print(f"  {package}: {set(versions)}")
    
    # Generate consolidated requirements
    consolidated = generate_consolidated_requirements(analysis)
    
    with open(root / 'requirements-consolidated.txt', 'w') as f:
        f.write(consolidated)
    
    print(f"\n💡 Strategic Recommendations:")
    print(f"  1. Replace {len(analysis['files'])} files with 1 consolidated file")
    print(f"  2. Fix {len(analysis['conflicts'])} version conflicts")
    print(f"  3. Potential reduction: ~{len(analysis['duplicates']) * len(analysis['files']) * 0.8:.0f} duplicate lines")
    print(f"\n📁 Generated: requirements-consolidated.txt")

if __name__ == "__main__":
    main()