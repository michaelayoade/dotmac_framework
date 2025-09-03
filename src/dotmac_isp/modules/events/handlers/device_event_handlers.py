"""
Device Event Handlers.

Event handlers for device-related events including health changes,
state changes, and device lifecycle events.
"""

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from dotmac_isp.modules.noc.services.alarm_management_service import AlarmManagementService
from dotmac_isp.modules.noc.services.event_correlation_service import EventCorrelationService
from dotmac_shared.device_management.dotmac_device_management.services.device_service import DeviceService

logger = logging.getLogger(__name__)


class DeviceEventHandlers:
    """Event handlers for device-related events."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        
        # Initialize services
        self.alarm_service = AlarmManagementService(db, tenant_id)
        self.correlation_service = EventCorrelationService(db, tenant_id)
        self.device_service = DeviceService(db, tenant_id)

    async def handle_device_health_changed(self, event: Dict[str, Any]) -> None:
        """Handle device health change events."""
        try:
            data = event["data"]
            device_id = data["device_id"]
            health_status = data["health_status"]
            health_score = data["health_score"]
            metrics = data.get("metrics", {})

            logger.info(f"Processing device health change for {device_id}: {health_status} (score: {health_score})")

            # Create correlation event
            await self.correlation_service.process_incoming_event({
                "event_type": "device_health_change",
                "severity": self._get_severity_from_health(health_status),
                "title": f"Device {device_id} health changed to {health_status}",
                "description": f"Device health score: {health_score}, Status: {health_status}",
                "device_id": device_id,
                "source_system": "device_monitoring",
                "raw_data": {
                    "health_status": health_status,
                    "health_score": health_score,
                    "metrics": metrics,
                    "event_source": event.get("source", "unknown")
                }
            })

            # Generate alarms based on health status
            if health_status in ["critical", "degraded"]:
                await self._create_device_health_alarm(device_id, health_status, health_score, metrics)

            # Evaluate alarm rules against metrics
            if metrics:
                generated_alarms = await self.alarm_service.evaluate_alarm_rules({
                    "device_id": device_id,
                    **metrics
                })
                
                if generated_alarms:
                    logger.info(f"Generated {len(generated_alarms)} alarms from device metrics for {device_id}")

        except Exception as e:
            logger.error(f"Error handling device health change event: {str(e)}")

    async def handle_device_state_change(self, event: Dict[str, Any]) -> None:
        """Handle device state change events (up/down)."""
        try:
            data = event["data"]
            device_id = data["device_id"]
            current_state = data["current_state"]
            previous_state = data.get("previous_state")

            logger.info(f"Processing device state change for {device_id}: {previous_state} -> {current_state}")

            # Create correlation event
            await self.correlation_service.process_incoming_event({
                "event_type": "device_state_change",
                "severity": "high" if current_state == "down" else "medium",
                "title": f"Device {device_id} state changed to {current_state}",
                "description": f"Device state changed from {previous_state} to {current_state}",
                "device_id": device_id,
                "previous_state": previous_state,
                "current_state": current_state,
                "source_system": "device_monitoring",
                "raw_data": data
            })

            # Create alarm for device down
            if current_state == "down":
                await self.alarm_service.create_alarm({
                    "alarm_type": "device_down",
                    "severity": "critical",
                    "device_id": device_id,
                    "title": f"Device {device_id} is down",
                    "description": f"Device {device_id} changed state from {previous_state} to down",
                    "source_system": "device_monitoring",
                    "context_data": {
                        "previous_state": previous_state,
                        "current_state": current_state,
                        "state_change_time": event.get("timestamp")
                    },
                    "tags": ["device_down", "infrastructure"]
                })

            # Clear alarm for device up (if coming from down state)
            elif current_state == "up" and previous_state == "down":
                # Find and clear device down alarms
                existing_alarms = await self.alarm_service.get_alarms_list(
                    device_filter=device_id,
                    alarm_type_filter="device_down",
                    status_filter=["active", "acknowledged"]
                )
                
                for alarm_data in existing_alarms.get("alarms", []):
                    await self.alarm_service.clear_alarm(
                        alarm_data["alarm_id"],
                        "system",
                        f"Device {device_id} is back online"
                    )

        except Exception as e:
            logger.error(f"Error handling device state change event: {str(e)}")

    async def handle_interface_state_change(self, event: Dict[str, Any]) -> None:
        """Handle interface state change events."""
        try:
            data = event["data"]
            device_id = data["device_id"]
            interface_id = data["interface_id"]
            current_state = data["current_state"]
            previous_state = data.get("previous_state")

            logger.info(f"Processing interface state change for {device_id}:{interface_id}: {previous_state} -> {current_state}")

            # Create correlation event
            await self.correlation_service.process_incoming_event({
                "event_type": "interface_state_change",
                "severity": "medium" if current_state == "down" else "low",
                "title": f"Interface {interface_id} on {device_id} state changed to {current_state}",
                "description": f"Interface state changed from {previous_state} to {current_state}",
                "device_id": device_id,
                "interface_id": interface_id,
                "previous_state": previous_state,
                "current_state": current_state,
                "source_system": "interface_monitoring",
                "raw_data": data
            })

            # Create alarm for interface down
            if current_state == "down":
                await self.alarm_service.create_alarm({
                    "alarm_type": "interface_down",
                    "severity": "major",
                    "device_id": device_id,
                    "interface_id": interface_id,
                    "title": f"Interface {interface_id} down on {device_id}",
                    "description": f"Interface {interface_id} on device {device_id} is down",
                    "source_system": "interface_monitoring",
                    "context_data": {
                        "interface_id": interface_id,
                        "previous_state": previous_state,
                        "current_state": current_state,
                        "interface_type": data.get("interface_type"),
                        "interface_speed": data.get("interface_speed")
                    },
                    "tags": ["interface_down", "network"]
                })

        except Exception as e:
            logger.error(f"Error handling interface state change event: {str(e)}")

    async def handle_device_configuration_change(self, event: Dict[str, Any]) -> None:
        """Handle device configuration change events."""
        try:
            data = event["data"]
            device_id = data["device_id"]
            change_type = data.get("change_type", "unknown")
            change_summary = data.get("change_summary", "Configuration changed")

            logger.info(f"Processing configuration change for {device_id}: {change_type}")

            # Create correlation event
            await self.correlation_service.process_incoming_event({
                "event_type": "configuration_change",
                "severity": "medium",
                "title": f"Configuration change on {device_id}: {change_type}",
                "description": change_summary,
                "device_id": device_id,
                "source_system": "configuration_management",
                "raw_data": data
            })

            # Create informational alarm for significant config changes
            if change_type in ["major_change", "security_change", "routing_change"]:
                await self.alarm_service.create_alarm({
                    "alarm_type": "configuration_change",
                    "severity": "minor",
                    "device_id": device_id,
                    "title": f"Configuration change on {device_id}",
                    "description": f"{change_type}: {change_summary}",
                    "source_system": "configuration_management",
                    "context_data": {
                        "change_type": change_type,
                        "change_summary": change_summary,
                        "change_user": data.get("changed_by"),
                        "change_time": event.get("timestamp")
                    },
                    "tags": ["config_change", "audit"]
                })

        except Exception as e:
            logger.error(f"Error handling device configuration change event: {str(e)}")

    async def handle_high_cpu_utilization(self, event: Dict[str, Any]) -> None:
        """Handle high CPU utilization events."""
        try:
            data = event["data"]
            device_id = data["device_id"]
            cpu_usage = data["cpu_usage"]
            threshold = data.get("threshold", 90)

            logger.info(f"Processing high CPU utilization for {device_id}: {cpu_usage}%")

            # Create alarm for high CPU
            severity = "critical" if cpu_usage > 95 else "major" if cpu_usage > 90 else "minor"
            
            await self.alarm_service.create_alarm({
                "alarm_type": "high_cpu",
                "severity": severity,
                "device_id": device_id,
                "title": f"High CPU utilization on {device_id}: {cpu_usage}%",
                "description": f"CPU utilization ({cpu_usage}%) exceeded threshold ({threshold}%)",
                "source_system": "performance_monitoring",
                "context_data": {
                    "cpu_usage": cpu_usage,
                    "threshold": threshold,
                    "measurement_time": event.get("timestamp")
                },
                "tags": ["high_cpu", "performance"]
            })

        except Exception as e:
            logger.error(f"Error handling high CPU utilization event: {str(e)}")

    async def handle_high_memory_utilization(self, event: Dict[str, Any]) -> None:
        """Handle high memory utilization events."""
        try:
            data = event["data"]
            device_id = data["device_id"]
            memory_usage = data["memory_usage"]
            threshold = data.get("threshold", 85)

            logger.info(f"Processing high memory utilization for {device_id}: {memory_usage}%")

            # Create alarm for high memory
            severity = "critical" if memory_usage > 95 else "major" if memory_usage > 85 else "minor"
            
            await self.alarm_service.create_alarm({
                "alarm_type": "high_memory",
                "severity": severity,
                "device_id": device_id,
                "title": f"High memory utilization on {device_id}: {memory_usage}%",
                "description": f"Memory utilization ({memory_usage}%) exceeded threshold ({threshold}%)",
                "source_system": "performance_monitoring",
                "context_data": {
                    "memory_usage": memory_usage,
                    "threshold": threshold,
                    "measurement_time": event.get("timestamp")
                },
                "tags": ["high_memory", "performance"]
            })

        except Exception as e:
            logger.error(f"Error handling high memory utilization event: {str(e)}")

    # Private helper methods

    async def _create_device_health_alarm(
        self,
        device_id: str,
        health_status: str,
        health_score: float,
        metrics: Dict[str, Any]
    ) -> None:
        """Create alarm for device health issues."""
        severity_map = {
            "critical": "critical",
            "degraded": "major",
            "warning": "minor"
        }
        
        severity = severity_map.get(health_status, "minor")
        
        await self.alarm_service.create_alarm({
            "alarm_type": "device_health",
            "severity": severity,
            "device_id": device_id,
            "title": f"Device {device_id} health is {health_status}",
            "description": f"Device health score: {health_score}, Status: {health_status}",
            "source_system": "health_monitoring",
            "context_data": {
                "health_status": health_status,
                "health_score": health_score,
                "metrics_summary": {
                    "cpu_usage": metrics.get("cpu_usage"),
                    "memory_usage": metrics.get("memory_usage"),
                    "interface_errors": metrics.get("interface_errors")
                }
            },
            "tags": ["device_health", "monitoring"]
        })

    def _get_severity_from_health(self, health_status: str) -> str:
        """Map health status to event severity."""
        severity_map = {
            "critical": "critical",
            "degraded": "high",
            "warning": "medium",
            "healthy": "low"
        }
        return severity_map.get(health_status, "medium")