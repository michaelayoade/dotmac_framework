#!/usr/bin/env python3
"""
Plugin Installation Script

This script handles the installation of third-party integration plugins
by installing their dependencies and registering them with the plugin system.
"""

import subprocess
import sys
import json
import os
from pathlib import Path

# Plugin definitions with their required dependencies
PLUGIN_DEFINITIONS = {
    "twilio": {
        "name": "Twilio SMS Plugin",
        "dependencies": ["twilio>=9.7.1"],
        "category": "communication",
        "description": "SMS communication via Twilio API",
        "config_example": {
            "account_sid": "ACXXXX...",
            "auth_token": "your_auth_token", 
            "phone_number": "+1234567890"
        }
    },
    "stripe": {
        "name": "Stripe Payment Plugin", 
        "dependencies": ["stripe>=12.4.0"],
        "category": "billing",
        "description": "Payment processing via Stripe API",
        "config_example": {
            "api_key": "sk_test_...",
            "webhook_secret": "whsec_...",
            "currency": "usd"
        }
    },
    "network-automation": {
        "name": "Network Automation Plugin",
        "dependencies": ["pysnmp>=7.1.21", "paramiko>=4.0.0", "ansible-runner>=2.4.1"],
        "category": "network_automation", 
        "description": "Network device automation and monitoring",
        "config_example": {
            "snmp_community": "public",
            "snmp_version": "2c",
            "ssh_username": "admin",
            "ssh_key_path": "/path/to/ssh/key"
        }
    },
    "sendgrid": {
        "name": "SendGrid Email Plugin",
        "dependencies": ["sendgrid>=6.10.0"],
        "category": "communication",
        "description": "Email delivery via SendGrid API",
        "config_example": {
            "api_key": "SG.xxx...",
            "from_email": "noreply@yourdomain.com"
        }
    },
    "slack": {
        "name": "Slack Integration Plugin", 
        "dependencies": ["slack-sdk>=3.27.0"],
        "category": "communication",
        "description": "Slack notifications and integrations",
        "config_example": {
            "bot_token": "xoxb-...",
            "channel": "#notifications"
        }
    },
    "mailchimp": {
        "name": "Mailchimp Marketing Plugin",
        "dependencies": ["mailchimp3>=3.0.21"],
        "category": "crm_integration", 
        "description": "Email marketing via Mailchimp",
        "config_example": {
            "api_key": "xxx-us1",
            "server": "us1"
        }
    },
    "hubspot": {
        "name": "HubSpot CRM Plugin",
        "dependencies": ["hubspot-api-client>=8.1.0"],
        "category": "crm_integration",
        "description": "CRM integration with HubSpot",
        "config_example": {
            "access_token": "pat-...",
            "portal_id": "12345"
        }
    },
    
    # Additional Communication Plugins
    "discord": {
        "name": "Discord Integration Plugin",
        "dependencies": ["discord.py>=2.3.0"],
        "category": "communication",
        "description": "Discord bot notifications and community management",
        "config_example": {
            "bot_token": "your_bot_token",
            "guild_id": "your_server_id",
            "channel_id": "notifications_channel"
        }
    },
    "whatsapp": {
        "name": "WhatsApp Business Plugin",
        "dependencies": ["requests>=2.31.0"],
        "category": "communication",
        "description": "WhatsApp Business API integration",
        "config_example": {
            "access_token": "your_access_token",
            "phone_number_id": "your_phone_number_id",
            "verify_token": "your_verify_token"
        }
    },
    "teams": {
        "name": "Microsoft Teams Plugin",
        "dependencies": ["pymsteams>=0.2.2"],
        "category": "communication",
        "description": "Microsoft Teams webhook notifications",
        "config_example": {
            "webhook_url": "https://outlook.office.com/webhook/...",
            "card_title": "ISP Notifications"
        }
    },
    
    # Additional Billing Plugins
    "paypal": {
        "name": "PayPal Payment Plugin",
        "dependencies": ["paypalrestsdk>=1.13.3"],
        "category": "billing",
        "description": "PayPal payment processing",
        "config_example": {
            "client_id": "your_client_id",
            "client_secret": "your_client_secret",
            "mode": "sandbox"
        }
    },
    "square": {
        "name": "Square Payment Plugin", 
        "dependencies": ["squareup>=28.0.0"],
        "category": "billing",
        "description": "Square payment processing",
        "config_example": {
            "access_token": "your_access_token",
            "environment": "sandbox",
            "location_id": "your_location_id"
        }
    },
    "quickbooks": {
        "name": "QuickBooks Integration Plugin",
        "dependencies": ["intuitlib>=1.2.4"],
        "category": "billing",
        "description": "QuickBooks Online integration for accounting",
        "config_example": {
            "client_id": "your_client_id",
            "client_secret": "your_client_secret",
            "redirect_uri": "https://your-app.com/callback"
        }
    },
    "paystack": {
        "name": "Paystack Payment Plugin",
        "dependencies": ["pypaystack2>=2.1.0"],
        "category": "billing",
        "description": "Paystack payment processing (Africa-focused)",
        "config_example": {
            "secret_key": "sk_test_...",
            "public_key": "pk_test_...",
            "callback_url": "https://your-app.com/paystack/callback"
        }
    },
    
    # Network Management Plugins
    "mikrotik": {
        "name": "MikroTik RouterOS Plugin",
        "dependencies": ["librouteros>=3.2.0"],
        "category": "network_automation",
        "description": "MikroTik RouterOS API integration",
        "config_example": {
            "host": "192.168.1.1",
            "username": "admin",
            "password": "your_password",
            "port": 8728
        }
    },
    "ubiquiti": {
        "name": "Ubiquiti UniFi Plugin",
        "dependencies": ["pyunifi>=2.21"],
        "category": "network_automation", 
        "description": "Ubiquiti UniFi Controller integration",
        "config_example": {
            "host": "unifi.local",
            "username": "admin",
            "password": "your_password",
            "port": 8443
        }
    },
    "netbox": {
        "name": "NetBox Integration Plugin",
        "dependencies": ["pynetbox>=7.3.0"],
        "category": "network_automation",
        "description": "NetBox network documentation integration",
        "config_example": {
            "api_url": "https://netbox.yourdomain.com/api/",
            "api_token": "your_api_token"
        }
    },
    
    # Monitoring & Analytics
    "datadog": {
        "name": "Datadog Monitoring Plugin",
        "dependencies": ["datadog-api-client>=2.19.0"],
        "category": "monitoring",
        "description": "Datadog infrastructure monitoring integration",
        "config_example": {
            "api_key": "your_api_key",
            "app_key": "your_app_key",
            "site": "datadoghq.com"
        }
    },
    "grafana": {
        "name": "Grafana Integration Plugin",
        "dependencies": ["grafana-api>=1.0.3"],
        "category": "monitoring",
        "description": "Grafana dashboard and metrics integration",
        "config_example": {
            "host": "https://grafana.yourdomain.com",
            "api_key": "your_api_key"
        }
    },
    
    # CRM & Marketing
    "salesforce": {
        "name": "Salesforce CRM Plugin",
        "dependencies": ["simple-salesforce>=1.12.4"],
        "category": "crm_integration",
        "description": "Salesforce CRM integration", 
        "config_example": {
            "username": "your_username",
            "password": "your_password",
            "security_token": "your_security_token",
            "domain": "test"
        }
    },
    "constant-contact": {
        "name": "Constant Contact Plugin",
        "dependencies": ["requests>=2.31.0"],
        "category": "crm_integration",
        "description": "Constant Contact email marketing",
        "config_example": {
            "api_key": "your_api_key",
            "access_token": "your_access_token"
        }
    },
    
    # Storage & Backup
    "aws-s3": {
        "name": "Amazon S3 Storage Plugin",
        "dependencies": ["boto3>=1.34.0"],
        "category": "storage",
        "description": "Amazon S3 file storage and backup",
        "config_example": {
            "access_key_id": "your_access_key",
            "secret_access_key": "your_secret_key",
            "bucket_name": "your_bucket",
            "region": "us-east-1"
        }
    },
    "google-drive": {
        "name": "Google Drive Plugin",
        "dependencies": ["google-api-python-client>=2.108.0", "google-auth>=2.23.0"],
        "category": "storage",
        "description": "Google Drive file storage integration",
        "config_example": {
            "service_account_file": "/path/to/service-account.json",
            "folder_id": "your_folder_id"
        }
    },
    
    # Support & Ticketing
    "zendesk": {
        "name": "Zendesk Support Plugin",
        "dependencies": ["zendesk>=1.1.1"],
        "category": "ticketing",
        "description": "Zendesk customer support integration",
        "config_example": {
            "subdomain": "your_subdomain",
            "email": "admin@yourdomain.com",
            "token": "your_api_token"
        }
    },
    "pagerduty": {
        "name": "PagerDuty Plugin",
        "dependencies": ["pypd>=1.1.0"],
        "category": "monitoring",
        "description": "PagerDuty incident management",
        "config_example": {
            "api_key": "your_api_key",
            "integration_key": "your_integration_key"
        }
    }
}

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent

def install_dependencies(dependencies):
    """Install plugin dependencies via pip."""
    print(f"Installing dependencies: {', '.join(dependencies)}")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade"
        ] + dependencies)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

def create_plugin_config_template(plugin_name, plugin_info):
    """Create a configuration template for the plugin."""
    config_dir = get_project_root() / "config" / "plugins"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / f"{plugin_name}.json.example"
    config_data = {
        "plugin_id": plugin_name,
        "name": plugin_info["name"],
        "category": plugin_info["category"],
        "enabled": False,
        "config_data": plugin_info["config_example"],
        "security": {
            "sandbox_enabled": True,
            "resource_limits": {
                "memory_mb": 256,
                "cpu_percent": 10
            }
        },
        "installation_notes": [
            f"1. Copy this file to {plugin_name}.json and configure your credentials",
            "2. Set environment variables or store secrets in your vault",
            "3. Enable the plugin by setting 'enabled': true",
            f"4. Use the Plugin Manager API to load and activate the plugin"
        ]
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"Configuration template created: {config_file}")
    return config_file

def register_plugin_metadata(plugin_name, plugin_info):
    """Register plugin metadata for discovery."""
    metadata_dir = get_project_root() / "src" / "dotmac_isp" / "plugins" / "registry"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_file = metadata_dir / "available_plugins.json"
    
    # Load existing metadata or create new
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {"plugins": {}}
    
    # Add/update plugin metadata
    metadata["plugins"][plugin_name] = {
        "name": plugin_info["name"],
        "category": plugin_info["category"], 
        "description": plugin_info["description"],
        "dependencies": plugin_info["dependencies"],
        "installed": True,
        "config_template": f"config/plugins/{plugin_name}.json.example"
    }
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Plugin metadata registered in: {metadata_file}")

def install_plugin(plugin_name):
    """Install a specific plugin."""
    if plugin_name not in PLUGIN_DEFINITIONS:
        print(f"Unknown plugin: {plugin_name}")
        print(f"Available plugins: {', '.join(PLUGIN_DEFINITIONS.keys())}")
        return False
    
    plugin_info = PLUGIN_DEFINITIONS[plugin_name]
    print(f"\nInstalling {plugin_info['name']}...")
    print(f"Description: {plugin_info['description']}")
    print(f"Category: {plugin_info['category']}")
    
    # Install dependencies
    if not install_dependencies(plugin_info["dependencies"]):
        return False
    
    # Create configuration template
    config_file = create_plugin_config_template(plugin_name, plugin_info)
    
    # Register plugin metadata
    register_plugin_metadata(plugin_name, plugin_info)
    
    print(f"\n✅ {plugin_info['name']} installed successfully!")
    print(f"\nNext steps:")
    print(f"1. Configure the plugin: {config_file}")
    print(f"2. Copy the example config and set your credentials")
    print(f"3. Load the plugin via the Plugin Manager API")
    print(f"4. Activate the plugin for your tenant(s)")
    
    return True

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python install_plugin.py <plugin_name>")
        print(f"Available plugins: {', '.join(PLUGIN_DEFINITIONS.keys())}")
        sys.exit(1)
    
    plugin_name = sys.argv[1].lower()
    
    # Check if we're in the right directory
    project_root = get_project_root()
    if not (project_root / "pyproject.toml").exists():
        print("Error: Must be run from the project root directory")
        sys.exit(1)
    
    success = install_plugin(plugin_name)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()