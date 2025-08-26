#!/usr/bin/env python3
"""
Fix missing dependencies across the DotMac platform.
This script addresses:
1. Missing OpenTelemetry instrumentation packages
2. Timezone import standardization
3. Other missing packages identified in error logs
"""

import os
import re
from pathlib import Path

def update_main_requirements():
    """Update main requirements.txt with missing observability packages."""
    
    requirements_path = Path("requirements.txt")
    
    # Read existing requirements
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            content = f.read()
    else:
        content = "# DotMac Platform - Unified Dependencies\n\n"
    
    # Add missing OpenTelemetry packages if not present
    missing_packages = [
        "# ===== OBSERVABILITY & TRACING =====",
        "opentelemetry-api>=1.22.0",
        "opentelemetry-sdk>=1.22.0",
        "opentelemetry-instrumentation>=0.43b0",
        "opentelemetry-instrumentation-fastapi>=0.43b0",
        "opentelemetry-instrumentation-sqlalchemy>=0.43b0",
        "opentelemetry-instrumentation-redis>=0.43b0",
        "opentelemetry-instrumentation-httpx>=0.43b0",
        "opentelemetry-instrumentation-requests>=0.43b0",
        "opentelemetry-instrumentation-urllib3>=0.43b0",
        "opentelemetry-instrumentation-asyncio>=0.43b0",
        "opentelemetry-instrumentation-celery>=0.43b0",
        "opentelemetry-instrumentation-system-metrics>=0.43b0",
        "opentelemetry-exporter-otlp>=1.22.0",
        "opentelemetry-propagator-b3>=1.22.0",
        "opentelemetry-propagator-jaeger>=1.22.0",
        "",
        "# ===== ADDITIONAL DATETIME SUPPORT =====",
        "pytz>=2023.3",
        ""
    ]
    
    # Check if observability section already exists
    if "opentelemetry-api" not in content:
        content += "\n" + "\n".join(missing_packages)
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        print(f"✅ Updated {requirements_path} with missing dependencies")
    else:
        print(f"⚠️ OpenTelemetry packages already present in {requirements_path}")

def fix_datetime_imports():
    """Find and fix files that use timezone without proper imports."""
    
    files_fixed = 0
    
    # Find Python files that might have timezone import issues
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip_dir in root for skip_dir in ['.git', '__pycache__', 'node_modules', '.venv']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if file uses timezone but doesn't import it properly
                    if 'timezone.utc' in content or 'datetime.now(timezone' in content:
                        lines = content.split('\n')
                        has_timezone_import = False
                        
                        # Check existing imports
                        for line in lines[:20]:  # Check first 20 lines for imports
                            if ('from datetime import' in line and 'timezone' in line) or \
                               ('import datetime' in line):
                                has_timezone_import = True
                                break
                        
                        if not has_timezone_import:
                            # Find the best place to add the import
                            import_line_idx = 0
                            for i, line in enumerate(lines):
                                if line.startswith('from datetime import') or line.startswith('import datetime'):
                                    # Update existing datetime import
                                    if 'from datetime import' in line and 'timezone' not in line:
                                        if ', timezone' not in line:
                                            lines[i] = line.rstrip() + ', timezone'
                                            has_timezone_import = True
                                            break
                                elif line.startswith('import ') or line.startswith('from '):
                                    import_line_idx = i + 1
                            
                            if not has_timezone_import:
                                # Add new import after other imports
                                lines.insert(import_line_idx, 'from datetime import timezone')
                            
                            # Write back the fixed content
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(lines))
                            
                            files_fixed += 1
                            print(f"Fixed timezone import in: {filepath}")
                
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    
    return files_fixed

def create_dependency_check_script():
    """Create a script to check for missing dependencies."""
    
    script_content = '''#!/usr/bin/env python3
"""
Check for missing dependencies in the DotMac platform.
"""

import importlib
import sys
from datetime import timezone

def check_packages():
    """Check if all required packages are available."""
    
    required_packages = [
        'opentelemetry',
        'opentelemetry.instrumentation.fastapi',
        'opentelemetry.instrumentation.sqlalchemy', 
        'opentelemetry.instrumentation.redis',
        'opentelemetry.instrumentation.httpx',
        'opentelemetry.instrumentation.urllib3',
        'fastapi',
        'sqlalchemy',
        'redis',
        'celery',
        'pydantic'
    ]
    
    missing = []
    available = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            available.append(package)
        except ImportError:
            missing.append(package)
    
    print("📦 Dependency Check Results")
    print("=" * 40)
    
    if available:
        print(f"✅ Available ({len(available)}):")
        for pkg in available:
            print(f"  - {pkg}")
    
    if missing:
        print(f"\\n❌ Missing ({len(missing)}):")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\\n🔧 To install missing packages:")
        print("pip install opentelemetry-instrumentation[fastapi,sqlalchemy,redis,httpx,urllib3]")
    else:
        print("\\n🎉 All required packages are available!")
    
    return len(missing) == 0

if __name__ == "__main__":
    success = check_packages()
    sys.exit(0 if success else 1)
'''
    
    with open('check_dependencies.py', 'w') as f:
        f.write(script_content)
    
    # Make it executable
    os.chmod('check_dependencies.py', 0o755)
    print("✅ Created dependency check script: check_dependencies.py")

def main():
    """Main function to fix all missing dependencies."""
    print("🔧 Fixing missing dependencies in DotMac platform...")
    
    # 1. Update main requirements file
    update_main_requirements()
    
    # 2. Fix datetime imports
    print("\\n🕐 Fixing datetime timezone imports...")
    fixed_count = fix_datetime_imports()
    print(f"Fixed timezone imports in {fixed_count} files")
    
    # 3. Create dependency checker
    print("\\n📋 Creating dependency check script...")
    create_dependency_check_script()
    
    print("\\n✅ Missing dependencies fixes completed!")
    print("\\nNext steps:")
    print("1. Run: pip install -r requirements.txt")
    print("2. Run: python check_dependencies.py")
    print("3. Test the application to ensure all imports work")

if __name__ == "__main__":
    main()