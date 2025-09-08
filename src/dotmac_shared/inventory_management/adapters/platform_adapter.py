"""
Platform adapters for integrating inventory management with ISP Framework and Management Platform.
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import ItemType, MovementType, WarehouseType
from ..core.schemas import (
    ItemCreate,
    ItemResponse,
    StockMovementResponse,
    WarehouseCreate,
    WarehouseResponse,
)
from ..services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class BaseInventoryAdapter(ABC):
    """Base adapter for platform-specific inventory integration."""

    def __init__(self, inventory_service: InventoryService):
        self.inventory_service = inventory_service

    @abstractmethod
    async def get_vendor_info(self, tenant_id: str, vendor_id: str) -> dict[str, Any]:
        """Get vendor information from the platform."""
        pass

    @abstractmethod
    async def send_inventory_notification(
        self, notification_type: str, recipient: str, data: dict[str, Any], **kwargs
    ) -> bool:
        """Send inventory-related notification."""
        pass

    @abstractmethod
    async def create_inventory_event(self, event_type: str, data: dict[str, Any]) -> bool:
        """Create inventory event in platform system."""
        pass


class ISPInventoryAdapter(BaseInventoryAdapter):
    """Adapter for ISP Framework inventory operations."""

    def __init__(self, inventory_service: InventoryService, isp_client=None):
        super().__init__(inventory_service)
        self.isp_client = isp_client

    async def get_vendor_info(self, tenant_id: str, vendor_id: str) -> dict[str, Any]:
        """Get vendor info from ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.get_vendor(tenant_id, vendor_id)
            return {"id": vendor_id, "name": f"Vendor {vendor_id}"}
        except Exception as e:
            logger.error(f"Error getting vendor info: {e}")
            return {"id": vendor_id, "name": f"Vendor {vendor_id}"}

    async def send_inventory_notification(
        self, notification_type: str, recipient: str, data: dict[str, Any], **kwargs
    ) -> bool:
        """Send notification via ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.send_notification(notification_type, recipient, data)
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def create_inventory_event(self, event_type: str, data: dict[str, Any]) -> bool:
        """Create inventory event in ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.create_event(event_type, data)
            return True
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False

    # ISP-specific inventory operations
    async def setup_isp_equipment_catalog(
        self, db: AsyncSession, tenant_id: str, created_by: Optional[str] = None
    ) -> list[ItemResponse]:
        """Setup standard ISP equipment catalog."""

        isp_equipment = [
            # Network Equipment
            {
                "name": "Ubiquiti UniFi Dream Machine",
                "item_type": ItemType.NETWORK_EQUIPMENT,
                "category": "router",
                "manufacturer": "Ubiquiti",
                "model": "UDM",
                "technical_specs": {
                    "ports": "8x Gigabit Ethernet, 1x WAN",
                    "wifi": "802.11ac Wave 2",
                    "throughput": "3.5 Gbps",
                    "poe_budget": "60W",
                },
                "standard_cost": Decimal("379.00"),
                "list_price": Decimal("449.00"),
                "reorder_point": 5,
                "reorder_quantity": 10,
            },
            {
                "name": "Ubiquiti UniFi Access Point AC Pro",
                "item_type": ItemType.NETWORK_EQUIPMENT,
                "category": "access_point",
                "manufacturer": "Ubiquiti",
                "model": "UAP-AC-PRO",
                "technical_specs": {
                    "wifi_standard": "802.11ac",
                    "max_speed": "1.75 Gbps",
                    "range": "122m",
                    "power_consumption": "9W",
                },
                "standard_cost": Decimal("149.00"),
                "list_price": Decimal("179.00"),
                "reorder_point": 10,
                "reorder_quantity": 20,
            },
            # Customer Premises Equipment
            {
                "name": "TP-Link Archer C7 Router",
                "item_type": ItemType.CUSTOMER_PREMISES_EQUIPMENT,
                "category": "cpe_router",
                "manufacturer": "TP-Link",
                "model": "Archer C7",
                "technical_specs": {
                    "wifi_standard": "802.11ac",
                    "max_speed": "1.75 Gbps",
                    "ports": "4x Gigabit Ethernet",
                    "antennas": "3x External",
                },
                "standard_cost": Decimal("59.00"),
                "list_price": Decimal("79.00"),
                "reorder_point": 15,
                "reorder_quantity": 30,
            },
            # Cables and Consumables
            {
                "name": "Cat6 Ethernet Cable - 100ft",
                "item_type": ItemType.CONSUMABLE,
                "category": "cable",
                "manufacturer": "Generic",
                "model": "CAT6-100FT",
                "technical_specs": {
                    "category": "Cat6",
                    "length": "100 feet",
                    "connector": "RJ45",
                    "color": "Blue",
                },
                "standard_cost": Decimal("25.00"),
                "list_price": Decimal("35.00"),
                "reorder_point": 50,
                "reorder_quantity": 100,
            },
            # Tools
            {
                "name": "Network Cable Tester",
                "item_type": ItemType.TOOL,
                "category": "testing_equipment",
                "manufacturer": "Fluke",
                "model": "MicroScanner2",
                "technical_specs": {
                    "tests": "Continuity, wiremap, tone generation",
                    "cable_types": "RJ45, RJ11, Coax",
                    "battery_life": "50 hours",
                },
                "standard_cost": Decimal("299.00"),
                "list_price": Decimal("399.00"),
                "reorder_point": 2,
                "reorder_quantity": 3,
            },
        ]

        created_items = []
        for equipment_data in isp_equipment:
            try:
                # Add ISP-specific metadata
                equipment_data["platform_data"] = {
                    "source": "isp_framework",
                    "equipment_type": equipment_data["category"],
                    "deployment_ready": True,
                }

                # Set tracking preferences based on item type
                if equipment_data["item_type"] in [
                    ItemType.NETWORK_EQUIPMENT,
                    ItemType.CUSTOMER_PREMISES_EQUIPMENT,
                ]:
                    equipment_data["track_serial_numbers"] = True
                    equipment_data["maintenance_required"] = True

                item_create = ItemCreate(**equipment_data)

                item = await self.inventory_service.inventory_manager.create_item(
                    db, tenant_id, item_create, created_by
                )
                created_items.append(ItemResponse.model_validate(item))

            except Exception as e:
                logger.warning(f"Failed to create equipment item {equipment_data['name']}: {e}")

        logger.info(f"Created {len(created_items)} ISP equipment items")
        return created_items

    async def setup_isp_warehouses(
        self,
        db: AsyncSession,
        tenant_id: str,
        locations: Optional[list[dict[str, Any]]] = None,
        created_by: Optional[str] = None,
    ) -> list[WarehouseResponse]:
        """Setup ISP-specific warehouse structure."""

        if not locations:
            locations = [
                {
                    "city": "Main Office",
                    "address": "123 Business Ave",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                }
            ]

        isp_warehouses = []

        for i, location in enumerate(locations):
            # Main warehouse
            isp_warehouses.append(
                {
                    "warehouse_code": f"ISP-MAIN-{i+1:02d}",
                    "name": f'Main Warehouse - {location["city"]}',
                    "warehouse_type": WarehouseType.MAIN,
                    "description": f'Primary equipment storage - {location["city"]}',
                    "address_line1": location.get("address"),
                    "city": location["city"],
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "barcode_scanning": True,
                    "wms_integrated": False,
                    "security_level": "high",
                }
            )

            # Field warehouse
            isp_warehouses.append(
                {
                    "warehouse_code": f"ISP-FIELD-{i+1:02d}",
                    "name": f'Field Operations - {location["city"]}',
                    "warehouse_type": WarehouseType.FIELD,
                    "description": f'Field technician equipment - {location["city"]}',
                    "address_line1": location.get("address"),
                    "city": location["city"],
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "barcode_scanning": True,
                    "security_level": "standard",
                }
            )

        created_warehouses = []
        for warehouse_data in isp_warehouses:
            try:
                # Add ISP-specific metadata
                warehouse_data["platform_data"] = {
                    "source": "isp_framework",
                    "service_area": warehouse_data.get("city", "Unknown"),
                }

                warehouse_create = WarehouseCreate(**warehouse_data)

                warehouse = await self.inventory_service.inventory_manager.create_warehouse(
                    db, tenant_id, warehouse_create, created_by
                )
                created_warehouses.append(WarehouseResponse.model_validate(warehouse))

            except Exception as e:
                logger.warning(f"Failed to create warehouse {warehouse_data['name']}: {e}")

        logger.info(f"Created {len(created_warehouses)} ISP warehouses")
        return created_warehouses

    async def process_customer_installation(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        installation_items: list[dict[str, Any]],
        technician_id: str,
        project_id: Optional[str] = None,
    ) -> list[StockMovementResponse]:
        """Process equipment allocation for customer installation."""

        movements = []

        for item_data in installation_items:
            item_code = item_data["item_code"]
            quantity = item_data["quantity"]
            warehouse_id = item_data.get("warehouse_id")

            # Get item
            item = await self.inventory_service.inventory_manager.get_item_by_code(db, tenant_id, item_code)
            if not item:
                logger.error(f"Item not found: {item_code}")
                continue

            # Issue equipment for installation
            movement = await self.inventory_service.issue_equipment_for_installation(
                db,
                tenant_id,
                str(item.id),
                warehouse_id,
                quantity,
                project_id,
                technician_id,
                f"Customer {customer_id}",
            )

            movements.append(movement)

            # Send notification about equipment allocation
            await self.send_inventory_notification(
                "equipment_allocated",
                technician_id,
                {
                    "item_name": item.name,
                    "quantity": quantity,
                    "customer_id": customer_id,
                    "project_id": project_id,
                },
            )

        return movements

    async def process_equipment_return(
        self,
        db: AsyncSession,
        tenant_id: str,
        return_items: list[dict[str, Any]],
        technician_id: str,
        reason: str = "Installation complete",
    ) -> list[StockMovementResponse]:
        """Process equipment return from field operations."""

        movements = []

        for item_data in return_items:
            movement = await self.inventory_service.inventory_manager.create_stock_movement(
                db,
                tenant_id,
                {
                    "item_id": item_data["item_id"],
                    "warehouse_id": item_data["warehouse_id"],
                    "movement_type": MovementType.RETURN,
                    "quantity": item_data["quantity"],
                    "reason_description": reason,
                    "serial_numbers": item_data.get("serial_numbers"),
                },
                technician_id,
            )

            movements.append(StockMovementResponse.model_validate(movement))

        return movements


class ManagementInventoryAdapter(BaseInventoryAdapter):
    """Adapter for Management Platform inventory operations."""

    def __init__(self, inventory_service: InventoryService, management_client=None):
        super().__init__(inventory_service)
        self.management_client = management_client

    async def get_vendor_info(self, tenant_id: str, vendor_id: str) -> dict[str, Any]:
        """Get vendor info from Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.get_vendor(tenant_id, vendor_id)
            return {"id": vendor_id, "name": f"Vendor {vendor_id}"}
        except Exception as e:
            logger.error(f"Error getting vendor info: {e}")
            return {"id": vendor_id, "name": f"Vendor {vendor_id}"}

    async def send_inventory_notification(
        self, notification_type: str, recipient: str, data: dict[str, Any], **kwargs
    ) -> bool:
        """Send notification via Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.send_notification(notification_type, recipient, data)
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def create_inventory_event(self, event_type: str, data: dict[str, Any]) -> bool:
        """Create inventory event in Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.create_event(event_type, data)
            return True
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return False

    # Management Platform specific operations
    async def setup_datacenter_inventory(
        self,
        db: AsyncSession,
        tenant_id: str,
        datacenter_locations: Optional[list[dict[str, Any]]] = None,
        created_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """Setup datacenter equipment inventory for Management Platform."""

        if not datacenter_locations:
            datacenter_locations = [
                {
                    "name": "Primary Datacenter",
                    "city": "Cloud Region 1",
                    "address": "Cloud Infrastructure",
                }
            ]

        # Create datacenter equipment catalog
        datacenter_equipment = [
            {
                "name": "Dell PowerEdge R740 Server",
                "item_type": ItemType.HARDWARE,
                "category": "server",
                "manufacturer": "Dell",
                "model": "PowerEdge R740",
                "technical_specs": {
                    "cpu": "2x Intel Xeon Gold 6248",
                    "ram": "128GB DDR4",
                    "storage": "2x 480GB SSD",
                    "network": "4x 1GbE",
                    "power": "750W PSU",
                },
                "standard_cost": Decimal("4500.00"),
                "reorder_point": 2,
                "reorder_quantity": 5,
            },
            {
                "name": "Cisco Catalyst 9300 Switch",
                "item_type": ItemType.NETWORK_EQUIPMENT,
                "category": "switch",
                "manufacturer": "Cisco",
                "model": "Catalyst 9300",
                "technical_specs": {
                    "ports": "24x Gigabit Ethernet",
                    "uplinks": "4x 10GbE SFP+",
                    "switching_capacity": "208 Gbps",
                    "poe_budget": "740W",
                },
                "standard_cost": Decimal("2800.00"),
                "reorder_point": 3,
                "reorder_quantity": 6,
            },
            {
                "name": "APC Smart-UPS 3000VA",
                "item_type": ItemType.HARDWARE,
                "category": "ups",
                "manufacturer": "APC",
                "model": "SMT3000",
                "technical_specs": {
                    "capacity": "3000VA / 2700W",
                    "runtime": "10 min at full load",
                    "outlets": "8x NEMA 5-15R",
                    "management": "Network card ready",
                },
                "standard_cost": Decimal("599.00"),
                "reorder_point": 5,
                "reorder_quantity": 10,
            },
        ]

        # Create items
        created_items = []
        for equipment_data in datacenter_equipment:
            try:
                equipment_data["platform_data"] = {
                    "source": "management_platform",
                    "deployment_environment": "datacenter",
                    "criticality": "high",
                }

                equipment_data["track_serial_numbers"] = True
                equipment_data["maintenance_required"] = True

                item_create = ItemCreate(**equipment_data)

                item = await self.inventory_service.inventory_manager.create_item(
                    db, tenant_id, item_create, created_by
                )
                created_items.append(ItemResponse.model_validate(item))

            except Exception as e:
                logger.warning(f"Failed to create datacenter item {equipment_data['name']}: {e}")

        # Create warehouses
        created_warehouses = []
        for location in datacenter_locations:
            try:
                warehouse_data = {
                    "warehouse_code": f'DC-{location["name"].replace(" ", "").upper()}',
                    "name": f'Datacenter - {location["name"]}',
                    "warehouse_type": WarehouseType.MAIN,
                    "description": f'Datacenter equipment storage - {location["name"]}',
                    "city": location["city"],
                    "address_line1": location.get("address"),
                    "temperature_controlled": True,
                    "humidity_controlled": True,
                    "security_level": "maximum",
                    "rfid_enabled": True,
                    "platform_data": {
                        "source": "management_platform",
                        "facility_type": "datacenter",
                    },
                }

                warehouse_create = WarehouseCreate(**warehouse_data)

                warehouse = await self.inventory_service.inventory_manager.create_warehouse(
                    db, tenant_id, warehouse_create, created_by
                )
                created_warehouses.append(WarehouseResponse.model_validate(warehouse))

            except Exception as e:
                logger.warning(f"Failed to create datacenter warehouse {location['name']}: {e}")

        return {
            "items": created_items,
            "warehouses": created_warehouses,
            "summary": {
                "items_created": len(created_items),
                "warehouses_created": len(created_warehouses),
            },
        }

    async def process_tenant_deployment_equipment(
        self,
        db: AsyncSession,
        tenant_id: str,
        deployment_config: dict[str, Any],
        allocated_by: str,
    ) -> list[StockMovementResponse]:
        """Allocate equipment for tenant deployment."""

        required_equipment = deployment_config.get("equipment_requirements", [])
        datacenter_warehouse_id = deployment_config.get("datacenter_warehouse_id")
        deployment_id = deployment_config.get("deployment_id")

        movements = []

        for equipment_req in required_equipment:
            # Find suitable equipment
            items, _ = await self.inventory_service.inventory_manager.list_items(
                db,
                tenant_id,
                {
                    "category": equipment_req["category"],
                    "manufacturer": equipment_req.get("manufacturer"),
                    "is_active": True,
                },
            )

            if not items:
                logger.warning(f"No equipment found for requirement: {equipment_req}")
                continue

            item = items[0]  # Take first matching item

            # Allocate equipment
            movement = await self.inventory_service.inventory_manager.create_stock_movement(
                db,
                tenant_id,
                {
                    "item_id": str(item.id),
                    "warehouse_id": datacenter_warehouse_id,
                    "movement_type": MovementType.ISSUE,
                    "quantity": equipment_req["quantity"],
                    "project_id": deployment_id,
                    "reason_description": f"Equipment allocated for tenant deployment {deployment_id}",
                },
                allocated_by,
            )

            movements.append(StockMovementResponse.model_validate(movement))

        return movements


class InventoryPlatformAdapter:
    """Main adapter that routes to appropriate platform adapters."""

    def __init__(
        self,
        management_adapter: ManagementInventoryAdapter = None,
        isp_adapter: ISPInventoryAdapter = None,
    ):
        self.management_adapter = management_adapter
        self.isp_adapter = isp_adapter

    def get_adapter(self, platform: str) -> Optional[BaseInventoryAdapter]:
        """Get adapter for specific platform."""
        if platform == "management":
            return self.management_adapter
        elif platform == "isp":
            return self.isp_adapter
        return None

    async def setup_platform_inventory(
        self,
        platform: str,
        db: AsyncSession,
        tenant_id: str,
        config: Optional[dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """Setup inventory for specific platform."""

        adapter = self.get_adapter(platform)
        if not adapter:
            raise ValueError(f"Unknown platform: {platform}")

        if platform == "management":
            return await adapter.setup_datacenter_inventory(
                db, tenant_id, config.get("datacenter_locations"), created_by
            )
        elif platform == "isp":
            equipment_result = await adapter.setup_isp_equipment_catalog(db, tenant_id, created_by)
            warehouses_result = await adapter.setup_isp_warehouses(db, tenant_id, config.get("locations"), created_by)

            return {
                "equipment": equipment_result,
                "warehouses": warehouses_result,
                "summary": {
                    "equipment_created": len(equipment_result),
                    "warehouses_created": len(warehouses_result),
                },
            }

        return {}

    async def send_platform_notification(
        self,
        platform: str,
        notification_type: str,
        recipient: str,
        data: dict[str, Any],
        **kwargs,
    ) -> bool:
        """Send notification through appropriate platform."""
        adapter = self.get_adapter(platform)
        if adapter:
            return await adapter.send_inventory_notification(notification_type, recipient, data, **kwargs)
        return False
