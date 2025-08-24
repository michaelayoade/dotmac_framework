#!/usr/bin/env python3
"""
Quick start script for 2-VPS demo.
Starts the Management Platform with all required services.
"""

import os
import sys
import asyncio
import subprocess
import time
from pathlib import Path

def print_banner():
    """Print demo banner."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     🚀 DotMac Management Platform                           ║
║                           2-VPS Demo Setup                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

This script will start the Management Platform for your 2-VPS demo.

VPS 1 (Management Platform): localhost:8000
VPS 2 (ISP Framework):       Your target server IP

Dashboard: http://localhost:8000/dashboard
API Docs:  http://localhost:8000/docs
Health:    http://localhost:8000/health

""")

def check_dependencies():
    """Check if required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "sqlalchemy",
        "asyncpg",
        "redis",
        "paramiko",
        "asyncssh",
        "jinja2"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n🚨 Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: poetry install")
        return False
    
    print("✅ All dependencies available\n")
    return True

def setup_environment():
    """Setup environment variables."""
    print("🔧 Setting up environment...")
    
    env_vars = {
        "ENVIRONMENT": "development",
        "DEBUG": "false",
        "LOG_LEVEL": "INFO",
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/mgmt_platform_demo",
        "REDIS_URL": "redis://localhost:6379/0",
        "SECRET_KEY": "demo-secret-key-change-in-production",
        "JWT_SECRET_KEY": "demo-jwt-secret-change-in-production",
        "CORS_ORIGINS": '["http://localhost:3000", "http://localhost:8000"]',
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"  ✅ {key}")
    
    print("✅ Environment configured\n")

def check_services():
    """Check if required services are running."""
    print("🔍 Checking required services...")
    
    services_ok = True
    
    # Check PostgreSQL
    try:
        import asyncpg
        print("  ✅ PostgreSQL client available")
        print("  💡 Make sure PostgreSQL is running on localhost:5432")
    except ImportError:
        print("  ❌ PostgreSQL client not available")
        services_ok = False
    
    # Check Redis (optional for demo)
    try:
        import redis
        print("  ✅ Redis client available")
        print("  💡 Make sure Redis is running on localhost:6379 (optional)")
    except ImportError:
        print("  ⚠️ Redis client not available (optional)")
    
    if not services_ok:
        print("\n🚨 Some required services are missing")
        return False
    
    print("✅ Service dependencies available\n")
    return True

def start_management_platform():
    """Start the Management Platform."""
    print("🚀 Starting DotMac Management Platform...")
    
    # Change to management platform directory
    app_dir = Path(__file__).parent
    os.chdir(app_dir)
    
    # Start with uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--log-level", "info"
    ]
    
    print(f"Command: {' '.join(cmd)}")
    print("\n" + "="*80)
    print("🎉 Management Platform starting...")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("📚 API Docs: http://localhost:8000/docs") 
    print("🔍 Health Check: http://localhost:8000/health")
    print("="*80 + "\n")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Management Platform...")
        print("Thank you for trying the DotMac demo!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to start Management Platform: {e}")
        sys.exit(1)

def print_demo_instructions():
    """Print demo instructions."""
    print("""
📋 2-VPS DEMO INSTRUCTIONS:

1. 🖥️  VPS 1 (Management Platform) - This server
   - Management Platform is running on: http://localhost:8000
   - Dashboard available at: http://localhost:8000/dashboard

2. 🖥️  VPS 2 (ISP Framework Target) - Your second server
   - Make sure you have SSH access to your second VPS
   - Ensure Docker is installed (or will be auto-installed)
   - Have SSH key or password authentication ready

3. 🚀 DEMO WORKFLOW:
   a) Open dashboard: http://localhost:8000/dashboard
   b) Fill in tenant creation form:
      - Company Name: Your ISP company name
      - Target Server IP: IP address of VPS 2
      - SSH Username: ubuntu (or your SSH user)
      - SSH Private Key: Path to your SSH private key
   c) Click "Deploy ISP Framework"
   d) Watch real-time deployment logs
   e) Access deployed ISP Framework on VPS 2

4. 📊 MONITORING:
   - View tenant status in dashboard
   - Monitor system metrics
   - Check deployment logs

Ready to start your demo? Press Enter to continue...
""")
    
    input()

def main():
    """Main demo startup function."""
    print_banner()
    
    # Pre-flight checks
    if not check_dependencies():
        print("❌ Dependency check failed. Please install required packages.")
        sys.exit(1)
    
    setup_environment()
    
    if not check_services():
        print("⚠️ Some services may not be available. Demo may have limited functionality.")
    
    print_demo_instructions()
    
    # Start the platform
    start_management_platform()

if __name__ == "__main__":
    main()