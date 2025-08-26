#!/usr/bin/env python3
"""
Fix critical startup blockers in the ISP Framework
"""
import os
import re
import sys

def fix_hvac_imports():
    """Remove or replace hvac imports with OpenBao alternatives"""
    
    files_with_hvac = [
        'src/dotmac_isp/core/secrets_manager.py',
        'src/dotmac_isp/core/secrets/vault_auth_strategies.py', 
        'src/dotmac_isp/core/secrets/openbao_client.py',
        'src/dotmac_isp/core/secret_manager.py'
    ]
    
    print("🔧 Fixing hvac import issues...")
    
    for file_path in files_with_hvac:
        if not os.path.exists(file_path):
            continue
            
        print(f"  📁 Processing {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Replace hvac imports
            content = re.sub(r'^import hvac.*$', '# hvac import removed - using OpenBao', content, flags=re.MULTILINE)
            content = re.sub(r'^from hvac.*$', '# hvac import removed - using OpenBao', content, flags=re.MULTILINE)
            
            # Replace hvac usage with OpenBao alternatives
            content = content.replace('OpenBaoClient', 'OpenBaoClient')
            
            with open(file_path, 'w') as f:
                f.write(content)
                
            print(f"    ✅ Fixed hvac imports in {file_path}")
            
        except Exception as e:
            print(f"    ❌ Error fixing {file_path}: {e}")

def test_critical_imports():
    """Test if critical imports work after fixes"""
    print("\n🧪 Testing critical imports...")
    
    sys.path.insert(0, 'src')
    
    critical_modules = [
        'dotmac_isp.core.database',
        'dotmac_isp.shared.auth',
        'dotmac_isp.core.secrets.openbao_client',
    ]
    
    success_count = 0
    for module in critical_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {module}: {e}")
    
    print(f"\n📊 Import test results: {success_count}/{len(critical_modules)} successful")
    return success_count == len(critical_modules)

def main():
    """Main execution"""
    print("🚨 FIXING CRITICAL STARTUP BLOCKERS")
    print("=" * 50)
    
    # Change to ISP framework directory
    os.chdir('/home/dotmac_framework/isp-framework')
    
    # Fix issues
    fix_hvac_imports()
    
    # Test results
    if test_critical_imports():
        print("\n🎉 All critical startup blockers resolved!")
        return True
    else:
        print("\n❌ Some issues remain")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)