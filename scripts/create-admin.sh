#!/bin/bash
# =============================================================================
# DotMac Platform - Unified Admin User Creation Script
# =============================================================================
# Creates admin users for both Management Platform and ISP Framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

main() {
    echo -e "${BLUE}🚀 DotMac Platform - Admin User Creation${NC}"
    echo "==========================================="
    echo ""
    
    # Get user input with sensible defaults
    echo "📝 Enter admin user details (press Enter for defaults):"
    
    read -p "Admin email [admin@dotmac.local]: " admin_email
    admin_email=${admin_email:-"admin@dotmac.local"}
    
    echo "🔐 Password (or press Enter for default: 'admin123!')"
    read -s -p "Admin password: " admin_password
    admin_password=${admin_password:-"admin123!"}
    echo ""
    
    read -p "First name [Platform]: " first_name
    first_name=${first_name:-"Platform"}
    
    read -p "Last name [Admin]: " last_name
    last_name=${last_name:-"Admin"}
    
    echo ""
    echo "📋 Creating admin user with:"
    echo "  Email: $admin_email"
    echo "  Name: $first_name $last_name"
    echo "  Platforms: Management Platform + ISP Framework"
    echo ""
    
    # Create Management Platform admin
    print_status "Creating Management Platform admin user..."
    create_management_admin
    
    # Create ISP Framework admin
    print_status "Creating ISP Framework admin user..."
    create_isp_admin
    
    # Show credentials
    show_credentials
    
    print_success "Admin user creation complete for both platforms!"
}

create_management_admin() {
    if [ -d "management-platform" ]; then
        cd management-platform
        
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            
            # Create admin using Python script
            cat > create_mgmt_admin.py << EOF
#!/usr/bin/env python3
import asyncio
import sys
from app.database import get_async_session
from app.services.user_management_service import UserManagementService
from app.schemas.user import UserCreate
from sqlalchemy.ext.asyncio import AsyncSession

async def create_admin():
    try:
        async for session in get_async_session():
            user_service = UserManagementService(session)
            
            user_data = UserCreate(
                email="$admin_email",
                password="$admin_password", 
                first_name="$first_name",
                last_name="$last_name",
                role="admin",
                is_active=True,
                is_verified=True
            )
            
            user = await user_service.create_user(user_data)
            print(f"✅ Management Platform admin created: {user.email}")
            break
    except Exception as e:
        print(f"❌ Error creating Management Platform admin: {e}")

if __name__ == "__main__":
    asyncio.run(create_admin())
EOF
            
            python create_mgmt_admin.py || print_warning "Management Platform admin creation failed"
            rm -f create_mgmt_admin.py
        else
            print_warning "Management Platform virtual environment not found"
        fi
        
        cd ..
    else
        print_warning "Management Platform directory not found"
    fi
}

create_isp_admin() {
    if [ -d "isp-framework" ] && [ -f "isp-framework/scripts/create_admin.py" ]; then
        cd isp-framework
        
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            
            # Create ISP admin using existing script with automated input
            cat > admin_input.txt << EOF
default
$admin_email

$admin_password
$first_name
$last_name
EOF
            
            python scripts/create_admin.py < admin_input.txt || print_warning "ISP Framework admin creation failed"
            rm -f admin_input.txt
        else
            print_warning "ISP Framework virtual environment not found"
        fi
        
        cd ..
    else
        print_warning "ISP Framework admin creation script not found"
    fi
}

show_credentials() {
    echo ""
    echo -e "${GREEN}🔐 Admin Login Credentials:${NC}"
    echo "=============================="
    echo ""
    echo -e "${BLUE}📧 Email:${NC} $admin_email"
    echo -e "${BLUE}🔑 Password:${NC} $admin_password"
    echo ""
    echo -e "${YELLOW}🌐 Login URLs:${NC}"
    echo "  Management Platform: http://localhost:8000/docs"
    echo "  ISP Framework: http://localhost:8001/docs"
    echo "  Admin Portal: http://localhost:3000"
    echo ""
    echo -e "${YELLOW}💾 Credentials saved to:${NC} admin_credentials.txt"
    
    # Save credentials to file
    cat > admin_credentials.txt << EOF
DotMac Platform - Admin Credentials
==================================

Email: $admin_email
Password: $admin_password
Name: $first_name $last_name

Management Platform: http://localhost:8000
ISP Framework: http://localhost:8001
Admin Portal: http://localhost:3000

Created: $(date)
EOF
    
    echo ""
    echo -e "${RED}⚠️  Keep credentials secure and delete admin_credentials.txt after use!${NC}"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -d "management-platform" ] && [ ! -d "isp-framework" ]; then
    print_error "Please run this script from the DotMac Platform root directory"
    exit 1
fi

main "$@"