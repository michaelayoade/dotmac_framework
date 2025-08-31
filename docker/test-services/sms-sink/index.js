const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const winston = require('winston');
const { v4: uuidv4 } = require('uuid');
const rateLimit = require('express-rate-limit');
const bodyParser = require('body-parser');
const fs = require('fs').promises;
const path = require('path');

// Configure logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: '/app/logs/sms-sink.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

class SMSSink {
  constructor() {
    this.messages = new Map(); // In-memory storage for testing
    this.webhookEndpoints = new Map(); // Registered webhook endpoints
    this.stats = {
      totalReceived: 0,
      totalSent: 0,
      totalFailed: 0,
      startTime: Date.now()
    };
    
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  setupMiddleware() {
    this.app.use(helmet());
    this.app.use(cors());
    this.app.use(bodyParser.json({ limit: '1mb' }));
    this.app.use(bodyParser.urlencoded({ extended: true }));

    // Rate limiting for webhook endpoint
    const webhookLimiter = rateLimit({
      windowMs: 1 * 60 * 1000, // 1 minute
      max: 100, // Limit each IP to 100 requests per windowMs
      message: 'Too many SMS requests from this IP'
    });

    this.app.use('/webhook', webhookLimiter);
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        uptime: Date.now() - this.stats.startTime,
        stats: this.stats
      });
    });

    // SMS webhook endpoint (receives SMS from providers)
    this.app.post('/webhook', (req, res) => {
      this.handleIncomingSMS(req, res);
    });

    // Send SMS endpoint (simulates SMS provider API)
    this.app.post('/send', (req, res) => {
      this.handleOutgoingSMS(req, res);
    });

    // Management API
    this.app.get('/messages', (req, res) => {
      this.getMessages(req, res);
    });

    this.app.get('/messages/:id', (req, res) => {
      this.getMessage(req, res);
    });

    this.app.delete('/messages', (req, res) => {
      this.clearMessages(req, res);
    });

    // Webhook management
    this.app.post('/webhooks', (req, res) => {
      this.registerWebhook(req, res);
    });

    this.app.get('/webhooks', (req, res) => {
      this.listWebhooks(req, res);
    });

    // Statistics
    this.app.get('/stats', (req, res) => {
      res.json(this.stats);
    });

    // Web UI (simple HTML interface)
    this.app.get('/', (req, res) => {
      res.send(this.generateWebUI());
    });

    // Start server
    const SMS_PORT = process.env.SMS_SINK_PORT || 3030;
    this.app.listen(SMS_PORT, '0.0.0.0', () => {
      logger.info(`SMS Sink server listening on port ${SMS_PORT}`);
      logger.info(`Web UI available at http://localhost:${SMS_PORT}/`);
    });
  }

  handleIncomingSMS(req, res) {
    try {
      const smsData = {
        id: uuidv4(),
        direction: 'inbound',
        from: req.body.from || req.body.FromNumber || req.body.sender,
        to: req.body.to || req.body.ToNumber || req.body.recipient,
        message: req.body.message || req.body.Body || req.body.text,
        timestamp: new Date().toISOString(),
        provider: req.headers['user-agent'] || 'unknown',
        raw: req.body
      };

      this.messages.set(smsData.id, smsData);
      this.stats.totalReceived++;

      logger.info('Incoming SMS received', {
        id: smsData.id,
        from: smsData.from,
        to: smsData.to,
        message: smsData.message?.substring(0, 100) + '...'
      });

      // Trigger any registered webhooks
      this.triggerWebhooks(smsData);

      res.status(200).json({
        success: true,
        id: smsData.id,
        message: 'SMS received successfully'
      });

    } catch (error) {
      logger.error('Error handling incoming SMS', error);
      this.stats.totalFailed++;
      res.status(500).json({
        success: false,
        error: 'Failed to process SMS'
      });
    }
  }

  handleOutgoingSMS(req, res) {
    try {
      const { to, from, message, tenant_id } = req.body;

      if (!to || !message) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: to, message'
        });
      }

      const smsData = {
        id: uuidv4(),
        direction: 'outbound',
        from: from || '+15551234567', // Default test number
        to: to,
        message: message,
        timestamp: new Date().toISOString(),
        tenant_id: tenant_id,
        status: 'delivered', // Always succeed in test environment
        raw: req.body
      };

      this.messages.set(smsData.id, smsData);
      this.stats.totalSent++;

      logger.info('Outgoing SMS sent', {
        id: smsData.id,
        from: smsData.from,
        to: smsData.to,
        tenant_id: smsData.tenant_id,
        message: smsData.message?.substring(0, 100) + '...'
      });

      res.status(200).json({
        success: true,
        id: smsData.id,
        status: 'delivered',
        message: 'SMS sent successfully'
      });

    } catch (error) {
      logger.error('Error sending SMS', error);
      this.stats.totalFailed++;
      res.status(500).json({
        success: false,
        error: 'Failed to send SMS'
      });
    }
  }

  getMessages(req, res) {
    const { tenant_id, direction, limit = 50 } = req.query;
    let messages = Array.from(this.messages.values());

    // Filter by tenant_id if provided
    if (tenant_id) {
      messages = messages.filter(msg => msg.tenant_id === tenant_id);
    }

    // Filter by direction if provided
    if (direction) {
      messages = messages.filter(msg => msg.direction === direction);
    }

    // Sort by timestamp (newest first) and limit
    messages = messages
      .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      .slice(0, parseInt(limit));

    res.json({
      messages,
      total: messages.length,
      stats: this.stats
    });
  }

  getMessage(req, res) {
    const message = this.messages.get(req.params.id);
    if (!message) {
      return res.status(404).json({
        success: false,
        error: 'Message not found'
      });
    }
    res.json(message);
  }

  clearMessages(req, res) {
    const { tenant_id } = req.query;
    
    if (tenant_id) {
      // Clear only messages for specific tenant
      for (const [id, message] of this.messages.entries()) {
        if (message.tenant_id === tenant_id) {
          this.messages.delete(id);
        }
      }
    } else {
      // Clear all messages
      this.messages.clear();
    }

    logger.info('Messages cleared', { tenant_id });
    res.json({ success: true, message: 'Messages cleared' });
  }

  registerWebhook(req, res) {
    const { url, events = ['sms.received'] } = req.body;
    if (!url) {
      return res.status(400).json({
        success: false,
        error: 'Webhook URL is required'
      });
    }

    const webhookId = uuidv4();
    this.webhookEndpoints.set(webhookId, { url, events, created: Date.now() });

    res.json({
      success: true,
      id: webhookId,
      message: 'Webhook registered successfully'
    });
  }

  listWebhooks(req, res) {
    const webhooks = Array.from(this.webhookEndpoints.entries()).map(([id, data]) => ({
      id,
      ...data
    }));
    res.json({ webhooks });
  }

  async triggerWebhooks(smsData) {
    for (const [id, webhook] of this.webhookEndpoints.entries()) {
      if (webhook.events.includes('sms.received')) {
        try {
          // In a real implementation, you'd make HTTP requests to webhook.url
          logger.info('Webhook triggered', {
            webhookId: id,
            url: webhook.url,
            smsId: smsData.id
          });
        } catch (error) {
          logger.error('Webhook trigger failed', error);
        }
      }
    }
  }

  generateWebUI() {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>DotMac SMS Sink - Testing Interface</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #e3f2fd; padding: 15px; border-radius: 6px; text-align: center; }
        .messages { margin-top: 20px; }
        .message { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 6px; }
        .message.inbound { border-left: 4px solid #4caf50; }
        .message.outbound { border-left: 4px solid #2196f3; }
        .controls { margin: 20px 0; }
        button { padding: 8px 16px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-primary { background: #2196f3; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 DotMac SMS Sink - Testing Interface</h1>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <h3>Total Received</h3>
                <div id="received">0</div>
            </div>
            <div class="stat-card">
                <h3>Total Sent</h3>
                <div id="sent">0</div>
            </div>
            <div class="stat-card">
                <h3>Total Failed</h3>
                <div id="failed">0</div>
            </div>
            <div class="stat-card">
                <h3>Uptime</h3>
                <div id="uptime">0s</div>
            </div>
        </div>

        <div class="controls">
            <button class="btn-primary" onclick="refreshMessages()">Refresh Messages</button>
            <button class="btn-danger" onclick="clearMessages()">Clear All Messages</button>
        </div>

        <div class="messages">
            <h2>Recent Messages</h2>
            <div id="messagesList">Loading...</div>
        </div>
    </div>

    <script>
        async function fetchStats() {
            const response = await fetch('/stats');
            const stats = await response.json();
            document.getElementById('received').textContent = stats.totalReceived;
            document.getElementById('sent').textContent = stats.totalSent;
            document.getElementById('failed').textContent = stats.totalFailed;
            document.getElementById('uptime').textContent = Math.floor((Date.now() - stats.startTime) / 1000) + 's';
        }

        async function fetchMessages() {
            const response = await fetch('/messages?limit=20');
            const data = await response.json();
            const messagesList = document.getElementById('messagesList');
            
            if (data.messages.length === 0) {
                messagesList.innerHTML = '<p>No messages yet. Send a test SMS to see it here.</p>';
                return;
            }

            messagesList.innerHTML = data.messages.map(msg => \`
                <div class="message \${msg.direction}">
                    <div><strong>\${msg.direction.toUpperCase()}</strong> - ID: \${msg.id}</div>
                    <div>From: \${msg.from} → To: \${msg.to}</div>
                    <div>Message: \${msg.message}</div>
                    <div class="timestamp">\${new Date(msg.timestamp).toLocaleString()}</div>
                    \${msg.tenant_id ? '<div>Tenant: ' + msg.tenant_id + '</div>' : ''}
                </div>
            \`).join('');
        }

        async function refreshMessages() {
            await fetchStats();
            await fetchMessages();
        }

        async function clearMessages() {
            if (confirm('Are you sure you want to clear all messages?')) {
                await fetch('/messages', { method: 'DELETE' });
                await refreshMessages();
            }
        }

        // Auto-refresh every 5 seconds
        setInterval(refreshMessages, 5000);
        
        // Initial load
        refreshMessages();
    </script>
</body>
</html>`;
  }
}

// Initialize and start the SMS sink
const smsSink = new SMSSink();

// Graceful shutdown
process.on('SIGINT', () => {
  logger.info('SMS Sink shutting down gracefully');
  process.exit(0);
});

process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled rejection', { reason, promise });
  process.exit(1);
});