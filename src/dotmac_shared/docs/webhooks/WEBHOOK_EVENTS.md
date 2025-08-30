# DotMac Platform Webhook Events Documentation

## Overview

The DotMac Platform provides real-time webhook notifications for important events across all services. Webhooks enable your applications to receive immediate updates when specific events occur, eliminating the need for polling.

## Configuration

### Webhook Endpoint Setup

```json
POST /api/v1/webhooks/endpoints
{
  "url": "https://your-app.com/webhooks/dotmac",
  "events": ["customer.created", "invoice.paid", "service.activated"],
  "secret": "your-webhook-secret",
  "active": true
}
```

### Authentication

All webhook requests include a signature header for verification:

```
X-DotMac-Signature: sha256=<signature>
```

Verify the signature using:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Event Structure

All webhook events follow this structure:

```json
{
  "id": "evt_1234567890",
  "type": "customer.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    // Event-specific data
  },
  "metadata": {
    "tenant_id": "default",
    "user_id": "usr_123",
    "request_id": "req_abc123"
  }
}
```

## Event Catalog

### 🔐 Identity Service Events

#### customer.created

Triggered when a new customer account is created.

```json
{
  "type": "customer.created",
  "data": {
    "customer_id": "cust_123",
    "display_name": "Acme Corp",
    "customer_type": "business",
    "state": "prospect",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### customer.activated

Customer account activated and ready for service.

```json
{
  "type": "customer.activated",
  "data": {
    "customer_id": "cust_123",
    "activation_date": "2024-01-15T10:30:00Z",
    "activated_by": "usr_456"
  }
}
```

#### customer.suspended

Customer account suspended due to non-payment or request.

```json
{
  "type": "customer.suspended",
  "data": {
    "customer_id": "cust_123",
    "reason": "non_payment",
    "suspension_date": "2024-01-15T10:30:00Z",
    "auto_resume_date": "2024-02-15T00:00:00Z"
  }
}
```

#### customer.churned

Customer has cancelled services and churned.

```json
{
  "type": "customer.churned",
  "data": {
    "customer_id": "cust_123",
    "churn_date": "2024-01-15T10:30:00Z",
    "churn_reason": "competitor",
    "lifetime_value": 5429.50
  }
}
```

#### user.login

User successfully logged in.

```json
{
  "type": "user.login",
  "data": {
    "user_id": "usr_123",
    "username": "john.doe",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "login_time": "2024-01-15T10:30:00Z"
  }
}
```

#### user.password_changed

User password was changed.

```json
{
  "type": "user.password_changed",
  "data": {
    "user_id": "usr_123",
    "changed_at": "2024-01-15T10:30:00Z",
    "change_type": "user_initiated"
  }
}
```

### 💰 Billing Service Events

#### invoice.created

New invoice generated for customer.

```json
{
  "type": "invoice.created",
  "data": {
    "invoice_id": "inv_123",
    "customer_id": "cust_123",
    "amount": 149.99,
    "currency": "USD",
    "due_date": "2024-02-01",
    "line_items": [
      {
        "description": "Internet Service - Premium",
        "amount": 149.99
      }
    ]
  }
}
```

#### invoice.paid

Invoice payment received and processed.

```json
{
  "type": "invoice.paid",
  "data": {
    "invoice_id": "inv_123",
    "payment_id": "pay_456",
    "amount_paid": 149.99,
    "payment_method": "credit_card",
    "paid_at": "2024-01-15T10:30:00Z"
  }
}
```

#### invoice.overdue

Invoice is past due date.

```json
{
  "type": "invoice.overdue",
  "data": {
    "invoice_id": "inv_123",
    "customer_id": "cust_123",
    "amount_due": 149.99,
    "days_overdue": 5,
    "due_date": "2024-01-10"
  }
}
```

#### payment.failed

Payment attempt failed.

```json
{
  "type": "payment.failed",
  "data": {
    "payment_id": "pay_456",
    "customer_id": "cust_123",
    "amount": 149.99,
    "failure_reason": "insufficient_funds",
    "retry_scheduled": "2024-01-17T00:00:00Z"
  }
}
```

#### subscription.created

New subscription created.

```json
{
  "type": "subscription.created",
  "data": {
    "subscription_id": "sub_123",
    "customer_id": "cust_123",
    "plan_id": "plan_premium",
    "start_date": "2024-01-15",
    "billing_cycle": "monthly",
    "amount": 149.99
  }
}
```

#### subscription.cancelled

Subscription cancelled by customer or system.

```json
{
  "type": "subscription.cancelled",
  "data": {
    "subscription_id": "sub_123",
    "cancellation_date": "2024-01-15",
    "cancellation_reason": "customer_request",
    "effective_date": "2024-02-01"
  }
}
```

#### credit.limit_exceeded

Customer exceeded credit limit.

```json
{
  "type": "credit.limit_exceeded",
  "data": {
    "customer_id": "cust_123",
    "credit_limit": 500.00,
    "current_balance": 525.00,
    "exceeded_amount": 25.00
  }
}
```

### 📦 Services Platform Events

#### service.provisioning_started

Service provisioning process initiated.

```json
{
  "type": "service.provisioning_started",
  "data": {
    "service_id": "svc_123",
    "customer_id": "cust_123",
    "service_type": "fiber_internet",
    "order_id": "ord_456",
    "estimated_completion": "2024-01-15T14:00:00Z"
  }
}
```

#### service.activated

Service successfully activated and ready for use.

```json
{
  "type": "service.activated",
  "data": {
    "service_id": "svc_123",
    "customer_id": "cust_123",
    "service_type": "fiber_internet",
    "activation_date": "2024-01-15T10:30:00Z",
    "configuration": {
      "speed": "1000/1000",
      "static_ip": "203.0.113.1"
    }
  }
}
```

#### service.suspended

Service temporarily suspended.

```json
{
  "type": "service.suspended",
  "data": {
    "service_id": "svc_123",
    "suspension_reason": "non_payment",
    "suspension_date": "2024-01-15T10:30:00Z"
  }
}
```

#### service.terminated

Service permanently terminated.

```json
{
  "type": "service.terminated",
  "data": {
    "service_id": "svc_123",
    "termination_date": "2024-01-15T10:30:00Z",
    "termination_reason": "customer_request"
  }
}
```

#### service.upgraded

Service plan upgraded.

```json
{
  "type": "service.upgraded",
  "data": {
    "service_id": "svc_123",
    "old_plan": "basic_100",
    "new_plan": "premium_1000",
    "upgrade_date": "2024-01-15T10:30:00Z",
    "price_difference": 50.00
  }
}
```

#### service.downgraded

Service plan downgraded.

```json
{
  "type": "service.downgraded",
  "data": {
    "service_id": "svc_123",
    "old_plan": "premium_1000",
    "new_plan": "basic_100",
    "downgrade_date": "2024-01-15T10:30:00Z",
    "price_difference": -50.00
  }
}
```

### 🌐 Networking Events

#### device.online

Network device came online.

```json
{
  "type": "device.online",
  "data": {
    "device_id": "dev_123",
    "device_type": "router",
    "ip_address": "192.168.1.1",
    "location": "POP-01",
    "online_at": "2024-01-15T10:30:00Z"
  }
}
```

#### device.offline

Network device went offline.

```json
{
  "type": "device.offline",
  "data": {
    "device_id": "dev_123",
    "device_type": "router",
    "last_seen": "2024-01-15T10:25:00Z",
    "offline_at": "2024-01-15T10:30:00Z"
  }
}
```

#### network.outage_detected

Network outage detected in area.

```json
{
  "type": "network.outage_detected",
  "data": {
    "outage_id": "out_123",
    "affected_area": "Zone-A",
    "affected_customers": 150,
    "detected_at": "2024-01-15T10:30:00Z",
    "estimated_restoration": "2024-01-15T12:00:00Z"
  }
}
```

#### network.outage_resolved

Network outage resolved.

```json
{
  "type": "network.outage_resolved",
  "data": {
    "outage_id": "out_123",
    "resolution_time": "2024-01-15T11:45:00Z",
    "downtime_minutes": 75,
    "root_cause": "fiber_cut"
  }
}
```

#### bandwidth.threshold_exceeded

Customer exceeded bandwidth threshold.

```json
{
  "type": "bandwidth.threshold_exceeded",
  "data": {
    "customer_id": "cust_123",
    "service_id": "svc_123",
    "threshold_gb": 1000,
    "current_usage_gb": 1050,
    "billing_period": "2024-01"
  }
}
```

### 🎫 Support Events

#### ticket.created

New support ticket created.

```json
{
  "type": "ticket.created",
  "data": {
    "ticket_id": "tkt_123",
    "customer_id": "cust_123",
    "priority": "high",
    "category": "network_issue",
    "subject": "Internet connection down",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### ticket.assigned

Ticket assigned to support agent.

```json
{
  "type": "ticket.assigned",
  "data": {
    "ticket_id": "tkt_123",
    "assigned_to": "agent_456",
    "assigned_at": "2024-01-15T10:35:00Z",
    "sla_deadline": "2024-01-15T14:30:00Z"
  }
}
```

#### ticket.resolved

Support ticket resolved.

```json
{
  "type": "ticket.resolved",
  "data": {
    "ticket_id": "tkt_123",
    "resolved_by": "agent_456",
    "resolution_time_minutes": 45,
    "resolution_notes": "Router reset resolved the issue",
    "resolved_at": "2024-01-15T11:15:00Z"
  }
}
```

#### ticket.escalated

Ticket escalated to higher tier.

```json
{
  "type": "ticket.escalated",
  "data": {
    "ticket_id": "tkt_123",
    "escalation_level": 2,
    "escalation_reason": "complex_technical_issue",
    "escalated_to": "tier2_team",
    "escalated_at": "2024-01-15T11:00:00Z"
  }
}
```

### 📊 Analytics Events

#### report.generated

Scheduled report generated.

```json
{
  "type": "report.generated",
  "data": {
    "report_id": "rpt_123",
    "report_type": "monthly_revenue",
    "period": "2024-01",
    "download_url": "https://api.dotmac.com/reports/rpt_123",
    "expires_at": "2024-02-15T00:00:00Z"
  }
}
```

#### alert.triggered

Analytics alert triggered.

```json
{
  "type": "alert.triggered",
  "data": {
    "alert_id": "alt_123",
    "alert_name": "High Churn Rate",
    "metric": "churn_rate",
    "threshold": 5.0,
    "current_value": 7.2,
    "triggered_at": "2024-01-15T10:30:00Z"
  }
}
```

## Retry Policy

Failed webhook deliveries are retried with exponential backoff:

- Attempt 1: Immediate
- Attempt 2: 1 minute
- Attempt 3: 5 minutes
- Attempt 4: 30 minutes
- Attempt 5: 2 hours
- Attempt 6: 6 hours
- Attempt 7: 24 hours

After 7 failed attempts, the webhook is marked as failed and notifications stop.

## Error Handling

### Response Codes

Your webhook endpoint should return:

- `200 OK` - Event processed successfully
- `202 Accepted` - Event received and will be processed asynchronously
- `400 Bad Request` - Event data is invalid (webhook will not be retried)
- `401 Unauthorized` - Authentication failed (webhook will not be retried)
- `500+ Server Error` - Temporary failure (webhook will be retried)

### Idempotency

Each event includes a unique `id` field. Store processed event IDs to handle duplicate deliveries:

```python
processed_events = set()

def handle_webhook(event):
    if event['id'] in processed_events:
        return  # Already processed

    # Process event
    process_event(event)
    processed_events.add(event['id'])
```

## Testing Webhooks

### Test Mode

Enable test mode to receive test events:

```json
POST /api/v1/webhooks/test
{
  "endpoint_id": "whk_123",
  "event_type": "customer.created"
}
```

### Webhook Logs

View webhook delivery logs:

```json
GET /api/v1/webhooks/endpoints/{endpoint_id}/logs
```

Response:

```json
{
  "logs": [
    {
      "event_id": "evt_123",
      "event_type": "customer.created",
      "status": "delivered",
      "attempts": 1,
      "delivered_at": "2024-01-15T10:30:05Z",
      "response_code": 200,
      "response_time_ms": 245
    }
  ]
}
```

## Best Practices

1. **Verify Signatures**: Always verify webhook signatures to ensure authenticity
2. **Respond Quickly**: Return a response within 5 seconds; process asynchronously if needed
3. **Handle Duplicates**: Implement idempotency to handle duplicate deliveries
4. **Monitor Failures**: Set up alerts for webhook failures
5. **Use HTTPS**: Always use HTTPS endpoints for security
6. **Log Events**: Log all received events for debugging
7. **Graceful Degradation**: Handle webhook failures without affecting your service

## Code Examples

### Python (Flask)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "your-webhook-secret"

@app.route('/webhooks/dotmac', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-DotMac-Signature')
    if not verify_signature(request.data, signature, WEBHOOK_SECRET):
        return jsonify({'error': 'Invalid signature'}), 401

    # Parse event
    event = request.json

    # Process based on event type
    if event['type'] == 'customer.created':
        handle_customer_created(event['data'])
    elif event['type'] == 'invoice.paid':
        handle_invoice_paid(event['data'])
    # ... handle other events

    return jsonify({'status': 'success'}), 200

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Node.js (Express)

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
const WEBHOOK_SECRET = 'your-webhook-secret';

app.post('/webhooks/dotmac', express.raw({type: 'application/json'}), (req, res) => {
  // Verify signature
  const signature = req.headers['x-dotmac-signature'];
  if (!verifySignature(req.body, signature, WEBHOOK_SECRET)) {
    return res.status(401).json({error: 'Invalid signature'});
  }

  // Parse event
  const event = JSON.parse(req.body);

  // Process based on event type
  switch(event.type) {
    case 'customer.created':
      handleCustomerCreated(event.data);
      break;
    case 'invoice.paid':
      handleInvoicePaid(event.data);
      break;
    // ... handle other events
  }

  res.json({status: 'success'});
});

function verifySignature(payload, signature, secret) {
  const expected = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}
```

## Support

For webhook-related support:

- Documentation: <https://docs.dotmac.com/webhooks>
- API Status: <https://status.dotmac.com>
- Support: <webhooks@dotmac.com>
