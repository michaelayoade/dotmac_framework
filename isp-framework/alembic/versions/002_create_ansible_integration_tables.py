"""Create Ansible integration tables

Revision ID: 002_ansible_integration
Revises: 001_network_integration
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_ansible_integration'
down_revision = '001_network_integration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all Ansible integration tables."""
    
    # Create ansible playbooks table
    op.create_table(
        'ansible_playbooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('playbook_type', sa.String(50), nullable=False, index=True),
        sa.Column('version', sa.String(50), nullable=False, default='1.0'),
        sa.Column('playbook_content', sa.Text, nullable=False),
        sa.Column('playbook_variables', postgresql.JSON, nullable=True),
        sa.Column('requirements', postgresql.JSON, nullable=True),
        sa.Column('target_device_types', postgresql.JSON, nullable=True),
        sa.Column('target_vendors', postgresql.JSON, nullable=True),
        sa.Column('target_os_versions', postgresql.JSON, nullable=True),
        sa.Column('timeout_minutes', sa.Integer, default=30, nullable=False),
        sa.Column('max_parallel_hosts', sa.Integer, default=10, nullable=False),
        sa.Column('gather_facts', sa.Boolean, default=True, nullable=False),
        sa.Column('check_mode_enabled', sa.Boolean, default=False, nullable=False),
        sa.Column('syntax_validated', sa.Boolean, default=False, nullable=False),
        sa.Column('last_tested', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_results', postgresql.JSON, nullable=True),
        sa.Column('execution_count', sa.Integer, default=0, nullable=False),
        sa.Column('last_executed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('success_rate', sa.Integer, default=0, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('documentation', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(50), default='active', nullable=False, index=True),
        sa.Column('status_reason', sa.Text, nullable=True),
        sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create playbook executions table
    op.create_table(
        'playbook_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('playbook_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ansible_playbooks.id'), nullable=False, index=True),
        sa.Column('execution_id', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('job_name', sa.String(255), nullable=True),
        sa.Column('inventory_content', sa.Text, nullable=False),
        sa.Column('extra_variables', postgresql.JSON, nullable=True),
        sa.Column('limit_hosts', postgresql.JSON, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('skip_tags', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(20), default='pending', nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('stdout_log', sa.Text, nullable=True),
        sa.Column('stderr_log', sa.Text, nullable=True),
        sa.Column('return_code', sa.Integer, nullable=True),
        sa.Column('total_hosts', sa.Integer, default=0, nullable=False),
        sa.Column('successful_hosts', sa.Integer, default=0, nullable=False),
        sa.Column('failed_hosts', sa.Integer, default=0, nullable=False),
        sa.Column('unreachable_hosts', sa.Integer, default=0, nullable=False),
        sa.Column('skipped_hosts', sa.Integer, default=0, nullable=False),
        sa.Column('host_results', postgresql.JSON, nullable=True),
        sa.Column('task_results', postgresql.JSON, nullable=True),
        sa.Column('changed_hosts', postgresql.JSON, nullable=True),
        sa.Column('triggered_by', sa.String(100), nullable=True),
        sa.Column('environment', sa.String(50), nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create device inventories table
    op.create_table(
        'device_inventories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('inventory_type', sa.String(50), nullable=False, index=True),
        sa.Column('inventory_content', sa.Text, nullable=True),
        sa.Column('inventory_script', sa.Text, nullable=True),
        sa.Column('update_interval', sa.Integer, nullable=True),
        sa.Column('group_variables', postgresql.JSON, nullable=True),
        sa.Column('host_variables', postgresql.JSON, nullable=True),
        sa.Column('auto_discovery_enabled', sa.Boolean, default=False, nullable=False),
        sa.Column('discovery_filters', postgresql.JSON, nullable=True),
        sa.Column('last_validated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validation_errors', postgresql.JSON, nullable=True),
        sa.Column('host_count', sa.Integer, default=0, nullable=False),
        sa.Column('reachable_hosts', sa.Integer, default=0, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(50), default='active', nullable=False, index=True),
        sa.Column('status_reason', sa.Text, nullable=True),
        sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create configuration templates table
    op.create_table(
        'configuration_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('playbook_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ansible_playbooks.id'), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('template_type', sa.String(50), nullable=False, index=True),
        sa.Column('device_type', sa.String(50), nullable=True, index=True),
        sa.Column('vendor', sa.String(100), nullable=True, index=True),
        sa.Column('template_content', sa.Text, nullable=False),
        sa.Column('default_variables', postgresql.JSON, nullable=True),
        sa.Column('required_variables', postgresql.JSON, nullable=True),
        sa.Column('validation_schema', postgresql.JSON, nullable=True),
        sa.Column('syntax_validated', sa.Boolean, default=False, nullable=False),
        sa.Column('last_validated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validation_errors', postgresql.JSON, nullable=True),
        sa.Column('usage_count', sa.Integer, default=0, nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('documentation', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(50), default='active', nullable=False, index=True),
        sa.Column('status_reason', sa.Text, nullable=True),
        sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create automation tasks table
    op.create_table(
        'automation_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('playbook_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ansible_playbooks.id'), nullable=False, index=True),
        sa.Column('inventory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('device_inventories.id'), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('task_type', sa.String(50), nullable=False, index=True),
        sa.Column('schedule_enabled', sa.Boolean, default=False, nullable=False),
        sa.Column('schedule_cron', sa.String(100), nullable=True),
        sa.Column('schedule_timezone', sa.String(50), default='UTC', nullable=False),
        sa.Column('trigger_events', postgresql.JSON, nullable=True),
        sa.Column('trigger_conditions', postgresql.JSON, nullable=True),
        sa.Column('max_concurrent_executions', sa.Integer, default=1, nullable=False),
        sa.Column('retry_count', sa.Integer, default=0, nullable=False),
        sa.Column('retry_delay_minutes', sa.Integer, default=5, nullable=False),
        sa.Column('task_variables', postgresql.JSON, nullable=True),
        sa.Column('notification_settings', postgresql.JSON, nullable=True),
        sa.Column('last_execution_id', sa.String(100), nullable=True),
        sa.Column('last_executed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', sa.String(20), nullable=True),
        sa.Column('execution_count', sa.Integer, default=0, nullable=False),
        sa.Column('success_count', sa.Integer, default=0, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(50), default='active', nullable=False, index=True),
        sa.Column('status_reason', sa.Text, nullable=True),
        sa.Column('status_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create indexes for better performance
    op.create_index('ix_ansible_playbooks_tenant_name', 'ansible_playbooks', ['tenant_id', 'name'], unique=True)
    op.create_index('ix_playbook_executions_playbook_status', 'playbook_executions', ['playbook_id', 'status'])
    op.create_index('ix_playbook_executions_created_status', 'playbook_executions', ['created_at', 'status'])
    op.create_index('ix_device_inventories_tenant_name', 'device_inventories', ['tenant_id', 'name'], unique=True)
    op.create_index('ix_configuration_templates_device_vendor', 'configuration_templates', ['device_type', 'vendor'])
    op.create_index('ix_automation_tasks_tenant_name', 'automation_tasks', ['tenant_id', 'name'], unique=True)


def downgrade() -> None:
    """Drop all Ansible integration tables."""
    
    # Drop indexes first
    op.drop_index('ix_automation_tasks_tenant_name')
    op.drop_index('ix_configuration_templates_device_vendor')
    op.drop_index('ix_device_inventories_tenant_name')
    op.drop_index('ix_playbook_executions_created_status')
    op.drop_index('ix_playbook_executions_playbook_status')
    op.drop_index('ix_ansible_playbooks_tenant_name')
    
    # Drop tables in reverse order of creation to handle foreign key constraints
    op.drop_table('automation_tasks')
    op.drop_table('configuration_templates')
    op.drop_table('device_inventories')
    op.drop_table('playbook_executions')
    op.drop_table('ansible_playbooks')