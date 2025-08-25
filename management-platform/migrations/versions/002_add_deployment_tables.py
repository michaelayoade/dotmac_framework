"""Add deployment tables

Revision ID: 002_add_deployment_tables
Revises: 001_initial_schema
Create Date: 2024-08-22 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_deployment_tables'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create infrastructure_templates table first (referenced by deployments)
    op.create_table(
        'infrastructure_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('cloud_provider', sa.String(50), nullable=False),
        sa.Column('resource_tier', sa.String(50), nullable=False),
        sa.Column('cpu_cores', sa.Integer(), nullable=False),
        sa.Column('memory_gb', sa.Integer(), nullable=False),
        sa.Column('storage_gb', sa.Integer(), nullable=False),
        sa.Column('network_bandwidth_mbps', sa.Integer(), nullable=False),
        sa.Column('hourly_cost_cents', sa.Integer(), nullable=False),
        sa.Column('monthly_cost_cents', sa.Integer(), nullable=False),
        sa.Column('template_config', sa.JSON(), nullable=False),
        sa.Column('environment_variables', sa.JSON(), nullable=False, default=sa.text("'{}'::json")),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    
    # Create indexes for infrastructure_templates
    op.create_index('ix_infrastructure_templates_tenant_id', 'infrastructure_templates', ['tenant_id'])
    op.create_index('ix_infrastructure_templates_name', 'infrastructure_templates', ['name'])
    op.create_index('ix_infrastructure_templates_cloud_provider', 'infrastructure_templates', ['cloud_provider'])
    op.create_index('ix_infrastructure_templates_resource_tier', 'infrastructure_templates', ['resource_tier'])
    op.create_index('ix_infrastructure_templates_is_active', 'infrastructure_templates', ['is_active'])

    # Create deployments table
    op.create_table(
        'deployments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('infrastructure_template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('environment', sa.String(50), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['infrastructure_template_id'], ['infrastructure_templates.id'])
    )
    
    # Create service_instances table
    op.create_table(
        'service_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_name', sa.String(255), nullable=False),
        sa.Column('service_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('health_status', sa.String(50), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('endpoints', sa.JSON(), nullable=True),
        sa.Column('resource_usage', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ondelete='CASCADE')
    )
    
    # Create deployment_logs table
    op.create_table(
        'deployment_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('log_level', sa.String(50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('component', sa.String(255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('updated_by', sa.String(255), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('ix_deployments_tenant_id', 'deployments', ['tenant_id'])
    op.create_index('ix_deployments_status', 'deployments', ['status'])
    op.create_index('ix_deployments_environment', 'deployments', ['environment'])
    op.create_index('ix_service_instances_tenant_id', 'service_instances', ['tenant_id'])
    op.create_index('ix_service_instances_deployment_id', 'service_instances', ['deployment_id'])
    op.create_index('ix_service_instances_status', 'service_instances', ['status'])
    op.create_index('ix_deployment_logs_deployment_id', 'deployment_logs', ['deployment_id'])
    op.create_index('ix_deployment_logs_timestamp', 'deployment_logs', ['timestamp'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_deployment_logs_timestamp')
    op.drop_index('ix_deployment_logs_deployment_id')
    op.drop_index('ix_service_instances_status')
    op.drop_index('ix_service_instances_deployment_id')
    op.drop_index('ix_service_instances_tenant_id')
    op.drop_index('ix_deployments_environment')
    op.drop_index('ix_deployments_status')
    op.drop_index('ix_deployments_tenant_id')
    
    # Drop tables (in reverse order)
    op.drop_table('deployment_logs')
    op.drop_table('service_instances')
    op.drop_table('deployments')
    
    # Drop infrastructure_templates indexes and table
    op.drop_index('ix_infrastructure_templates_is_active')
    op.drop_index('ix_infrastructure_templates_resource_tier')
    op.drop_index('ix_infrastructure_templates_cloud_provider')
    op.drop_index('ix_infrastructure_templates_name')
    op.drop_index('ix_infrastructure_templates_tenant_id')
    op.drop_table('infrastructure_templates')