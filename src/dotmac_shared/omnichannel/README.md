# DotMac Omnichannel Communication Service

A comprehensive, multi-tenant omnichannel communication platform for the DotMac framework, providing unified customer interaction management across multiple communication channels with intelligent routing, agent management, and real-time analytics.

## 🌟 Features

### Multi-Channel Communication

- **Email Integration**: Professional email communication with templates and tracking
- **SMS/WhatsApp**: Mobile messaging with delivery confirmations
- **Social Media**: Twitter, Facebook, LinkedIn integration
- **Voice/VoIP**: Call management and recording
- **Live Chat**: Website chat widgets and chatbots
- **Custom Channels**: Extensible plugin system for custom integrations

### Intelligent Routing & Orchestration

- **Smart Routing**: Rule-based routing with customer context, priority, and agent skills
- **Load Balancing**: Distribute conversations across available agents
- **Escalation Management**: Automatic escalation based on SLA breaches
- **Queue Management**: Sophisticated queuing with priority handling
- **Context Preservation**: Maintain conversation context across channel switches

### Agent Workforce Management

- **Team Management**: Hierarchical team structures with role-based access
- **Skill-Based Routing**: Match customer needs with agent expertise
- **Availability Management**: Real-time status tracking and scheduling
- **Performance Analytics**: KPIs, response times, customer satisfaction
- **Workload Distribution**: Balanced assignment based on capacity

### Customer Experience

- **Unified History**: Complete conversation history across all channels
- **Customer Profiles**: Rich customer context with communication preferences
- **Multi-Contact Support**: Handle multiple contacts per customer account
- **Channel Preferences**: Respect customer communication preferences
- **Conversation Threading**: Maintain context across interactions

## 🏗️ Architecture

```
dotmac_shared/omnichannel/
├── core/                           # Core business logic
│   ├── interaction_manager.py      # Central interaction orchestration
│   ├── routing_engine.py          # Intelligent routing algorithms
│   ├── agent_manager.py           # Agent workload and availability
│   ├── channel_orchestrator.py    # Multi-channel coordination
│   └── workflow_engine.py         # Conversation workflow automation
├── models/                         # Data models
│   ├── interactions.py            # Interaction and conversation models
│   ├── customers.py               # Customer and contact models
│   ├── agents.py                  # Agent and team models
│   ├── channels.py                # Channel configuration models
│   └── analytics.py               # Analytics and reporting models
├── channels/                       # Channel implementations
│   ├── base.py                    # Base channel interface
│   ├── email_channel.py           # Email communication
│   ├── sms_channel.py             # SMS/WhatsApp messaging
│   ├── social_channel.py          # Social media integration
│   ├── voice_channel.py           # Voice/VoIP handling
│   └── webhook_channel.py         # Generic webhook integration
├── routing/                        # Routing implementations
│   ├── rule_engine.py             # Rule-based routing
│   ├── skill_matcher.py           # Agent skill matching
│   ├── load_balancer.py           # Load distribution
│   └── escalation_manager.py      # Escalation workflows
├── analytics/                      # Analytics and reporting
│   ├── metrics_collector.py       # Real-time metrics
│   ├── dashboard_service.py       # Dashboard data aggregation
│   ├── performance_analyzer.py    # Agent/channel performance
│   └── sla_monitor.py             # SLA tracking and alerting
├── integrations/                   # External service integrations
│   ├── crm_integration.py         # CRM system sync
│   ├── notification_service.py    # Alert and notification
│   └── audit_integration.py       # Audit trail integration
├── workflows/                      # Automation workflows
│   ├── conversation_flows.py      # Conversation automation
│   ├── escalation_flows.py        # Escalation automation
│   └── notification_flows.py      # Notification workflows
├── schemas/                        # API contracts
│   ├── interaction_schemas.py     # Interaction models
│   ├── agent_schemas.py           # Agent management models
│   ├── channel_schemas.py         # Channel configuration
│   └── analytics_schemas.py       # Analytics data models
├── templates/                      # Configuration templates
│   ├── channel_config.yaml.j2     # Channel configurations
│   ├── routing_rules.yaml.j2      # Routing rule templates
│   └── workflow_config.yaml.j2    # Workflow definitions
└── tests/                         # Comprehensive test suite
    ├── test_interaction_manager.py
    ├── test_routing_engine.py
    ├── test_channel_plugins.py
    └── test_analytics.py
```

## 🚀 Quick Start

### Installation

```bash
cd /home/dotmac_framework/src/dotmac_shared/omnichannel
pip install -e .
```

### Basic Usage

```python
from dotmac_shared.omnichannel import (
    InteractionManager,
    RoutingEngine,
    ChannelOrchestrator,
    AgentManager
)

# Initialize core components
interaction_manager = InteractionManager()
routing_engine = RoutingEngine()
channel_orchestrator = ChannelOrchestrator()
agent_manager = AgentManager()

# Create a customer interaction
interaction = await interaction_manager.create_interaction(
    customer_id="customer_123",
    channel="email",
    content="I need help with my service",
    priority="high"
)

# Route to appropriate agent
agent = await routing_engine.route_interaction(interaction)

# Send response
await channel_orchestrator.send_response(
    interaction_id=interaction.id,
    agent_id=agent.id,
    content="Hello! I'd be happy to help you with your service.",
    channel="email"
)
```

### Channel Plugin Configuration

```yaml
# config/omnichannel_channels.yml
channels:
  email:
    provider: "sendgrid"
    config:
      api_key: "${SENDGRID_API_KEY}"
      from_email: "support@company.com"
      templates:
        welcome: "d-1234567890abcdef"
        followup: "d-abcdef1234567890"

  sms:
    provider: "twilio"
    config:
      account_sid: "${TWILIO_ACCOUNT_SID}"
      auth_token: "${TWILIO_AUTH_TOKEN}"
      from_phone: "+1234567890"

  social:
    provider: "social_multi"
    config:
      twitter:
        api_key: "${TWITTER_API_KEY}"
        api_secret: "${TWITTER_API_SECRET}"
      facebook:
        page_access_token: "${FACEBOOK_PAGE_TOKEN}"
```

## 🎯 Core Components

### Interaction Manager

Central orchestrator for all customer interactions:

```python
from dotmac_shared.omnichannel.core import InteractionManager

manager = InteractionManager()

# Create interaction
interaction = await manager.create_interaction(
    customer_id="cust_123",
    channel="email",
    content="Need billing help",
    metadata={"source_ip": "192.168.1.1"}
)

# Update interaction
await manager.update_interaction(
    interaction.id,
    status="in_progress",
    assigned_agent="agent_456"
)

# Close interaction
await manager.close_interaction(
    interaction.id,
    resolution="Issue resolved",
    satisfaction_rating=5
)
```

### Routing Engine

Intelligent routing based on rules, skills, and availability:

```python
from dotmac_shared.omnichannel.routing import RoutingEngine

engine = RoutingEngine()

# Configure routing rules
await engine.add_routing_rule({
    "condition": {
        "channel": "email",
        "priority": "high",
        "keywords": ["billing", "payment"]
    },
    "action": {
        "route_to_team": "billing_team",
        "escalate_after": "15m"
    }
})

# Route interaction
agent = await engine.route_interaction(interaction)
```

### Agent Manager

Comprehensive agent and team management:

```python
from dotmac_shared.omnichannel.core import AgentManager

agent_mgr = AgentManager()

# Update agent availability
await agent_mgr.update_agent_status(
    agent_id="agent_123",
    status="available",
    max_concurrent_interactions=5
)

# Get team performance
team_stats = await agent_mgr.get_team_performance(
    team_id="support_team",
    date_range=("2024-01-01", "2024-01-31")
)
```

### Channel Orchestrator

Multi-channel communication management:

```python
from dotmac_shared.omnichannel.core import ChannelOrchestrator

orchestrator = ChannelOrchestrator()

# Send message through appropriate channel
result = await orchestrator.send_message(
    interaction_id="int_123",
    channel="email",
    content="Thank you for contacting us...",
    template_id="support_response",
    template_vars={"customer_name": "John Doe"}
)

# Handle incoming message
await orchestrator.handle_incoming_message(
    channel="sms",
    from_number="+1234567890",
    content="I need help with my order",
    metadata={"carrier": "Verizon"}
)
```

## 📊 Analytics & Reporting

### Real-time Dashboard

```python
from dotmac_shared.omnichannel.analytics import DashboardService

dashboard = DashboardService()

# Get real-time stats
stats = await dashboard.get_real_time_stats(
    tenant_id="tenant_123"
)
# Returns: {
#   "active_interactions": 45,
#   "available_agents": 12,
#   "avg_response_time": 180,
#   "channel_distribution": {...}
# }

# Get agent performance
performance = await dashboard.get_agent_performance(
    agent_id="agent_123",
    period="last_30_days"
)
```

### SLA Monitoring

```python
from dotmac_shared.omnichannel.analytics import SLAMonitor

sla_monitor = SLAMonitor()

# Configure SLA rules
await sla_monitor.configure_sla(
    tenant_id="tenant_123",
    rules={
        "first_response": "2h",
        "resolution": "24h",
        "escalation": "4h"
    }
)

# Check SLA breaches
breaches = await sla_monitor.get_sla_breaches(
    date_range=("2024-01-01", "2024-01-31")
)
```

## 🔧 Configuration

### Environment Variables

```bash
# Channel Configurations
SENDGRID_API_KEY="your_sendgrid_key"
TWILIO_ACCOUNT_SID="your_twilio_sid"
TWILIO_AUTH_TOKEN="your_twilio_token"

# Database
OMNICHANNEL_DATABASE_URL="postgresql://user:pass@localhost/omnichannel"

# Redis Cache
OMNICHANNEL_REDIS_URL="redis://localhost:6379/2"

# Message Queue
OMNICHANNEL_CELERY_BROKER="redis://localhost:6379/3"

# External Integrations
CRM_API_ENDPOINT="https://api.crm-system.com/v1"
NOTIFICATION_SERVICE_URL="http://notifications:8000"
```

### Advanced Configuration

```python
from dotmac_shared.omnichannel.config import OmnichannelConfig

config = OmnichannelConfig(
    # Routing settings
    default_routing_strategy="skill_based",
    max_interaction_queue_size=1000,
    agent_timeout_minutes=30,

    # Performance settings
    enable_caching=True,
    cache_ttl_seconds=300,
    max_concurrent_interactions_per_agent=10,

    # SLA settings
    default_response_time_sla="2h",
    default_resolution_time_sla="24h",
    escalation_reminder_intervals=[30, 60, 120]  # minutes
)
```

## 🧪 Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=dotmac_shared.omnichannel --cov-report=html

# Run integration tests
pytest tests/ -m integration

# Run performance tests
pytest tests/ -m performance
```

## 🔗 Integration Examples

### ISP Framework Integration

```python
from dotmac_shared.omnichannel.integrations import ISPIntegration

# Initialize ISP integration
isp_integration = ISPIntegration(
    isp_api_url="http://isp-api:8000",
    tenant_mapping=tenant_mapping
)

# Sync customer data
await isp_integration.sync_customer_data(
    customer_id="cust_123",
    isp_customer_id="isp_456"
)
```

### CRM Integration

```python
from dotmac_shared.omnichannel.integrations import CRMIntegration

crm = CRMIntegration(
    crm_type="salesforce",
    api_endpoint="https://api.salesforce.com",
    credentials=crm_credentials
)

# Create case in CRM
case_id = await crm.create_case(
    interaction_id="int_123",
    customer_data=customer_data,
    case_type="support"
)
```

## 📈 Performance Features

- **Horizontal Scaling**: Distributed architecture with load balancing
- **Caching**: Multi-layer caching for high-performance operations
- **Async Processing**: Non-blocking operations with background tasks
- **Connection Pooling**: Efficient database and external API management
- **Rate Limiting**: Protect against abuse and ensure fair usage
- **Circuit Breakers**: Fault tolerance for external service calls

## 🔐 Security Features

- **Multi-Tenant Isolation**: Complete data separation per tenant
- **Encryption**: End-to-end encryption for sensitive communications
- **Audit Trail**: Complete interaction and agent activity logging
- **Access Control**: Role-based permissions for agents and administrators
- **Data Privacy**: GDPR/CCPA compliant data handling
- **Rate Limiting**: Protection against abuse and DOS attacks

## 📞 Support

For issues and questions:

- GitHub Issues: [omnichannel-service/issues](https://github.com/dotmac-framework/omnichannel-service/issues)
- Documentation: [docs.dotmac-framework.com/omnichannel-service](https://docs.dotmac-framework.com/omnichannel-service)
- Email: <support@dotmac-framework.com>

## 📜 License

MIT License - see LICENSE file for details.

---

**Built for enterprise-scale customer communication management** 🚀
