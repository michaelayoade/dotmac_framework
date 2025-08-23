"""Test customer functionality with real database."""

import asyncio
from uuid import uuid4
from sqlalchemy.orm import Session

from src.dotmac_isp.core.database import get_db, SessionLocal
from src.dotmac_isp.modules.identity.service import CustomerService
from src.dotmac_isp.modules.identity.schemas import CustomerCreateAPI
from src.dotmac_isp.modules.identity.models import CustomerType

def test_customer_database_creation():
    """Test customer creation with database persistence."""
    print("🧪 Testing customer creation with database...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create service with database session
        service = CustomerService(db)
        
        # Create test customer data with unique number
        import random
        unique_number = f"TEST-{random.randint(1000, 9999)}"
        customer_data = CustomerCreateAPI(
            customer_number=unique_number,
            display_name="Test Database Customer",
            customer_type=CustomerType.RESIDENTIAL,
            first_name="Test",
            last_name="Customer",
            email="test@database.com",
            phone="+1234567890"
        )
        
        print(f"Creating customer: {customer_data.customer_number}")
        
        # Test customer creation
        result = asyncio.run(service.create_customer(customer_data))
        
        print("✅ Customer created successfully!")
        print(f"   Portal ID: {result.portal_id}")
        print(f"   Portal Password: {result.portal_password}")
        print(f"   Customer Number: {result.customer_number}")
        print(f"   Display Name: {result.display_name}")
        print(f"   Customer Type: {result.customer_type}")
        print(f"   Database ID: {result.id}")
        
        # Verify in database
        from src.dotmac_isp.modules.identity.repository import CustomerRepository
        repo = CustomerRepository(db, service.tenant_id)
        
        db_customer = repo.get_by_customer_number(unique_number)
        if db_customer:
            print("✅ Customer verified in database!")
            print(f"   DB Portal ID: {db_customer.portal_id}")
            print(f"   DB Customer Number: {db_customer.customer_number}")
            print(f"   DB Display Name: {db_customer.display_name}")
        else:
            print("❌ Customer not found in database!")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_customer_retrieval():
    """Test customer retrieval from database."""
    print("\n🧪 Testing customer retrieval from database...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create service with database session
        service = CustomerService(db)
        
        # Try to retrieve any existing customer
        from src.dotmac_isp.modules.identity.repository import CustomerRepository
        repo = CustomerRepository(db, service.tenant_id)
        
        # Get the first customer from the database
        customers = repo.list(limit=1)
        if not customers:
            print("❌ No customers found in database!")
            return False
        
        db_customer = customers[0]
        if db_customer:
            print("✅ Customer found in database!")
            print(f"   Portal ID: {db_customer.portal_id}")
            print(f"   Customer Number: {db_customer.customer_number}")
            print(f"   Display Name: {db_customer.display_name}")
            print(f"   Created At: {db_customer.created_at}")
            return True
        else:
            print("❌ Customer not found in database!")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("🗄️ Testing Customer Module with Real Database\n")
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Customer creation
    total_tests += 1
    if test_customer_database_creation():
        success_count += 1
    
    # Test 2: Customer retrieval
    total_tests += 1
    if test_customer_retrieval():
        success_count += 1
    
    print(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED - Database integration working!")
    else:
        print("⚠️  Some tests failed - check database integration")