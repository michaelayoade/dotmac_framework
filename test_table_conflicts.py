#!/usr/bin/env python3
"""
Test script to check for remaining SQLAlchemy table conflicts.
"""
import sys
import os

# Add paths to Python path
sys.path.insert(0, os.path.join(os.getcwd(), 'isp-framework/src'))
sys.path.insert(0, os.path.join(os.getcwd(), 'management-platform'))

def test_isp_framework_tables():
    """Test ISP framework for table conflicts."""
    try:
        from dotmac_isp.modules.omnichannel.models import CustomerContact as ModelsContact
        from dotmac_isp.modules.omnichannel.models_production import CustomerContact as ProductionContact
        
        print("✅ ISP Framework omnichannel models import successfully")
        print(f"Models table: {ModelsContact.__tablename__}")
        print(f"Production table: {ProductionContact.__tablename__}")
        
        if ModelsContact.__tablename__ == ProductionContact.__tablename__:
            print("✅ Table names match - no conflicts")
            return True
        else:
            print("❌ Table names don't match - conflict detected")
            return False
            
    except Exception as e:
        print(f"❌ Error testing ISP framework tables: {e}")
        return False

def test_management_platform_tables():
    """Test management platform for table conflicts."""
    try:
        from app.models.user import User
        from app.models.tenant import Tenant
        
        print("✅ Management Platform models import successfully")
        print(f"User table: {User.__tablename__}")
        print(f"Tenant table: {Tenant.__tablename__}")
        
        return True
            
    except Exception as e:
        print(f"❌ Error testing Management platform tables: {e}")
        return False

def main():
    """Run all table conflict tests."""
    print("Testing for remaining SQLAlchemy table conflicts...\n")
    
    isp_ok = test_isp_framework_tables()
    print()
    mgmt_ok = test_management_platform_tables()
    
    print("\n" + "="*50)
    if isp_ok and mgmt_ok:
        print("✅ All tests passed - no table conflicts detected!")
        return 0
    else:
        print("❌ Some tests failed - conflicts still exist!")
        return 1

if __name__ == "__main__":
    sys.exit(main())