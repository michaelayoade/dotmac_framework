"""
DotMac API Aggregator - Unified API composition for frontend applications
Combines all microservices into a single, coherent API for frontend consumption
"""

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import httpx
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ServiceEndpoint(BaseModel):
    """Service endpoint configuration"""
    name: str
    url: str
    health_endpoint: str = "/health"
    timeout: int = 30


class APIAggregatorConfig:
    """Configuration for API Aggregator"""
    
    # Service endpoints
    SERVICES = {
        "platform": ServiceEndpoint(
            name="Platform Service",
            url="http://dotmac-platform:8000",
            health_endpoint="/health"
        ),
        "networking": ServiceEndpoint(
            name="Enhanced Networking Service", 
            url="http://dotmac-networking-enhanced:8000",
            health_endpoint="/health"
        ),
        "identity": ServiceEndpoint(
            name="Identity Service",
            url="http://dotmac-identity:8000", 
            health_endpoint="/health"
        ),
        "billing": ServiceEndpoint(
            name="Billing Service",
            url="http://dotmac-billing:8000",
            health_endpoint="/health"
        ),
        "analytics": ServiceEndpoint(
            name="Analytics Service",
            url="http://dotmac-analytics:8000",
            health_endpoint="/health"
        ),
        "services": ServiceEndpoint(
            name="Services Management",
            url="http://dotmac-services:8000",
            health_endpoint="/health"
        ),
        "core_events": ServiceEndpoint(
            name="Core Events Service",
            url="http://dotmac-core-events:8000",
            health_endpoint="/health"
        )
    }


class APIAggregator:
    """Main API Aggregator class"""
    
    def __init__(self):
        self.services = APIAggregatorConfig.SERVICES
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def proxy_request(self, service_name: str, path: str, method: str = "GET", 
                          data: Any = None, params: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """Proxy request to underlying service"""
        
        if service_name not in self.services:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        service = self.services[service_name]
        url = f"{service.url}{path}"
        
        try:
            if method.upper() == "GET":
                response = await self.http_client.get(url, params=params, headers=headers)
            elif method.upper() == "POST":
                response = await self.http_client.post(url, json=data, params=params, headers=headers)
            elif method.upper() == "PUT":
                response = await self.http_client.put(url, json=data, params=params, headers=headers)
            elif method.upper() == "DELETE":
                response = await self.http_client.delete(url, params=params, headers=headers)
            else:
                raise HTTPException(status_code=405, detail=f"Method {method} not supported")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail=f"Service {service_name} timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Service error: {e.response.text}")
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of individual service"""
        
        if service_name not in self.services:
            return {"status": "unknown", "error": "Service not found"}
        
        service = self.services[service_name]
        
        try:
            response = await self.http_client.get(f"{service.url}{service.health_endpoint}", timeout=5.0)
            response.raise_for_status()
            health_data = response.json()
            
            return {
                "status": "healthy",
                "service": service.name,
                "url": service.url,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "details": health_data
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": service.name,
                "url": service.url,
                "error": str(e)
            }
    
    async def check_all_services_health(self) -> Dict[str, Any]:
        """Check health of all services"""
        
        health_checks = await asyncio.gather(
            *[self.check_service_health(name) for name in self.services.keys()],
            return_exceptions=True
        )
        
        service_health = {}
        healthy_count = 0
        
        for i, (service_name, health) in enumerate(zip(self.services.keys(), health_checks)):
            if isinstance(health, Exception):
                service_health[service_name] = {
                    "status": "error", 
                    "error": str(health)
                }
            else:
                service_health[service_name] = health
                if health["status"] == "healthy":
                    healthy_count += 1
        
        overall_status = "healthy" if healthy_count == len(self.services) else "degraded" if healthy_count > 0 else "unhealthy"
        
        return {
            "overall_status": overall_status,
            "healthy_services": healthy_count,
            "total_services": len(self.services),
            "services": service_health,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()


# Global aggregator instance
aggregator = APIAggregator()


# FastAPI app
app = FastAPI(
    title="DotMac Unified API",
    description="Unified API aggregating all DotMac microservices for frontend consumption",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================
# HEALTH & STATUS ENDPOINTS
# ================================

@app.get("/health", summary="Aggregator Health Check")
async def health_check():
    """Health check for the API aggregator itself"""
    return {
        "status": "healthy",
        "service": "DotMac API Aggregator", 
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/services", summary="All Services Health Check")
async def services_health_check():
    """Check health of all underlying services"""
    return await aggregator.check_all_services_health()


@app.get("/health/services/{service_name}", summary="Individual Service Health Check")
async def service_health_check(service_name: str):
    """Check health of individual service"""
    return await aggregator.check_service_health(service_name)


# ================================
# CUSTOMER MANAGEMENT APIs
# ================================

@app.get("/api/v1/customers", summary="List Customers", tags=["Customer Management"])
async def list_customers(limit: int = 100, offset: int = 0):
    """List customers from identity service"""
    return await aggregator.proxy_request("identity", f"/customers?limit={limit}&offset={offset}")


@app.post("/api/v1/customers", summary="Create Customer", tags=["Customer Management"])
async def create_customer(customer_data: dict):
    """Create new customer"""
    return await aggregator.proxy_request("identity", "/customers", method="POST", data=customer_data)


@app.get("/api/v1/customers/{customer_id}", summary="Get Customer", tags=["Customer Management"])
async def get_customer(customer_id: str):
    """Get customer details"""
    return await aggregator.proxy_request("identity", f"/customers/{customer_id}")


@app.put("/api/v1/customers/{customer_id}", summary="Update Customer", tags=["Customer Management"])
async def update_customer(customer_id: str, customer_data: dict):
    """Update customer information"""
    return await aggregator.proxy_request("identity", f"/customers/{customer_id}", method="PUT", data=customer_data)


# ================================
# BILLING & SUBSCRIPTION APIs
# ================================

@app.get("/api/v1/billing/accounts", summary="List Billing Accounts", tags=["Billing"])
async def list_billing_accounts():
    """List billing accounts"""
    return await aggregator.proxy_request("billing", "/accounts")


@app.get("/api/v1/billing/accounts/{account_id}/invoices", summary="Get Account Invoices", tags=["Billing"])
async def get_account_invoices(account_id: str):
    """Get invoices for billing account"""
    return await aggregator.proxy_request("billing", f"/accounts/{account_id}/invoices")


@app.post("/api/v1/billing/subscriptions", summary="Create Subscription", tags=["Billing"])
async def create_subscription(subscription_data: dict):
    """Create new service subscription"""
    return await aggregator.proxy_request("billing", "/subscriptions", method="POST", data=subscription_data)


@app.get("/api/v1/billing/subscriptions/{subscription_id}", summary="Get Subscription", tags=["Billing"])
async def get_subscription(subscription_id: str):
    """Get subscription details"""
    return await aggregator.proxy_request("billing", f"/subscriptions/{subscription_id}")


# ================================
# NETWORK MANAGEMENT APIs
# ================================

@app.get("/api/v1/network/status", summary="Network Overview", tags=["Network Management"])
async def get_network_status():
    """Get overall network status and health"""
    try:
        # Get data from multiple services
        network_health = await aggregator.proxy_request("networking", "/integrated/network-health-dashboard")
        voltha_status = await aggregator.proxy_request("networking", "/voltha/network-status")
        
        return {
            "overall_health": network_health,
            "voltha_status": voltha_status,
            "retrieved_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "error": "Failed to retrieve network status",
            "details": str(e),
            "retrieved_at": datetime.utcnow().isoformat()
        }


@app.get("/api/v1/network/topology/analysis", summary="Network Topology Analysis", tags=["Network Management"])
async def get_network_topology_analysis():
    """Get comprehensive network topology analysis"""
    return await aggregator.proxy_request("networking", "/topology/analysis")


@app.get("/api/v1/network/devices", summary="List Network Devices", tags=["Network Management"])
async def list_network_devices():
    """List all network devices"""
    return await aggregator.proxy_request("networking", "/topology/devices")


@app.post("/api/v1/network/devices", summary="Add Network Device", tags=["Network Management"])
async def add_network_device(device_data: dict):
    """Add new network device to topology"""
    return await aggregator.proxy_request("networking", "/topology/add-device", method="POST", data=device_data)


# ================================
# SERVICE PROVISIONING APIs  
# ================================

@app.post("/api/v1/services/provision", summary="Provision Customer Service", tags=["Service Provisioning"])
async def provision_customer_service(provisioning_data: dict):
    """Provision service for customer using VOLTHA"""
    return await aggregator.proxy_request("networking", "/voltha/provision-subscriber", method="POST", data=provisioning_data)


@app.post("/api/v1/services/suspend", summary="Suspend Customer Service", tags=["Service Provisioning"])
async def suspend_customer_service(suspension_data: dict):
    """Suspend customer service"""
    return await aggregator.proxy_request("networking", "/voltha/suspend-service", method="POST", data=suspension_data)


@app.post("/api/v1/services/restore", summary="Restore Customer Service", tags=["Service Provisioning"])
async def restore_customer_service(restoration_data: dict):
    """Restore customer service"""
    return await aggregator.proxy_request("networking", "/voltha/restore-service", method="POST", data=restoration_data)


@app.get("/api/v1/services/subscriber-status/{customer_id}/{onu_device_id}", summary="Get Subscriber Status", tags=["Service Provisioning"])
async def get_subscriber_status(customer_id: str, onu_device_id: str):
    """Get real-time subscriber service status"""
    return await aggregator.proxy_request("networking", f"/voltha/subscriber-status/{customer_id}/{onu_device_id}")


# ================================
# DEVICE AUTOMATION APIs
# ================================

@app.post("/api/v1/automation/deploy-config", summary="Deploy Device Configuration", tags=["Device Automation"])
async def deploy_device_configuration(deployment_data: dict):
    """Deploy configuration to multiple devices via SSH"""
    return await aggregator.proxy_request("networking", "/ssh/deploy-configuration", method="POST", data=deployment_data)


@app.post("/api/v1/automation/discover-devices", summary="Discover Network Devices", tags=["Device Automation"])
async def discover_network_devices(discovery_data: dict):
    """Discover devices via SSH scanning"""
    return await aggregator.proxy_request("networking", "/ssh/network-discovery", method="POST", data=discovery_data)


@app.post("/api/v1/automation/firmware-upgrade", summary="Mass Firmware Upgrade", tags=["Device Automation"])
async def mass_firmware_upgrade(upgrade_data: dict):
    """Perform mass firmware upgrade"""
    return await aggregator.proxy_request("networking", "/ssh/firmware-upgrade", method="POST", data=upgrade_data)


@app.get("/api/v1/automation/execution-stats", summary="Automation Statistics", tags=["Device Automation"])
async def get_automation_stats():
    """Get SSH automation execution statistics"""
    return await aggregator.proxy_request("networking", "/ssh/execution-stats")


# ================================
# ANALYTICS & REPORTING APIs
# ================================

@app.get("/api/v1/analytics/dashboard", summary="Analytics Dashboard", tags=["Analytics"])
async def get_analytics_dashboard():
    """Get analytics dashboard data"""
    return await aggregator.proxy_request("analytics", "/dashboard")


@app.get("/api/v1/analytics/network-performance", summary="Network Performance Metrics", tags=["Analytics"])
async def get_network_performance():
    """Get network performance analytics"""
    return await aggregator.proxy_request("analytics", "/network-performance")


@app.get("/api/v1/analytics/customer-metrics", summary="Customer Metrics", tags=["Analytics"])
async def get_customer_metrics():
    """Get customer analytics and metrics"""
    return await aggregator.proxy_request("analytics", "/customer-metrics")


# ================================
# CAPTIVE PORTAL & WIFI APIs
# ================================

@app.get("/api/v1/wifi/hotspots", summary="List WiFi Hotspots", tags=["WiFi Management"])
async def list_wifi_hotspots():
    """List all WiFi hotspots"""
    return await aggregator.proxy_request("networking", "/captive-portal/hotspots")


@app.post("/api/v1/wifi/hotspots", summary="Create WiFi Hotspot", tags=["WiFi Management"])
async def create_wifi_hotspot(hotspot_data: dict):
    """Create new WiFi hotspot with captive portal"""
    return await aggregator.proxy_request("networking", "/captive-portal/create-hotspot", method="POST", data=hotspot_data)


@app.post("/api/v1/wifi/authenticate", summary="Authenticate WiFi User", tags=["WiFi Management"])
async def authenticate_wifi_user(auth_data: dict):
    """Authenticate user for WiFi hotspot access"""
    return await aggregator.proxy_request("networking", "/captive-portal/authenticate-user", method="POST", data=auth_data)


# ================================
# INTEGRATED WORKFLOWS APIs
# ================================

@app.post("/api/v1/workflows/customer-onboarding", summary="Automated Customer Onboarding", tags=["Integrated Workflows"])
async def automated_customer_onboarding(onboarding_data: dict):
    """Complete automated customer onboarding workflow"""
    return await aggregator.proxy_request("networking", "/integrated/customer-onboarding", method="POST", data=onboarding_data)


@app.get("/api/v1/workflows/network-health", summary="Network Health Dashboard", tags=["Integrated Workflows"])
async def network_health_dashboard():
    """Comprehensive network health dashboard"""
    return await aggregator.proxy_request("networking", "/integrated/network-health-dashboard")


# ================================
# OPENAPI SCHEMA AGGREGATION
# ================================

@app.get("/api/v1/schemas", summary="Available Service Schemas", tags=["API Documentation"])
async def get_available_schemas():
    """Get list of available service OpenAPI schemas"""
    schemas = {}
    
    for service_name, service in aggregator.services.items():
        try:
            schema = await aggregator.proxy_request(service_name, "/openapi.json")
            schemas[service_name] = {
                "title": schema.get("info", {}).get("title", service.name),
                "version": schema.get("info", {}).get("version", "unknown"),
                "url": f"{service.url}/docs",
                "openapi_url": f"{service.url}/openapi.json"
            }
        except:
            schemas[service_name] = {
                "title": service.name,
                "version": "unknown",
                "status": "unavailable"
            }
    
    return {
        "available_schemas": schemas,
        "aggregated_docs": "/docs",
        "generated_at": datetime.utcnow().isoformat()
    }


# ================================
# STARTUP & SHUTDOWN EVENTS
# ================================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("DotMac API Aggregator starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    await aggregator.cleanup()
    logger.info("DotMac API Aggregator shutdown complete")


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    uvicorn.run(
        "dotmac_api_gateway.aggregator:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )