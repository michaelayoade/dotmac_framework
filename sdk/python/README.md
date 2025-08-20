# DotMac Platform Python SDK

Official Python SDK for the DotMac Platform API.

## Installation

```bash
pip install dotmac-platform-sdk
```

## Quick Start

```python
from dotmac_sdk import DotMacClient

# Initialize client with API key
client = DotMacClient(
    base_url="https://api.dotmac.com",
    api_key="your-api-key"
)

# Or with access token
client = DotMacClient(
    base_url="https://api.dotmac.com",
    access_token="your-jwt-token"
)

# Create a customer
customer = client.customers.create({
    "display_name": "Acme Corp",
    "customer_type": "business",
    "primary_email": "contact@acme.com",
    "primary_phone": "+1-555-0123"
})

# List customers
customers = client.customers.list(page=1, limit=20, state="active")

# Get customer details
customer = client.customers.get("cust_123")

# Create a support ticket
ticket = client.tickets.create({
    "customer_id": "cust_123",
    "subject": "Internet connection issue",
    "description": "Connection drops every hour",
    "priority": "high"
})
```

## Services

- **Customers**: Customer account management
- **Invoices**: Billing and invoicing
- **Services**: Service provisioning
- **Tickets**: Support tickets
- **Network**: Network management

## Error Handling

```python
from dotmac_sdk import DotMacClient, DotMacAPIError

client = DotMacClient(api_key="your-api-key")

try:
    customer = client.customers.get("invalid_id")
except DotMacAPIError as e:
    print(f"API Error: {e}")
```

## Documentation

Full documentation: https://docs.dotmac.com/sdk/python

## License

MIT License
