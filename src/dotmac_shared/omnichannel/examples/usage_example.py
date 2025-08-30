"""
Omnichannel Service Usage Example

Demonstrates how to use the omnichannel service with the DotMac plugin system
for managing customer interactions across multiple communication channels.

Author: DotMac Framework Team
License: MIT
"""

import asyncio
from datetime import datetime
from uuid import uuid4

# Note: This example shows the intended usage pattern
# Actual imports would work when the full DotMac environment is available


async def omnichannel_usage_example():
    """Example usage of omnichannel service"""

    try:
        # Import omnichannel components (commented for standalone example)
        # from dotmac_shared.omnichannel import (
        #     ChannelOrchestrator,
        #     InteractionManager,
        #     RoutingEngine,
        #     AgentManager,
        #     ChannelType
        # )
        # from dotmac_shared.omnichannel.plugins import create_twilio_sms_plugin

        # 1. Initialize core components
        tenant_id = uuid4()

        # Initialize components (pseudo-code)
        # channel_orchestrator = ChannelOrchestrator(tenant_id)
        # interaction_manager = InteractionManager(tenant_id)
        # routing_engine = RoutingEngine(tenant_id)
        # agent_manager = AgentManager(tenant_id)

        # 2. Configure communication channels via plugin system
        twilio_config = {
            "account_sid": "AC1234567890abcdef",
            "auth_token": "your_auth_token_here",
            "from_number": "+1234567890",
            "webhook_url": "https://your-app.com/webhooks/twilio",
            "max_concurrent_messages": 100,
            "rate_limit_per_minute": 60,
        }

        # Create and register Twilio SMS plugin
        # twilio_plugin = create_twilio_sms_plugin(twilio_config)
        # await channel_orchestrator.initialize()

        # 3. Create customer interaction
        customer_id = uuid4()
        interaction_data = {
            "customer_id": customer_id,
            "channel": "email",  # ChannelType.EMAIL
            "subject": "Service Inquiry",
            "content": "I need help with my internet service setup",
            "priority": "high",
            "source": "customer_portal",
        }

        # Create interaction
        # interaction = await interaction_manager.create_interaction(**interaction_data)

        # 4. Route interaction to available agent
        # available_agents = await agent_manager.get_available_agents(
        #     channel="email",
        #     skills=["technical_support", "internet_service"]
        # )

        # if available_agents:
        #     agent = available_agents[0]
        #     routing_result = await routing_engine.assign_interaction(
        #         interaction.id,
        #         agent.id
        #     )
        #     print(f"👨‍💼 Routed interaction to agent {agent.full_name}")

        # 5. Send response via appropriate channel
        response_data = {
            "interaction_id": uuid4(),  # interaction.id
            "channel": "email",  # ChannelType.EMAIL
            "recipient": "customer@example.com",
            "subject": "Re: Service Inquiry",
            "content": "Hello! Thank you for contacting us. I'll help you with your internet service setup.",
            "agent_id": uuid4(),
            "template_id": "support_response",
        }

        # Send response
        # message_result = await channel_orchestrator.send_message(**response_data)
        # if message_result.success:
        #     print(f"📧 Response sent successfully: {message_result.message_id}")
        # else:
        #     print(f"❌ Failed to send response: {message_result.failure_reason}")

        # 6. Monitor plugin status
        # plugin_status = await channel_orchestrator.get_plugin_status()
        # for plugin_id, status in plugin_status.items():
        #     print(f"🔌 Plugin {plugin_id}: {status['health_status']['status']}")

        # 7. Get channel statistics
        # stats = await channel_orchestrator.get_channel_statistics()
        # for channel_type, channel_stats in stats.items():
        #     print(f"📊 {channel_type}: {channel_stats['success_rate']:.1f}% success rate")

    except Exception as e:
        import traceback

        traceback.print_exc()


def show_architecture_overview():
    """Display architecture overview"""
    print(
        """
    Plugin System Integration:
    ┌─────────────────────────────────────────┐
    │         Channel Orchestrator            │
    │  ┌─────────────────────────────────────┐ │
    │  │    Omnichannel Plugin Manager       │ │
    │  │  ┌─────────────────────────────────┐ │ │
    │  │  │     DotMac Plugin System        │ │ │
    │  │  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌───┐ │ │ │
    │  │  │  │ SMS │ │Email│ │Voice│ │...│ │ │ │
    │  │  │  └─────┘ └─────┘ └─────┘ └───┘ │ │ │
    │  │  └─────────────────────────────────┘ │ │
    │  └─────────────────────────────────────┘ │
    └─────────────────────────────────────────┘

    Core Components:
    • InteractionManager: Customer interaction lifecycle
    • RoutingEngine: Intelligent agent assignment
    • AgentManager: Workforce and capacity management
    • ChannelOrchestrator: Multi-channel coordination

    Plugin Integration Benefits:
    • Automatic plugin discovery from registry
    • Hot-reloading of communication plugins
    • Health monitoring and status reporting
    • Tenant-specific plugin configurations
    • Rate limiting and capacity management
    """
    )


if __name__ == "__main__":
    """Run the example"""

    # Show architecture overview
    show_architecture_overview()

    # Run usage example
    asyncio.run(omnichannel_usage_example())
