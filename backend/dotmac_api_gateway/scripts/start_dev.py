#!/usr/bin/env python3
"""
Development startup script for DotMac API Gateway.
"""

import sys
from pathlib import Path

# Add the project to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotmac_api_gateway.core.config import GatewayConfig
from dotmac_api_gateway.runtime import APIGatewayApp


def main():
    """Start the API Gateway in development mode."""
    print("Starting DotMac API Gateway (Development Mode)")
    print("=" * 50)

    # Create development configuration
    config = GatewayConfig(
        environment="development",
        debug=True,
        tenant_id="dev-tenant"
    )

    # Create and run the application
    gateway = APIGatewayApp(config)
    gateway.create_app()

    print(f"API Gateway starting on http://{config.server.host}:{config.server.port}")
    print("Interactive API docs available at: http://localhost:8000/docs")
    print("Health check endpoint: http://localhost:8000/health")
    print("Metrics endpoint: http://localhost:8000/metrics")
    print("\nPress Ctrl+C to stop the server")

    try:
        gateway.run(
            host=config.server.host,
            port=config.server.port,
            reload=True,
            log_level="debug"
        )
    except KeyboardInterrupt:
        print("\nShutting down API Gateway...")


if __name__ == "__main__":
    main()
