#!/usr/bin/env python3
"""
DotMac Platform - Unified Service Runner with SignOz Observability
Starts all microservices with comprehensive telemetry
"""

import os
import sys
import asyncio
import signal
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Import SignOz observability
from dotmac_sdk_core.observability_signoz import init_signoz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class DotMacServiceManager:
    """Manages all DotMac microservices with SignOz observability."""
    
    def __init__(self):
        self.services = {}
        self.telemetry = {}
        self.running = False
        
        # SignOz configuration from environment
        self.signoz_endpoint = os.getenv("SIGNOZ_ENDPOINT", "localhost:4317")
        self.environment = os.getenv("ENVIRONMENT", "development")
        
    async def start_service(self, service_name: str, port: int):
        """Start a single microservice with SignOz instrumentation."""
        try:
            # Initialize SignOz telemetry for service
            telemetry = init_signoz(
                service_name=f"dotmac-{service_name}",
                service_version="1.0.0",
                environment=self.environment,
                signoz_endpoint=self.signoz_endpoint,
                custom_attributes={
                    "service.port": port,
                    "service.type": "microservice",
                    "platform.name": "dotmac",
                    "platform.version": "1.0.0"
                }
            )
            
            self.telemetry[service_name] = telemetry
            
            # Import service module dynamically
            if service_name == "api_gateway":
                from dotmac_api_gateway import create_app
            elif service_name == "identity":
                from dotmac_identity import create_app
            elif service_name == "billing":
                from dotmac_billing import create_app
            elif service_name == "services":
                from dotmac_services import create_app
            elif service_name == "networking":
                from dotmac_networking import create_app
            elif service_name == "analytics":
                from dotmac_analytics import create_app
            elif service_name == "core_ops":
                from dotmac_core_ops import create_app
            elif service_name == "core_events":
                from dotmac_core_events import create_app
            elif service_name == "platform":
                from dotmac_platform import create_app
            elif service_name == "devtools":
                from dotmac_devtools import create_app
            else:
                raise ValueError(f"Unknown service: {service_name}")
            
            # Create FastAPI app
            app = create_app()
            
            # Instrument with SignOz
            telemetry.instrument_fastapi(app)
            telemetry.instrument_sqlalchemy(app.state.db_engine if hasattr(app.state, 'db_engine') else None)
            telemetry.instrument_redis(app.state.redis if hasattr(app.state, 'redis') else None)
            telemetry.instrument_httpx()
            telemetry.instrument_asyncio()
            
            # Start service with uvicorn
            import uvicorn
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=port,
                log_level="info" if self.environment == "production" else "debug",
                access_log=False,  # Use SignOz for access logs
                use_colors=True,
                reload=self.environment == "development",
                workers=1  # Single worker per service for clarity
            )
            
            server = uvicorn.Server(config)
            
            # Record service start event
            telemetry.record_business_event(
                event_type="service_started",
                tenant_id="system",
                attributes={
                    "service": service_name,
                    "port": port,
                    "environment": self.environment
                }
            )
            
            self.services[service_name] = server
            
            logger.info(f"✓ Started {service_name} on port {port} with SignOz telemetry")
            
            # Run server
            await server.serve()
            
        except Exception as e:
            logger.error(f"✗ Failed to start {service_name}: {e}")
            if service_name in self.telemetry:
                self.telemetry[service_name].record_business_event(
                    event_type="service_start_failed",
                    tenant_id="system",
                    attributes={
                        "service": service_name,
                        "error": str(e)
                    }
                )
            raise
    
    async def start_all_services(self):
        """Start all DotMac microservices with SignOz."""
        logger.info("🚀 Starting DotMac Platform with SignOz Observability")
        logger.info(f"📊 SignOz Endpoint: {self.signoz_endpoint}")
        logger.info(f"🌍 Environment: {self.environment}")
        
        # Service configuration
        services_config = {
            "api_gateway": 8000,
            "identity": 8001,
            "billing": 8002,
            "services": 8003,
            "networking": 8004,
            "analytics": 8005,
            "core_ops": 8006,
            "core_events": 8007,
            "platform": 8008,
            "devtools": 8009,
        }
        
        # Start services concurrently
        tasks = []
        for service_name, port in services_config.items():
            task = asyncio.create_task(self.start_service(service_name, port))
            tasks.append(task)
        
        self.running = True
        
        try:
            # Wait for all services
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error during service startup: {e}")
            await self.shutdown()
    
    async def health_check(self):
        """Periodic health check with SignOz metrics."""
        while self.running:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            for service_name, server in self.services.items():
                if service_name in self.telemetry:
                    telemetry = self.telemetry[service_name]
                    
                    # Check if service is running
                    is_healthy = server.started if hasattr(server, 'started') else False
                    
                    # Record health metric
                    with telemetry.trace_operation("health_check"):
                        telemetry.record_business_event(
                            event_type="health_check",
                            tenant_id="system",
                            attributes={
                                "service": service_name,
                                "healthy": is_healthy
                            }
                        )
    
    async def shutdown(self):
        """Gracefully shutdown all services."""
        logger.info("📉 Shutting down DotMac Platform...")
        self.running = False
        
        # Shutdown services
        for service_name, server in self.services.items():
            try:
                # Record shutdown event
                if service_name in self.telemetry:
                    self.telemetry[service_name].record_business_event(
                        event_type="service_stopping",
                        tenant_id="system",
                        attributes={"service": service_name}
                    )
                
                # Shutdown server
                await server.shutdown()
                
                # Shutdown telemetry
                if service_name in self.telemetry:
                    self.telemetry[service_name].shutdown()
                
                logger.info(f"✓ Stopped {service_name}")
                
            except Exception as e:
                logger.error(f"Error shutting down {service_name}: {e}")
        
        logger.info("👋 DotMac Platform shutdown complete")


async def main():
    """Main entry point."""
    manager = DotMacServiceManager()
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        asyncio.create_task(manager.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start health checker
        health_task = asyncio.create_task(manager.health_check())
        
        # Start all services
        await manager.start_all_services()
        
        # Wait for health checker
        await health_task
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    # Verify SignOz is configured
    if not os.getenv("SIGNOZ_ENDPOINT"):
        logger.warning("SIGNOZ_ENDPOINT not set, using default localhost:4317")
    
    # Print startup banner
    print("""
    ╔════════════════════════════════════════════════╗
    ║     DotMac Platform with SignOz Observability  ║
    ║                                                ║
    ║     Metrics ✓  Traces ✓  Logs ✓  Unified ✓   ║
    ╚════════════════════════════════════════════════╝
    """)
    
    # Run the platform
    asyncio.run(main())