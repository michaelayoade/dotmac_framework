"""
NetJSON Support for DotMac - Adds OpenWrt UCI generation capability.
Lightweight alternative to full OpenWISP Controller integration.
"""

from typing import Any, Dict, List, Optional
import json


class NetJSONRenderer:
    """
    Convert NetJSON DeviceConfiguration to OpenWrt UCI commands.
    Provides the key OpenWISP functionality without the overhead.
    """

    def __init__(self):
        self.uci_commands = []

    def render_openwrt_config(self, netjson_config: Dict[str, Any]) -> str:
        """
        Convert NetJSON configuration to UCI commands.

        Example NetJSON input:
        {
          "interfaces": [
            {
              "name": "wlan0",
              "type": "wireless",
              "wireless": {
                "mode": "access_point",
                "ssid": "MyNetwork",
                "encryption": {"protocol": "wpa2", "key": "password"}
              }
            }
          ]
        }
        """
        self.uci_commands = []

        # Process interfaces
        if "interfaces" in netjson_config:
            self._render_interfaces(netjson_config["interfaces"])

        # Process system settings
        if "system" in netjson_config:
            self._render_system(netjson_config["system"])

        # Process network settings
        if "network" in netjson_config:
            self._render_network_settings(netjson_config["network"])

        # Add commit command
        self.uci_commands.append("uci commit")

        return "\n".join(self.uci_commands)

    def _render_interfaces(self, interfaces: List[Dict[str, Any]]) -> None:
        """Render network interfaces to UCI commands."""
        for idx, interface in enumerate(interfaces):
            if interface.get("type") == "wireless":
                self._render_wireless_interface(interface, idx)
            elif interface.get("type") == "ethernet":
                self._render_ethernet_interface(interface, idx)
            elif interface.get("type") == "bridge":
                self._render_bridge_interface(interface, idx)

    def _render_wireless_interface(self, interface: Dict[str, Any], idx: int) -> None:
        """Render wireless interface configuration."""
        name = interface.get("name", f"wlan{idx}")
        wireless = interface.get("wireless", {})

        # Basic wireless configuration
        if "ssid" in wireless:
            self.uci_commands.append(
                f"uci set wireless.@wifi-iface[{idx}].ssid='{wireless['ssid']}'"
            )

        if "mode" in wireless:
            mode_mapping = {
                "access_point": "ap",
                "station": "sta",
                "adhoc": "adhoc",
                "monitor": "monitor",
            }
            uci_mode = mode_mapping.get(wireless["mode"], wireless["mode"])
            self.uci_commands.append(
                f"uci set wireless.@wifi-iface[{idx}].mode='{uci_mode}'"
            )

        # Encryption settings
        if "encryption" in wireless:
            encryption = wireless["encryption"]
            protocol = encryption.get("protocol", "none")

            if protocol == "wpa2":
                self.uci_commands.append(
                    f"uci set wireless.@wifi-iface[{idx}].encryption='psk2'"
                )
                if "key" in encryption:
                    self.uci_commands.append(
                        f"uci set wireless.@wifi-iface[{idx}].key='{encryption['key']}'"
                    )
            elif protocol == "wpa3":
                self.uci_commands.append(
                    f"uci set wireless.@wifi-iface[{idx}].encryption='sae'"
                )
                if "key" in encryption:
                    self.uci_commands.append(
                        f"uci set wireless.@wifi-iface[{idx}].key='{encryption['key']}'"
                    )
            elif protocol == "none":
                self.uci_commands.append(
                    f"uci set wireless.@wifi-iface[{idx}].encryption='none'"
                )

        # Network assignment
        if "network" in interface:
            self.uci_commands.append(
                f"uci set wireless.@wifi-iface[{idx}].network='{interface['network']}'"
            )

        # Enable the interface
        self.uci_commands.append(f"uci set wireless.@wifi-iface[{idx}].disabled='0'")

    def _render_ethernet_interface(self, interface: Dict[str, Any], idx: int) -> None:
        """Render ethernet interface configuration."""
        name = interface.get("name", f"eth{idx}")

        # Create network interface
        self.uci_commands.append(f"uci set network.{name}=interface")
        self.uci_commands.append(f"uci set network.{name}.ifname='{name}'")

        # IP configuration
        if "addresses" in interface and interface["addresses"]:
            address = interface["addresses"][0]  # Use first address
            if "address" in address and "mask" in address:
                ip = address["address"]
                mask = address["mask"]
                self.uci_commands.append(f"uci set network.{name}.proto='static'")
                self.uci_commands.append(f"uci set network.{name}.ipaddr='{ip}'")
                self.uci_commands.append(f"uci set network.{name}.netmask='{mask}'")
        else:
            # DHCP client by default
            self.uci_commands.append(f"uci set network.{name}.proto='dhcp'")

    def _render_bridge_interface(self, interface: Dict[str, Any], idx: int) -> None:
        """Render bridge interface configuration."""
        name = interface.get("name", f"br{idx}")

        self.uci_commands.append(f"uci set network.{name}=interface")
        self.uci_commands.append(f"uci set network.{name}.type='bridge'")

        # Bridge ports
        if "bridge" in interface and "members" in interface["bridge"]:
            members = " ".join(interface["bridge"]["members"])
            self.uci_commands.append(f"uci set network.{name}.ifname='{members}'")

    def _render_system(self, system: Dict[str, Any]) -> None:
        """Render system configuration."""
        if "hostname" in system:
            self.uci_commands.append(
                f"uci set system.@system[0].hostname='{system['hostname']}'"
            )

        if "timezone" in system:
            self.uci_commands.append(
                f"uci set system.@system[0].timezone='{system['timezone']}'"
            )

    def _render_network_settings(self, network: Dict[str, Any]) -> None:
        """Render network-wide settings."""
        # DNS servers
        if "dns_servers" in network:
            dns_servers = " ".join(network["dns_servers"])
            self.uci_commands.append(f"uci set network.wan.dns='{dns_servers}'")

        # Default gateway
        if "gateway" in network:
            self.uci_commands.append(
                f"uci set network.wan.gateway='{network['gateway']}'"
            )


class NetJSONValidator:
    """Validate NetJSON configuration before rendering."""

    @staticmethod
    def validate_netjson(config: Dict[str, Any]) -> List[str]:
        """
        Validate NetJSON configuration and return list of errors.
        Returns empty list if valid.
        """
        errors = []

        # Check for required fields
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return errors

        # Validate interfaces
        if "interfaces" in config:
            if not isinstance(config["interfaces"], list):
                errors.append("Interfaces must be a list")
            else:
                for idx, interface in enumerate(config["interfaces"]):
                    interface_errors = NetJSONValidator._validate_interface(
                        interface, idx
                    )
                    errors.extend(interface_errors)

        return errors

    @staticmethod
    def _validate_interface(interface: Dict[str, Any], idx: int) -> List[str]:
        """Validate single interface configuration."""
        errors = []
        prefix = f"Interface {idx}"

        # Required fields
        if "name" not in interface:
            errors.append(f"{prefix}: name is required")

        if "type" not in interface:
            errors.append(f"{prefix}: type is required")
        elif interface["type"] not in ["wireless", "ethernet", "bridge", "loopback"]:
            errors.append(f"{prefix}: invalid type '{interface['type']}'")

        # Validate wireless specific fields
        if interface.get("type") == "wireless":
            wireless = interface.get("wireless", {})
            if "mode" in wireless and wireless["mode"] not in [
                "access_point",
                "station",
                "adhoc",
                "monitor",
            ]:
                errors.append(f"{prefix}: invalid wireless mode '{wireless['mode']}'")

            if "encryption" in wireless:
                encryption = wireless["encryption"]
                if "protocol" in encryption and encryption["protocol"] not in [
                    "none",
                    "wep",
                    "wpa",
                    "wpa2",
                    "wpa3",
                ]:
                    errors.append(
                        f"{prefix}: invalid encryption protocol '{encryption['protocol']}'"
                    )

        return errors


class NetJSONTemplateEngine:
    """Template engine for NetJSON configurations with variable substitution."""

    def __init__(self):
        self.variables = {}

    def set_variables(self, variables: Dict[str, Any]) -> None:
        """Set template variables for substitution."""
        self.variables = variables

    def render_template(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render NetJSON template with variable substitution.

        Template variables use {{variable_name}} syntax:
        {
          "interfaces": [
            {
              "name": "wlan0",
              "wireless": {
                "ssid": "{{wifi_ssid}}",
                "encryption": {"key": "{{wifi_password}}"}
              }
            }
          ]
        }
        """
        template_str = json.dumps(template_config)

        # Simple variable substitution
        for var_name, var_value in self.variables.items():
            template_str = template_str.replace(f"{{{{{var_name}}}}}", str(var_value))

        return json.loads(template_str)


# Integration with existing DotMac device_config.py
class NetJSONConfigMixin:
    """Mixin to add NetJSON support to existing DeviceConfigSDK."""

    def __init__(self):
        self.netjson_renderer = NetJSONRenderer()
        self.netjson_validator = NetJSONValidator()
        self.netjson_template_engine = NetJSONTemplateEngine()

    async def create_netjson_template(
        self,
        template_name: str,
        device_type: str,
        netjson_config: Dict[str, Any],
        variables: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create NetJSON-based configuration template."""

        # Validate NetJSON config
        errors = self.netjson_validator.validate_netjson(netjson_config)
        if errors:
            raise ValueError(f"Invalid NetJSON configuration: {errors}")

        # Store as template
        template = {
            "template_id": str(uuid4()),
            "template_name": template_name,
            "device_type": device_type,
            "vendor": "OpenWrt",
            "template_format": "netjson",
            "template_content": json.dumps(netjson_config),
            "variables": variables or [],
            "created_at": utc_now().isoformat(),
            **kwargs,
        }

        return template

    async def render_netjson_to_uci(
        self, template_id: str, variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render NetJSON template to UCI commands."""

        # Get template (implementation depends on storage backend)
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        netjson_config = json.loads(template["template_content"])

        # Apply variables if provided
        if variables:
            self.netjson_template_engine.set_variables(variables)
            netjson_config = self.netjson_template_engine.render_template(
                netjson_config
            )

        # Convert to UCI
        return self.netjson_renderer.render_openwrt_config(netjson_config)
