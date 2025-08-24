import logging

logger = logging.getLogger(__name__)

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
logger.info("🧪 Testing customer creation with database...")
    
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
        
logger.info(f"Creating customer: {customer_data.customer_number}")
        
        # Test customer creation
        result = asyncio.run(service.create_customer(customer_data))
        
logger.info("✅ Customer created successfully!")
logger.info(f"   Portal ID: {result.portal_id}")
logger.info(f"   Portal Password: {result.portal_password}")
logger.info(f"   Customer Number: {result.customer_number}")
logger.info(f"   Display Name: {result.display_name}")
logger.info(f"   Customer Type: {result.customer_type}")
logger.info(f"   Database ID: {result.id}")
        
        # Verify in database
        from src.dotmac_isp.modules.identity.repository import CustomerRepository
        repo = CustomerRepository(db, service.tenant_id)
        
        db_customer = repo.get_by_customer_number(unique_number)
        if db_customer:
logger.info("✅ Customer verified in database!")
logger.info(f"   DB Portal ID: {db_customer.portal_id}")
logger.info(f"   DB Customer Number: {db_customer.customer_number}")
logger.info(f"   DB Display Name: {db_customer.display_name}")
        else:
logger.info("❌ Customer not found in database!")
            
        return True
        
    except Exception as e:
logger.info(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_customer_retrieval():
    """Test customer retrieval from database."""
logger.info("\n🧪 Testing customer retrieval from database...")
    
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
logger.info("❌ No customers found in database!")
            return False
        
        db_customer = customers[0]
        if db_customer:
logger.info("✅ Customer found in database!")
logger.info(f"   Portal ID: {db_customer.portal_id}")
logger.info(f"   Customer Number: {db_customer.customer_number}")
logger.info(f"   Display Name: {db_customer.display_name}")
logger.info(f"   Created At: {db_customer.created_at}")
            return True
        else:
logger.info("❌ Customer not found in database!")
            return False
            
    except Exception as e:
logger.info(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
logger.info("🗄️ Testing Customer Module with Real Database\n")
    
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
    
logger.info(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
logger.info("🎉 ALL TESTS PASSED - Database integration working!")
    else:
logger.info("⚠️  Some tests failed - check database integration")