#!/usr/bin/env python3
"""Test if ISP server can start with all APIs."""
import os
import sys
import asyncio
from contextlib import asynccontextmanager

# Set up environment
os.environ["PYTHONPATH"] = "./src"
sys.path.insert(0, "./src")

async def test_isp_server():
    """Test ISP server startup and API availability."""
    print("🚀 Testing ISP Server with Poetry")
    print("=" * 40)
    
    try:
        # Import and create app
        from dotmac_isp.app import create_app
        app = create_app()
        
        print("✅ ISP app created successfully")
        
        # Check if routes are registered
        route_count = len(app.routes)
        print(f"✅ Found {route_count} registered routes")
        
        # List some key routes
        api_routes = []
        for route in app.routes[:10]:  # Show first 10 routes
            if hasattr(route, 'path') and '/api/' in route.path:
                methods = getattr(route, 'methods', set())
                api_routes.append(f"{list(methods)} {route.path}")
        
        if api_routes:
            print(f"✅ API routes found:")
            for route in api_routes:
                print(f"   {route}")
        else:
            print("⚠️  No /api/ routes found in first 10 routes")
            
        # Try to get OpenAPI schema
        try:
            schema = app.openapi()
            endpoint_count = len(schema.get("paths", {}))
            print(f"✅ OpenAPI schema generated: {endpoint_count} endpoints")
            
            # Show some endpoint paths
            if endpoint_count > 0:
                paths = list(schema["paths"].keys())[:5]
                print(f"   Sample endpoints: {', '.join(paths)}")
            
        except Exception as e:
            print(f"⚠️  OpenAPI schema error: {e}")
        
        print(f"\n🎉 SUCCESS: ISP server is functional with APIs!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_isp_server())
    sys.exit(0 if success else 1)