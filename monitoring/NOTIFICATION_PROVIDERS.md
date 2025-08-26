# Notification Providers Configuration Guide

This guide shows how to configure different notification providers with the DotMac monitoring system. **Choose only the providers you actually use** - there's no need to configure all of them.

## 📧 Email Notifications (Built-in)

Email is the most universal notification method and works with any SMTP server.

### Environment Variables:
```bash
SMTP_SMARTHOST=smtp.gmail.com:587
SMTP_FROM=alerts@yourdomain.com
SMTP_AUTH_USERNAME=your-email@gmail.com
SMTP_AUTH_PASSWORD=your-app-password
DEFAULT_EMAIL_TO=admin@yourdomain.com
CRITICAL_EMAIL_TO=oncall@yourdomain.com
```

### Popular SMTP Providers:
- **Gmail**: `smtp.gmail.com:587` (use app passwords)
- **Outlook**: `smtp-mail.outlook.com:587`
- **Yahoo**: `smtp.mail.yahoo.com:587`
- **SendGrid**: `smtp.sendgrid.net:587`
- **Mailgun**: `smtp.mailgun.org:587`

## 🔗 Webhook Notifications (Universal)

Webhooks work with almost any service and are the most flexible option.

### Environment Variables:
```bash
DEFAULT_WEBHOOK_URL=https://your-service.com/webhook
CRITICAL_WEBHOOK_URL=https://your-emergency-service.com/webhook
WEBHOOK_USERNAME=optional-basic-auth-username
WEBHOOK_PASSWORD=optional-basic-auth-password
```

### Compatible Services:
- **Discord**: Create webhook in channel settings
- **Microsoft Teams**: Create incoming webhook connector
- **Mattermost**: Create incoming webhook integration
- **Generic HTTP services**: Any endpoint that accepts POST requests

## 🚨 PagerDuty

For incident management and on-call scheduling.

### Setup:
1. Create integration in PagerDuty service
2. Get integration key
3. Configure webhook URL

### Environment Variables:
```bash
CRITICAL_WEBHOOK_URL=https://events.pagerduty.com/v2/enqueue
PAGERDUTY_INTEGRATION_KEY=your-integration-key
```

## 📱 OpsGenie

Alternative incident management platform.

### Environment Variables:
```bash
CRITICAL_WEBHOOK_URL=https://api.opsgenie.com/v2/alerts
OPSGENIE_API_KEY=your-api-key
```

## 💬 Discord

Popular for team communication.

### Setup:
1. Go to Discord channel → Settings → Integrations → Webhooks
2. Create new webhook
3. Copy webhook URL

### Environment Variables:
```bash
DEFAULT_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
```

## 🔔 Microsoft Teams

For Microsoft-centric organizations.

### Setup:
1. Go to Teams channel → Connectors → Incoming Webhook
2. Configure webhook name and image
3. Copy webhook URL

### Environment Variables:
```bash
DEFAULT_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR/WEBHOOK/URL
```

## 📞 SMS Notifications

Via webhook services like Twilio, AWS SNS, or similar.

### Twilio Example:
```bash
SMS_WEBHOOK_URL=https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT/Messages.json
SMS_USERNAME=your-account-sid
SMS_PASSWORD=your-auth-token
```

## 🤖 Telegram

For teams using Telegram.

### Setup:
1. Create bot with @BotFather
2. Get bot token
3. Add bot to group and get chat ID

### Environment Variables:
```bash
DEFAULT_WEBHOOK_URL=https://api.telegram.org/bot<BOT_TOKEN>/sendMessage
TELEGRAM_CHAT_ID=your-chat-id
```

## 📊 Custom Integrations

### Webhook Payload Format
Your webhook endpoints will receive JSON payloads like:
```json
{
  "alerts": [
    {
      "labels": {
        "alertname": "ServiceDown",
        "service": "isp-framework",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Service is down",
        "description": "ISP Framework has been down for 1 minute"
      },
      "status": "firing"
    }
  ]
}
```

### Custom Script Integration
You can also use webhook to trigger custom scripts:
```bash
# Create webhook handler script
#!/bin/bash
# /usr/local/bin/alert-handler.sh
curl -X POST "https://your-api.com/alerts" \
  -H "Content-Type: application/json" \
  -d "$@"

# Set webhook URL to your script
DEFAULT_WEBHOOK_URL=http://localhost:8080/webhook
```

## 🔧 Configuration Examples

### Minimal Setup (Email Only):
```bash
# .env.monitoring
SMTP_SMARTHOST=smtp.gmail.com:587
SMTP_FROM=alerts@yourdomain.com
SMTP_AUTH_USERNAME=your-email@gmail.com
SMTP_AUTH_PASSWORD=your-app-password
DEFAULT_EMAIL_TO=admin@yourdomain.com
```

### Multi-Channel Setup:
```bash
# .env.monitoring
# Email for regular alerts
SMTP_SMARTHOST=smtp.gmail.com:587
SMTP_FROM=alerts@yourdomain.com
SMTP_AUTH_USERNAME=your-email@gmail.com
SMTP_AUTH_PASSWORD=your-app-password
DEFAULT_EMAIL_TO=team@yourdomain.com

# Discord for team notifications
DEFAULT_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK

# PagerDuty for critical alerts
CRITICAL_WEBHOOK_URL=https://events.pagerduty.com/v2/enqueue
PAGERDUTY_INTEGRATION_KEY=your-integration-key
```

### High-Availability Setup:
```bash
# Multiple notification methods for redundancy
DEFAULT_EMAIL_TO=primary@yourdomain.com
CRITICAL_EMAIL_TO=oncall@yourdomain.com,backup@yourdomain.com

# Multiple webhook endpoints
DEFAULT_WEBHOOK_URL=https://primary-webhook.com/alerts
CRITICAL_WEBHOOK_URL=https://emergency-webhook.com/alerts

# SMS for critical alerts
SMS_WEBHOOK_URL=https://api.twilio.com/messages
SMS_USERNAME=your-twilio-sid
SMS_PASSWORD=your-twilio-token
```

## 🚀 Quick Start

1. **Choose your notification method(s)** from the options above
2. **Configure environment variables** in `monitoring/.env.monitoring`
3. **Test your configuration** by triggering a test alert
4. **Customize alert routing** in `alertmanager-flexible.yml` if needed

## ✅ Testing Your Configuration

```bash
# Test email configuration
echo "Test alert" | mail -s "Test Alert" admin@yourdomain.com

# Test webhook configuration
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test alert from DotMac monitoring"}'

# Trigger test alert in Prometheus
curl -X POST http://localhost:9090/api/v1/alerts
```

## 🔄 Switching Providers

The configuration is completely flexible. You can:
- Start with email only
- Add webhook notifications later
- Switch from one provider to another
- Use multiple providers simultaneously
- Disable any provider by simply removing its environment variables

Choose what works best for your team and infrastructure!