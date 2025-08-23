#!/usr/bin/env python3
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
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're in the project root and have installed dependencies:")
    print("   pip install -e .")
    sys.exit(1)


async def create_admin_user():
    """Create the first admin user."""
    print("🚀 DotMac ISP Framework - Create Admin User")
    print("=" * 50)
    
    # Get user input with defaults
    print("📝 Enter admin user details (press Enter for defaults)")
    tenant_id = input("Tenant ID [default]: ").strip() or "default"
    email = input("Admin email [admin@dotmac.local]: ").strip() or "admin@dotmac.local"
    
    print(f"\n🔐 Password (or press Enter for default: 'admin123!')")
    password = getpass("Admin password: ").strip() or "admin123!"
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters!")
        sys.exit(1)
        
    first_name = input("First name [Admin]: ").strip() or "Admin"
    last_name = input("Last name [User]: ").strip() or "User"
    
    print(f"\n📋 Creating user with:")
    print(f"   Email: {email}")
    print(f"   Tenant: {tenant_id}")
    print(f"   Name: {first_name} {last_name}")
    
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
            
            print(f"\n✅ Admin user created successfully!")
            print(f"   📧 Email: {user.email}")
            print(f"   👤 Role: {user.role}")
            print(f"   🏢 Tenant: {tenant_id}")
            print(f"   🆔 User ID: {user.id}")
            
            # Create login instructions
            print(f"\n🔐 Login Information:")
            print(f"   📧 Email: {email}")
            print(f"   🔑 Password: {password}")
            print(f"   🌐 Login URL: http://localhost:8000/api/v1/auth/login")
            print(f"   🎛️  Admin Portal: http://localhost:3000")
            
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
            
            print(f"\n💾 Credentials saved to: {cred_file}")
            print(f"   ⚠️  Keep this file secure and delete after use!")
            
            break
            
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        print(f"💡 Make sure PostgreSQL is running and database is initialized:")
        print(f"   docker-compose up -d postgres")
        print(f"   make setup-db")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_admin_user())