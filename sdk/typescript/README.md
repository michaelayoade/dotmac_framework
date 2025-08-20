# DotMac Platform TypeScript SDK

Official TypeScript SDK for the DotMac Platform API.

## Installation

```bash
npm install @dotmac/platform-sdk
```

## Quick Start

```typescript
import DotMacClient from '@dotmac/platform-sdk';

// Initialize client with API key
const client = new DotMacClient({
  baseURL: 'https://api.dotmac.com',
  apiKey: 'your-api-key',
});

// Or with access token
const client = new DotMacClient({
  baseURL: 'https://api.dotmac.com',
  accessToken: 'your-jwt-token',
});

// Create a customer
const customer = await client.customers.create({
  display_name: 'Acme Corp',
  customer_type: 'business',
  primary_email: 'contact@acme.com',
  primary_phone: '+1-555-0123',
});

// List customers
const customers = await client.customers.list({
  page: 1,
  limit: 20,
  state: 'active',
});

// Get customer details
const customer = await client.customers.get('cust_123');

// Create a support ticket
const ticket = await client.tickets.create({
  customer_id: 'cust_123',
  subject: 'Internet connection issue',
  description: 'Connection drops every hour',
  priority: 'high',
});
```

## Error Handling

```typescript
try {
  const customer = await client.customers.get('invalid_id');
} catch (error) {
  if (axios.isAxiosError(error)) {
    console.error('API Error:', error.response?.data);
  }
}
```

## TypeScript Support

This SDK is written in TypeScript and provides full type definitions.

## Documentation

Full documentation: https://docs.dotmac.com/sdk/typescript

## License

MIT License
