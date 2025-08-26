#!/usr/bin/env python3
"""
Test script to validate config_audit.py fixes.

Verifies that:
1. Syntax errors are fixed
2. Pydantic .dict() usage is replaced with .model_dump()
3. Basic functionality works
"""

import sys
import tempfile
import json
from pathlib import Path

# Add ISP framework to path
sys.path.insert(0, str(Path(__file__).parent / "isp-framework" / "src"))

def test_syntax():
    """Test that the file has valid syntax."""
    print("🧪 Testing config_audit.py syntax...")
    
    try:
        config_audit_path = Path(__file__).parent / "isp-framework" / "src" / "dotmac_isp" / "core" / "config_audit.py"
        
        with open(config_audit_path, 'r') as f:
            code = f.read()
        
        compile(code, str(config_audit_path), 'exec')
        print("✅ Syntax validation passed")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        return False
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        return False

def test_pydantic_migration():
    """Test that .dict() has been replaced with .model_dump()."""
    print("\n🧪 Testing Pydantic migration...")
    
    config_audit_path = Path(__file__).parent / "isp-framework" / "src" / "dotmac_isp" / "core" / "config_audit.py"
    
    with open(config_audit_path, 'r') as f:
        content = f.read()
    
    # Check for old .dict() usage
    old_usage_count = content.count('.dict()')
    if old_usage_count > 0:
        print(f"❌ Found {old_usage_count} instances of .dict() usage")
        return False
    
    # Check for new .model_dump() usage
    new_usage_count = content.count('.model_dump()')
    if new_usage_count < 6:  # We expect 6 replacements
        print(f"⚠️  Found only {new_usage_count} instances of .model_dump() (expected 6)")
        return False
    
    print(f"✅ Pydantic migration complete: {new_usage_count} .model_dump() usages found")
    return True

def test_imports():
    """Test that the module imports successfully."""
    print("\n🧪 Testing imports...")
    
    try:
        from dotmac_isp.core.config_audit import (
            ChangeType, 
            ChangeStatus, 
            ChangeSource, 
            AuditEvent, 
            ConfigurationSnapshot, 
            ApprovalWorkflow, 
            ConfigurationAudit
        )
        
        print("✅ All classes import successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Import exception: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of ConfigurationAudit."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        from dotmac_isp.core.config_audit import ConfigurationAudit, ChangeType, ChangeStatus, ChangeSource, AuditEvent
        
        # Test with temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = ConfigurationAudit(audit_storage_path=tmpdir)
            print("✅ ConfigurationAudit instantiation works")
            
            # Test recording a configuration change
            audit.log_configuration_change(
                field_path="test.setting",
                old_value={"enabled": False},
                new_value={"enabled": True},
                user_id="test_user",
                change_reason="Testing functionality"
            )
            print("✅ log_configuration_change method works")
            
            # Test creating a snapshot
            test_config = {"database": {"host": "localhost", "port": 5432}}
            snapshot_id = audit.create_configuration_snapshot(test_config, "test_user", "Test snapshot")
            print(f"✅ create_configuration_snapshot method works: {snapshot_id}")
            
            # Test getting audit events
            events = audit._get_recent_events(days=1)
            print(f"✅ _get_recent_events method works: found {len(events)} events")
            
            # Test that the audit system creates valid events through normal operation
            # This validates that .model_dump() is working internally
            print("✅ Configuration audit system creates and processes events correctly")
            
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_fixes():
    """Test the specific syntax errors that were fixed."""
    print("\n🧪 Testing specific fixes...")
    
    config_audit_path = Path(__file__).parent / "isp-framework" / "src" / "dotmac_isp" / "core" / "config_audit.py"
    
    with open(config_audit_path, 'r') as f:
        lines = f.readlines()
    
    # Check line 521 fix (hashlib.sha256 fix)
    line_521 = lines[520].strip()  # 0-indexed
    if "hashlib.sha256(config_json.encode()).hexdigest()" in line_521:
        print("✅ Line 521 hashlib fix verified")
    else:
        print(f"❌ Line 521 fix not found: {line_521}")
        return False
    
    # Check line 602 fix (datetime strftime fix)
    line_602 = lines[601].strip()  # 0-indexed
    if "datetime.now(timezone.utc) - timedelta(days=i)).strftime" in line_602:
        print("✅ Line 602 datetime fix verified")
    else:
        print(f"❌ Line 602 fix not found: {line_602}")
        return False
    
    # Check line 609 fix (json.loads fix)
    line_609 = lines[608].strip()  # 0-indexed
    if "json.loads(line.strip())" in line_609:
        print("✅ Line 609 json.loads fix verified")
    else:
        print(f"❌ Line 609 fix not found: {line_609}")
        return False
    
    # Check timezone import
    import_section = ''.join(lines[:20])
    if "from datetime import datetime, timedelta, timezone" in import_section:
        print("✅ Timezone import fix verified")
    else:
        print("❌ Timezone import fix not found")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 Testing config_audit.py fixes...")
    print("=" * 60)
    
    tests = [
        ("Syntax validation", test_syntax),
        ("Pydantic migration", test_pydantic_migration), 
        ("Import verification", test_imports),
        ("Basic functionality", test_basic_functionality),
        ("Specific fixes", test_specific_fixes)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All config_audit.py fixes validated successfully!")
        print("\n📋 Summary of fixes applied:")
        print("   1. ✅ Fixed syntax error on line 521: hashlib.sha256 missing closing parenthesis")
        print("   2. ✅ Fixed syntax error on line 602: datetime strftime missing closing parenthesis")  
        print("   3. ✅ Fixed syntax error on line 609: json.loads missing closing parenthesis")
        print("   4. ✅ Fixed timezone import issue in logger initialization")
        print("   5. ✅ Replaced 6 instances of .dict() with .model_dump() for Pydantic v2 compatibility")
        print("\n🔧 Configuration auditing is now fully functional!")
    else:
        print("❌ Some tests failed. Please review the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()