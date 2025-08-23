#!/usr/bin/env python3
"""
Test database setup script for DotMac Management Platform.
Creates and configures PostgreSQL test database for development and CI.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg


async def create_test_database():
    """Create and configure the test database."""
    # Database connection parameters
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    admin_user = os.getenv("DB_ADMIN_USER", "postgres")
    admin_password = os.getenv("DB_ADMIN_PASSWORD", "postgres")
    
    # Test database parameters
    test_db_name = "test_dotmac_platform"
    test_user = "test_user"
    test_password = "test_password"
    
    print("🔧 Setting up PostgreSQL test database...")
    
    try:
        # Connect as admin user
        admin_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            database="postgres"
        )
        
        print(f"✅ Connected to PostgreSQL as {admin_user}")
        
        # Drop test database if exists
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
        print(f"🗑️  Dropped existing database: {test_db_name}")
        
        # Drop test user if exists
        await admin_conn.execute(f"DROP USER IF EXISTS {test_user}")
        print(f"🗑️  Dropped existing user: {test_user}")
        
        # Create test user
        await admin_conn.execute(f"""
            CREATE USER {test_user} 
            WITH PASSWORD '{test_password}' 
            CREATEDB LOGIN
        """)
        print(f"👤 Created test user: {test_user}")
        
        # Create test database
        await admin_conn.execute(f"""
            CREATE DATABASE {test_db_name} 
            OWNER {test_user}
            ENCODING 'UTF8'
            LC_COLLATE = 'en_US.UTF-8'
            LC_CTYPE = 'en_US.UTF-8'
        """)
        print(f"📊 Created test database: {test_db_name}")
        
        await admin_conn.close()
        
        # Connect to test database and set up extensions
        test_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=test_user,
            password=test_password,
            database=test_db_name
        )
        
        # Install required extensions
        await test_conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        await test_conn.execute("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\"")
        await test_conn.execute("CREATE EXTENSION IF NOT EXISTS \"btree_gin\"")
        print("🔧 Installed PostgreSQL extensions")
        
        await test_conn.close()
        
        print("✅ Test database setup completed successfully!")
        print(f"📝 Connection string: postgresql+asyncpg://{test_user}:{test_password}@{host}:{port}/{test_db_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup test database: {e}")
        return False


async def cleanup_test_database():
    """Clean up test database and user."""
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    admin_user = os.getenv("DB_ADMIN_USER", "postgres")
    admin_password = os.getenv("DB_ADMIN_PASSWORD", "postgres")
    
    test_db_name = "test_dotmac_platform"
    test_user = "test_user"
    
    print("🧹 Cleaning up test database...")
    
    try:
        admin_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            database="postgres"
        )
        
        # Terminate active connections to test database
        await admin_conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{test_db_name}'
            AND pid <> pg_backend_pid()
        """)
        
        # Drop test database and user
        await admin_conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
        await admin_conn.execute(f"DROP USER IF EXISTS {test_user}")
        
        await admin_conn.close()
        
        print("✅ Test database cleanup completed!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to cleanup test database: {e}")
        return False


def print_usage():
    """Print usage instructions."""
    print("""
Test Database Setup Script

Usage:
    python scripts/setup_test_db.py [command]

Commands:
    setup     - Create and configure test database (default)
    cleanup   - Remove test database and user
    help      - Show this help message

Environment Variables:
    DB_HOST           - PostgreSQL host (default: localhost)
    DB_PORT           - PostgreSQL port (default: 5432)  
    DB_ADMIN_USER     - Admin username (default: postgres)
    DB_ADMIN_PASSWORD - Admin password (default: postgres)

Examples:
    # Setup test database
    python scripts/setup_test_db.py setup
    
    # Cleanup test database
    python scripts/setup_test_db.py cleanup
    
    # With custom credentials
    DB_ADMIN_PASSWORD=mypassword python scripts/setup_test_db.py setup
""")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "setup"
    
    if command == "help":
        print_usage()
        return
    elif command == "setup":
        success = await create_test_database()
    elif command == "cleanup":
        success = await cleanup_test_database()
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())