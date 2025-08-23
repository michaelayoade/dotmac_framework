"""Add omnichannel module tables

Revision ID: 004_omnichannel
Revises: 003_create_identity_tables
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_omnichannel'
down_revision = '003_create_identity_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create enums
    contact_type_enum = sa.Enum('PRIMARY', 'BILLING', 'TECHNICAL', 'EMERGENCY', 'SALES', 'SUPPORT', 'EXECUTIVE', name='contacttype')
    interaction_type_enum = sa.Enum('INBOUND', 'OUTBOUND', 'INTERNAL', 'SYSTEM', name='interactiontype')
    interaction_status_enum = sa.Enum('PENDING', 'IN_PROGRESS', 'WAITING_CUSTOMER', 'COMPLETED', 'FAILED', 'CANCELLED', name='interactionstatus')
    agent_status_enum = sa.Enum('AVAILABLE', 'BUSY', 'AWAY', 'OFFLINE', 'IN_TRAINING', 'ON_BREAK', name='agentstatus')
    routing_strategy_enum = sa.Enum('ROUND_ROBIN', 'LEAST_BUSY', 'SKILL_BASED', 'PRIORITY_BASED', 'GEOGRAPHIC', 'CUSTOMER_HISTORY', name='routingstrategy')
    escalation_trigger_enum = sa.Enum('TIME_BASED', 'PRIORITY_BASED', 'KEYWORD_BASED', 'SENTIMENT_BASED', 'CUSTOMER_TIER', 'AGENT_REQUEST', name='escalationtrigger')
    
    contact_type_enum.create(op.get_bind())
    interaction_type_enum.create(op.get_bind())
    interaction_status_enum.create(op.get_bind())
    agent_status_enum.create(op.get_bind())
    routing_strategy_enum.create(op.get_bind())
    escalation_trigger_enum.create(op.get_bind())

    # 1. Registered Channels (Plugin Registry)
    op.create_table('omnichannel_registered_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', sa.String(50), nullable=False),
        sa.Column('channel_name', sa.String(100), nullable=False),
        sa.Column('plugin_class', sa.String(200), nullable=False),
        sa.Column('capabilities', postgresql.JSONB, default=list),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('configuration_schema', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 2. Channel Configurations
    op.create_table('omnichannel_channel_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_registered_channels.id'), nullable=False),
        sa.Column('configuration', postgresql.JSONB, default=dict),
        sa.Column('is_enabled', sa.Boolean, default=False),
        sa.Column('last_health_check', sa.DateTime),
        sa.Column('health_status', sa.String(20), default='unknown'),
        sa.Column('error_message', sa.Text),
        sa.Column('total_messages_sent', sa.Integer, default=0),
        sa.Column('total_messages_failed', sa.Integer, default=0),
        sa.Column('average_response_time', sa.Float, default=0.0),
        sa.Column('last_message_sent', sa.DateTime),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 3. Customer Contacts
    op.create_table('omnichannel_customer_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_type', contact_type_enum, nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200)),
        sa.Column('email_primary', sa.String(255)),
        sa.Column('phone_primary', sa.String(50)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_primary', sa.Boolean, default=False),
        sa.Column('preferred_language', sa.String(10), default='en'),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('allow_marketing', sa.Boolean, default=False),
        sa.Column('allow_notifications', sa.Boolean, default=True),
        sa.Column('quiet_hours_start', sa.String(8)),
        sa.Column('quiet_hours_end', sa.String(8)),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 4. Contact Communication Channels
    op.create_table('omnichannel_contact_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_customer_contacts.id'), nullable=False),
        sa.Column('registered_channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_registered_channels.id'), nullable=False),
        sa.Column('channel_address', sa.String(500), nullable=False),
        sa.Column('channel_display_name', sa.String(200)),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('is_preferred', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('channel_metadata', postgresql.JSONB, default=dict),
        sa.Column('opt_in_marketing', sa.Boolean, default=False),
        sa.Column('opt_in_notifications', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 5. Agents
    op.create_table('omnichannel_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', sa.String(50)),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('status', agent_status_enum, default='OFFLINE'),
        sa.Column('max_concurrent_interactions', sa.Integer, default=5),
        sa.Column('current_workload', sa.Integer, default=0),
        sa.Column('channel_skills', postgresql.JSONB, default=dict),
        sa.Column('language_skills', postgresql.JSONB, default=list),
        sa.Column('department_skills', postgresql.JSONB, default=list),
        sa.Column('total_interactions', sa.Integer, default=0),
        sa.Column('total_interactions_resolved', sa.Integer, default=0),
        sa.Column('average_response_time', sa.Float, default=0.0),
        sa.Column('average_resolution_time', sa.Float, default=0.0),
        sa.Column('customer_satisfaction', sa.Float, default=0.0),
        sa.Column('work_schedule', postgresql.JSONB, default=dict),
        sa.Column('timezone', sa.String(50), default='UTC'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 6. Agent Teams
    op.create_table('omnichannel_agent_teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('supported_channels', postgresql.JSONB, default=list),
        sa.Column('supported_languages', postgresql.JSONB, default=list),
        sa.Column('supported_departments', postgresql.JSONB, default=list),
        sa.Column('max_queue_size', sa.Integer, default=100),
        sa.Column('routing_strategy', routing_strategy_enum, default='ROUND_ROBIN'),
        sa.Column('operating_hours', postgresql.JSONB, default=dict),
        sa.Column('sla_response_minutes', sa.Integer, default=15),
        sa.Column('sla_resolution_minutes', sa.Integer, default=240),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 7. Agent Team Memberships
    op.create_table('omnichannel_agent_team_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id'), nullable=False),
        sa.Column('team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agent_teams.id'), nullable=False),
        sa.Column('is_team_lead', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('joined_at', sa.DateTime),
        sa.Column('specializations', postgresql.JSONB, default=list),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 8. Conversation Threads
    op.create_table('omnichannel_conversation_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_customer_contacts.id'), nullable=False),
        sa.Column('registered_channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_registered_channels.id'), nullable=False),
        sa.Column('thread_subject', sa.String(500)),
        sa.Column('thread_reference', sa.String(100), unique=True, nullable=False),
        sa.Column('first_interaction_at', sa.DateTime),
        sa.Column('last_interaction_at', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_resolved', sa.Boolean, default=False),
        sa.Column('priority_level', sa.Integer, default=3),
        sa.Column('tags', postgresql.JSONB, default=list),
        sa.Column('context_summary', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 9. Communication Interactions
    op.create_table('omnichannel_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interaction_reference', sa.String(100), unique=True, nullable=False),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_customer_contacts.id'), nullable=False),
        sa.Column('channel_info_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_contact_channels.id'), nullable=False),
        sa.Column('conversation_thread_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_conversation_threads.id')),
        sa.Column('interaction_type', interaction_type_enum, nullable=False),
        sa.Column('status', interaction_status_enum, default='PENDING'),
        sa.Column('subject', sa.String(500)),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_type', sa.String(50), default='text'),
        sa.Column('channel_message_id', sa.String(200)),
        sa.Column('channel_metadata', postgresql.JSONB, default=dict),
        sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id')),
        sa.Column('assigned_team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agent_teams.id')),
        sa.Column('priority_level', sa.Integer, default=3),
        sa.Column('interaction_start', sa.DateTime),
        sa.Column('first_response_time', sa.DateTime),
        sa.Column('resolution_time', sa.DateTime),
        sa.Column('sla_due_time', sa.DateTime),
        sa.Column('is_sla_breached', sa.Boolean, default=False),
        sa.Column('sentiment_score', sa.Float),
        sa.Column('satisfaction_rating', sa.Integer),
        sa.Column('tags', postgresql.JSONB, default=list),
        sa.Column('internal_notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 10. Routing Rules
    op.create_table('omnichannel_routing_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('priority', sa.Integer, default=5),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_registered_channels.id')),
        sa.Column('priority_condition', sa.Integer),
        sa.Column('customer_tier_condition', sa.String(50)),
        sa.Column('time_condition', postgresql.JSONB),
        sa.Column('keyword_conditions', postgresql.JSONB, default=list),
        sa.Column('language_condition', sa.String(10)),
        sa.Column('target_team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agent_teams.id')),
        sa.Column('target_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id')),
        sa.Column('priority_override', sa.Integer),
        sa.Column('sla_override_minutes', sa.Integer),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 11. Interaction Responses
    op.create_table('omnichannel_interaction_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_interactions.id'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('content_type', sa.String(50), default='text'),
        sa.Column('is_internal', sa.Boolean, default=False),
        sa.Column('channel_message_id', sa.String(200)),
        sa.Column('delivery_status', sa.String(50), default='pending'),
        sa.Column('delivery_timestamp', sa.DateTime),
        sa.Column('delivery_metadata', postgresql.JSONB, default=dict),
        sa.Column('response_time_seconds', sa.Integer),
        sa.Column('attachments', postgresql.JSONB, default=list),
        sa.Column('template_used', sa.String(100)),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 12. Interaction Escalations
    op.create_table('omnichannel_interaction_escalations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_interactions.id'), nullable=False),
        sa.Column('escalation_level', sa.Integer, nullable=False),
        sa.Column('trigger_type', escalation_trigger_enum, nullable=False),
        sa.Column('trigger_reason', sa.Text, nullable=False),
        sa.Column('escalated_from_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id')),
        sa.Column('escalated_to_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id')),
        sa.Column('escalated_to_team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agent_teams.id')),
        sa.Column('escalated_at', sa.DateTime),
        sa.Column('resolved_at', sa.DateTime),
        sa.Column('is_resolved', sa.Boolean, default=False),
        sa.Column('escalation_notes', sa.Text),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 13. Agent Performance Metrics
    op.create_table('omnichannel_agent_performance_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_agents.id'), nullable=False),
        sa.Column('metric_date', sa.DateTime, nullable=False),
        sa.Column('total_interactions', sa.Integer, default=0),
        sa.Column('interactions_resolved', sa.Integer, default=0),
        sa.Column('interactions_escalated', sa.Integer, default=0),
        sa.Column('average_response_time_minutes', sa.Float, default=0.0),
        sa.Column('average_resolution_time_minutes', sa.Float, default=0.0),
        sa.Column('customer_satisfaction_average', sa.Float, default=0.0),
        sa.Column('customer_satisfaction_count', sa.Integer, default=0),
        sa.Column('sla_breaches', sa.Integer, default=0),
        sa.Column('online_time_minutes', sa.Integer, default=0),
        sa.Column('active_time_minutes', sa.Integer, default=0),
        sa.Column('utilization_percentage', sa.Float, default=0.0),
        sa.Column('channel_metrics', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # 14. Channel Analytics
    op.create_table('omnichannel_channel_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('registered_channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('omnichannel_registered_channels.id'), nullable=False),
        sa.Column('metric_date', sa.DateTime, nullable=False),
        sa.Column('total_interactions', sa.Integer, default=0),
        sa.Column('inbound_interactions', sa.Integer, default=0),
        sa.Column('outbound_interactions', sa.Integer, default=0),
        sa.Column('average_response_time_minutes', sa.Float, default=0.0),
        sa.Column('average_resolution_time_minutes', sa.Float, default=0.0),
        sa.Column('customer_satisfaction_average', sa.Float, default=0.0),
        sa.Column('customer_satisfaction_count', sa.Integer, default=0),
        sa.Column('plugin_uptime_percentage', sa.Float, default=0.0),
        sa.Column('plugin_error_count', sa.Integer, default=0),
        sa.Column('message_delivery_rate', sa.Float, default=0.0),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('deleted_at', sa.DateTime),
        sa.Column('is_deleted', sa.Boolean, default=False),
    )
    
    # CREATE INDEXES FOR PERFORMANCE
    
    # Registered Channels indexes
    op.create_index('uq_registered_channel_tenant_channel', 'omnichannel_registered_channels', ['tenant_id', 'channel_id'], unique=True)
    op.create_index('ix_registered_channel_tenant', 'omnichannel_registered_channels', ['tenant_id'])
    op.create_index('ix_registered_channel_active', 'omnichannel_registered_channels', ['is_active'])
    
    # Channel Configuration indexes
    op.create_index('uq_channel_config_tenant_channel', 'omnichannel_channel_configurations', ['tenant_id', 'channel_id'], unique=True)
    op.create_index('ix_channel_config_tenant', 'omnichannel_channel_configurations', ['tenant_id'])
    op.create_index('ix_channel_config_enabled', 'omnichannel_channel_configurations', ['is_enabled'])
    op.create_index('ix_channel_config_health', 'omnichannel_channel_configurations', ['health_status'])
    
    # Customer Contact indexes  
    op.create_index('ix_customer_contact_customer', 'omnichannel_customer_contacts', ['customer_id'])
    op.create_index('ix_customer_contact_tenant', 'omnichannel_customer_contacts', ['tenant_id'])
    op.create_index('ix_customer_contact_primary', 'omnichannel_customer_contacts', ['is_primary'])
    op.create_index('ix_customer_contact_active', 'omnichannel_customer_contacts', ['is_active'])
    
    # Contact Channel indexes
    op.create_index('uq_contact_channel_address', 'omnichannel_contact_channels', ['contact_id', 'registered_channel_id', 'channel_address'], unique=True)
    op.create_index('ix_contact_channel_contact', 'omnichannel_contact_channels', ['contact_id'])
    op.create_index('ix_contact_channel_registered', 'omnichannel_contact_channels', ['registered_channel_id'])
    op.create_index('ix_contact_channel_verified', 'omnichannel_contact_channels', ['is_verified'])
    op.create_index('ix_contact_channel_active', 'omnichannel_contact_channels', ['is_active'])
    op.create_index('ix_contact_channel_preferred', 'omnichannel_contact_channels', ['is_preferred'])
    
    # Agent indexes
    op.create_index('uq_agent_tenant_user', 'omnichannel_agents', ['tenant_id', 'user_id'], unique=True)
    op.create_index('ix_agent_user', 'omnichannel_agents', ['user_id'])
    op.create_index('ix_agent_status', 'omnichannel_agents', ['status'])
    op.create_index('ix_agent_workload', 'omnichannel_agents', ['current_workload'])
    op.create_index('ix_agent_tenant', 'omnichannel_agents', ['tenant_id'])
    
    # Agent Team indexes
    op.create_index('ix_agent_team_active', 'omnichannel_agent_teams', ['is_active'])
    op.create_index('ix_agent_team_tenant', 'omnichannel_agent_teams', ['tenant_id'])
    
    # Agent Team Membership indexes
    op.create_index('uq_agent_team_membership', 'omnichannel_agent_team_memberships', ['tenant_id', 'agent_id', 'team_id'], unique=True)
    op.create_index('ix_agent_team_membership_agent', 'omnichannel_agent_team_memberships', ['agent_id'])
    op.create_index('ix_agent_team_membership_team', 'omnichannel_agent_team_memberships', ['team_id'])
    op.create_index('ix_agent_team_membership_active', 'omnichannel_agent_team_memberships', ['is_active'])
    
    # Conversation Thread indexes
    op.create_index('ix_conversation_contact', 'omnichannel_conversation_threads', ['contact_id'])
    op.create_index('ix_conversation_channel', 'omnichannel_conversation_threads', ['registered_channel_id'])
    op.create_index('ix_conversation_active', 'omnichannel_conversation_threads', ['is_active'])
    op.create_index('ix_conversation_resolved', 'omnichannel_conversation_threads', ['is_resolved'])
    op.create_index('ix_conversation_last_interaction', 'omnichannel_conversation_threads', ['last_interaction_at'])
    
    # Communication Interaction indexes (CRITICAL FOR PERFORMANCE)
    op.create_index('ix_interaction_contact', 'omnichannel_interactions', ['contact_id'])
    op.create_index('ix_interaction_channel', 'omnichannel_interactions', ['channel_info_id'])
    op.create_index('ix_interaction_thread', 'omnichannel_interactions', ['conversation_thread_id'])
    op.create_index('ix_interaction_agent', 'omnichannel_interactions', ['assigned_agent_id'])
    op.create_index('ix_interaction_team', 'omnichannel_interactions', ['assigned_team_id'])
    op.create_index('ix_interaction_status', 'omnichannel_interactions', ['status'])
    op.create_index('ix_interaction_priority', 'omnichannel_interactions', ['priority_level'])
    op.create_index('ix_interaction_tenant_status', 'omnichannel_interactions', ['tenant_id', 'status'])
    op.create_index('ix_interaction_sla_due', 'omnichannel_interactions', ['sla_due_time'])
    op.create_index('ix_interaction_created', 'omnichannel_interactions', ['created_at'])
    
    # Routing Rule indexes
    op.create_index('ix_routing_rule_active', 'omnichannel_routing_rules', ['is_active'])
    op.create_index('ix_routing_rule_priority', 'omnichannel_routing_rules', ['priority'])
    op.create_index('ix_routing_rule_channel', 'omnichannel_routing_rules', ['channel_id'])
    op.create_index('ix_routing_rule_tenant', 'omnichannel_routing_rules', ['tenant_id'])
    
    # Response indexes
    op.create_index('ix_response_interaction', 'omnichannel_interaction_responses', ['interaction_id'])
    op.create_index('ix_response_agent', 'omnichannel_interaction_responses', ['agent_id'])
    op.create_index('ix_response_delivery_status', 'omnichannel_interaction_responses', ['delivery_status'])
    op.create_index('ix_response_created', 'omnichannel_interaction_responses', ['created_at'])
    op.create_index('ix_response_tenant', 'omnichannel_interaction_responses', ['tenant_id'])
    
    # Escalation indexes
    op.create_index('ix_escalation_interaction', 'omnichannel_interaction_escalations', ['interaction_id'])
    op.create_index('ix_escalation_level', 'omnichannel_interaction_escalations', ['escalation_level'])
    op.create_index('ix_escalation_trigger', 'omnichannel_interaction_escalations', ['trigger_type'])
    op.create_index('ix_escalation_resolved', 'omnichannel_interaction_escalations', ['is_resolved'])
    op.create_index('ix_escalation_tenant', 'omnichannel_interaction_escalations', ['tenant_id'])
    
    # Performance Metric indexes
    op.create_index('uq_agent_metric_date', 'omnichannel_agent_performance_metrics', ['tenant_id', 'agent_id', 'metric_date'], unique=True)
    op.create_index('ix_agent_metric_agent', 'omnichannel_agent_performance_metrics', ['agent_id'])
    op.create_index('ix_agent_metric_date', 'omnichannel_agent_performance_metrics', ['metric_date'])
    op.create_index('ix_agent_metric_tenant', 'omnichannel_agent_performance_metrics', ['tenant_id'])
    
    # Channel Analytics indexes
    op.create_index('uq_channel_analytics_date', 'omnichannel_channel_analytics', ['tenant_id', 'registered_channel_id', 'metric_date'], unique=True)
    op.create_index('ix_channel_analytics_channel', 'omnichannel_channel_analytics', ['registered_channel_id'])
    op.create_index('ix_channel_analytics_date', 'omnichannel_channel_analytics', ['metric_date'])
    op.create_index('ix_channel_analytics_tenant', 'omnichannel_channel_analytics', ['tenant_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('omnichannel_channel_analytics')
    op.drop_table('omnichannel_agent_performance_metrics')
    op.drop_table('omnichannel_interaction_escalations')
    op.drop_table('omnichannel_interaction_responses')
    op.drop_table('omnichannel_routing_rules')
    op.drop_table('omnichannel_interactions')
    op.drop_table('omnichannel_conversation_threads')
    op.drop_table('omnichannel_agent_team_memberships')
    op.drop_table('omnichannel_agent_teams')
    op.drop_table('omnichannel_agents')
    op.drop_table('omnichannel_contact_channels')
    op.drop_table('omnichannel_customer_contacts')
    op.drop_table('omnichannel_channel_configurations')
    op.drop_table('omnichannel_registered_channels')
    
    # Drop enums
    sa.Enum(name='escalationtrigger').drop(op.get_bind())
    sa.Enum(name='routingstrategy').drop(op.get_bind())
    sa.Enum(name='agentstatus').drop(op.get_bind())
    sa.Enum(name='interactionstatus').drop(op.get_bind())
    sa.Enum(name='interactiontype').drop(op.get_bind())
    sa.Enum(name='contacttype').drop(op.get_bind())