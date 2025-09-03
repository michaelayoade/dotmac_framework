/**
 * Mock Tenant Container Server
 * 
 * Simulates tenant container endpoints for CI/CD testing
 * without requiring full container orchestration.
 */

const express = require('express');
const WebSocket = require('ws');
const app = express();
const PORT = 3100;

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'tenant-mock' });
});

// Mock tenant dashboard
app.get('/dashboard', (req, res) => {
  res.json({
    tenantId: 'mock-tenant-123',
    name: 'Mock Tenant Corp',
    status: 'active',
    apps: ['isp_framework', 'crm', 'e_commerce']
  });
});

// Mock settings endpoint
app.get('/settings/organization', (req, res) => {
  res.json({
    companyName: 'Mock Tenant Corp',
    timezone: 'America/New_York',
    lastUpdated: new Date().toISOString()
  });
});

// Mock notification endpoint
app.post('/api/notifications', (req, res) => {
  console.log('Mock tenant received notification:', req.body);
  res.json({ status: 'received', id: `notif_${Date.now()}` });
});

// Start HTTP server
const server = app.listen(PORT, () => {
  console.log(`Mock tenant server running on port ${PORT}`);
});

// WebSocket server for real-time communication testing
const wss = new WebSocket.Server({ server });

wss.on('connection', (ws, req) => {
  console.log('Mock WebSocket connection established');
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      console.log('Mock tenant received WebSocket message:', data);
      
      // Echo back with mock response
      const response = {
        type: 'response',
        originalType: data.type,
        timestamp: Date.now(),
        status: 'received',
        mockData: true
      };
      
      ws.send(JSON.stringify(response));
    } catch (e) {
      console.error('Invalid JSON message:', e);
    }
  });
  
  ws.on('close', () => {
    console.log('Mock WebSocket connection closed');
  });
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Shutting down mock tenant server...');
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('Shutting down mock tenant server...');
  server.close(() => {
    process.exit(0);
  });
});