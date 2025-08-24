#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

"""Create initial admin user for DotMac ISP Framework."""

import asyncio
import sys
import os
from getpass import getpass

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from dotmac_isp.core.database import get_async_session
    from dotmac_isp.modules.identity.service import UserService
    from dotmac_isp.modules.identity.schemas import UserCreateSchema
    from dotmac_isp.shared.enums import UserRole
except ImportError as e:
logger.error(f"❌ Import error: {e}")
logger.info("💡 Make sure you're in the project root and have installed dependencies:")
logger.info("   pip install -e .")
    sys.exit(1)


async def create_admin_user():
    """Create the first admin user."""
logger.info("🚀 DotMac ISP Framework - Create Admin User")
logger.info("=" * 50)
    
    # Get user input with defaults
logger.info("📝 Enter admin user details (press Enter for defaults)")
    tenant_id = input("Tenant ID [default]: ").strip() or "default"
    email = input("Admin email [admin@dotmac.local]: ").strip() or "admin@dotmac.local"
    
logger.info(f"\n🔐 Password (or press Enter for default: 'admin123!')")
    password = getpass("Admin password: ").strip() or "admin123!"
    
    if len(password) < 8:
logger.info("❌ Password must be at least 8 characters!")
        sys.exit(1)
        
    first_name = input("First name [Admin]: ").strip() or "Admin"
    last_name = input("Last name [User]: ").strip() or "User"
    
logger.info(f"\n📋 Creating user with:")
logger.info(f"   Email: {email}")
logger.info(f"   Tenant: {tenant_id}")
logger.info(f"   Name: {first_name} {last_name}")
    
    try:
        # Get database session
        async for session in get_async_session():
            user_service = UserService(session, tenant_id)
            
            # Create admin user
            user_data = UserCreateSchema(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True
            )
            
            user = await user_service.create_user(user_data.dict())
            
logger.info(f"\n✅ Admin user created successfully!")
logger.info(f"   📧 Email: {user.email}")
logger.info(f"   👤 Role: {user.role}")
logger.info(f"   🏢 Tenant: {tenant_id}")
logger.info(f"   🆔 User ID: {user.id}")
            
            # Create login instructions
logger.info(f"\n🔐 Login Information:")
logger.info(f"   📧 Email: {email}")
logger.info(f"   🔑 Password: {password}")
logger.info(f"   🌐 Login URL: http://localhost:8000/api/v1/auth/login")
logger.info(f"   🎛️  Admin Portal: http://localhost:3000")
            
            # Save credentials to file
            cred_file = "admin_credentials.txt"
            with open(cred_file, "w") as f:
                f.write(f"DotMac ISP Framework - Admin Credentials\n")
                f.write(f"=====================================\n")
                f.write(f"Email: {email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"Tenant: {tenant_id}\n")
                f.write(f"User ID: {user.id}\n")
                f.write(f"Login URL: http://localhost:8000/api/v1/auth/login\n")
                f.write(f"Admin Portal: http://localhost:3000\n")
            
logger.info(f"\n💾 Credentials saved to: {cred_file}")
logger.info(f"   ⚠️  Keep this file secure and delete after use!")
            
            break
            
    except Exception as e:
logger.info(f"❌ Failed to create admin user: {e}")
logger.info(f"💡 Make sure PostgreSQL is running and database is initialized:")
logger.info(f"   docker-compose up -d postgres")
logger.info(f"   make setup-db")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_admin_user())