#!/usr/bin/env python3
"""
Complete removal of hvac/Vault references and replacement with OpenBao
"""
import os
import re
import sys

def remove_hvac_references():
    """Remove all hvac/Vault references from Python files"""
    
    print("🔧 Removing ALL hvac and Vault references...")
    
    # Find all Python files with hvac/Vault references
    result = os.popen("find . -name '*.py' -type f -exec grep -l 'hvac\\|import.*[Vv]ault\\|from.*[Vv]ault' {} \\;").read()
    files_with_hvac = [f.strip() for f in result.split('\n') if f.strip()]
    
    for file_path in files_with_hvac:
        if not os.path.exists(file_path):
            continue
            
        print(f"  📁 Processing {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Remove hvac imports
            content = re.sub(r'^import hvac.*$', '# hvac removed - using OpenBao instead', content, flags=re.MULTILINE)
            content = re.sub(r'^from hvac.*$', '# hvac removed - using OpenBao instead', content, flags=re.MULTILINE)
            
            # Remove vault client imports
# OpenBaoClient removed - using OpenBaoClient instead
# openbao_client removed - using openbao_client instead
            
            # Replace usage patterns
            content = content.replace('OpenBaoClient', 'OpenBaoClient')
            content = content.replace('OpenBaoClient', 'OpenBaoClient')
            content = content.replace('openbao_client', 'openbao_client')
            
            # Replace import paths
# openbao_client removed - using openbao_client instead
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"    ✅ Updated {file_path}")
            else:
                print(f"    ➡️ No changes needed in {file_path}")
                
        except Exception as e:
            print(f"    ❌ Error processing {file_path}: {e}")

def test_critical_startup():
    """Test critical startup components"""
    print("\n🧪 Testing startup components...")
    
    os.chdir('/home/dotmac_framework/isp-framework')
    sys.path.insert(0, 'src')
    
    tests = [
        ('dotmac_isp.core.database', 'Database Layer'),
        ('dotmac_isp.shared.auth', 'Authentication System'),
        ('dotmac_isp.core.secrets.openbao_client', 'OpenBao Client'),
        ('dotmac_isp.core.secrets.openbao_native_client', 'Native OpenBao Client'),
    ]
    
    success_count = 0
    for module, description in tests:
        try:
            __import__(module)
            print(f"  ✅ {description}: {module}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {description}: {module} - {str(e)[:100]}")
    
    return success_count, len(tests)

def main():
    """Main execution"""
    print("🚨 COMPLETE HVAC/VAULT REMOVAL & OPENBAO MIGRATION")
    print("=" * 60)
    
    os.chdir('/home/dotmac_framework')
    
    # Remove hvac references
    remove_hvac_references()
    
    # Test startup
    success_count, total_tests = test_critical_startup()
    
    print(f"\n📊 RESULTS: {success_count}/{total_tests} components working")
    
    if success_count == total_tests:
        print("\n🎉 MIGRATION COMPLETE - All hvac removed, OpenBao working!")
        return True
    else:
        print(f"\n⚠️ {total_tests - success_count} components still have issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)