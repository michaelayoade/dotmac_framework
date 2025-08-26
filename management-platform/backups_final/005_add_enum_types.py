"""Add PostgreSQL enum types for status fields

Revision ID: 005_add_enum_types
Revises: 004_add_unique_constraints
Create Date: 2025-08-25 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_add_enum_types'
down_revision: Union[str, None] = '004_add_unique_constraints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    deployment_status_enum = postgresql.ENUM()
        'pending', 'provisioning', 'deploying', 'running', 'updating', 
        'stopping', 'stopped', 'failed', 'deleting', 'deleted',
        name='deploymentstatus'
    )
    deployment_status_enum.create(op.get_bind()
    
    cloud_provider_enum = postgresql.ENUM()
        'aws', 'azure', 'gcp', 'digitalocean', 'kubernetes',
        name='cloudprovider'
    )
    cloud_provider_enum.create(op.get_bind()
    
    resource_tier_enum = postgresql.ENUM()
        'micro', 'small', 'medium', 'large', 'xlarge',
        name='resourcetier'
    )
    resource_tier_enum.create(op.get_bind()
    
    deployment_event_type_enum = postgresql.ENUM()
        'created', 'started', 'completed', 'failed', 'cancelled', 
        'paused', 'resumed', 'rolled_back',
        name='deploymenteventtype'
    )
    deployment_event_type_enum.create(op.get_bind()
    
    plugin_status_enum = postgresql.ENUM()
        'active', 'inactive', 'deprecated', 'maintenance',
        name='pluginstatus'
    )
    plugin_status_enum.create(op.get_bind()
    
    license_tier_enum = postgresql.ENUM()
        'free', 'basic', 'premium', 'enterprise', 'custom',
        name='licensetier'
    )
    license_tier_enum.create(op.get_bind()
    
    license_status_enum = postgresql.ENUM()
        'trial', 'active', 'expired', 'suspended', 'cancelled',
        name='licensestatus'
    )
    license_status_enum.create(op.get_bind()
    
    subscription_status_enum = postgresql.ENUM()
        'trial', 'active', 'past_due', 'cancelled', 'unpaid', 'paused',
        name='subscriptionstatus'
    )
    subscription_status_enum.create(op.get_bind()
    
    pricing_plan_type_enum = postgresql.ENUM()
        'saas', 'on_premise', 'hybrid', 'custom',
        name='pricingplantype'
    )
    pricing_plan_type_enum.create(op.get_bind()
    
    invoice_status_enum = postgresql.ENUM()
        'draft', 'sent', 'paid', 'overdue', 'cancelled', 'refunded',
        name='invoicestatus'
    )
    invoice_status_enum.create(op.get_bind()
    
    payment_status_enum = postgresql.ENUM()
        'pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded',
        name='paymentstatus'
    )
    payment_status_enum.create(op.get_bind()
    
    commission_status_enum = postgresql.ENUM()
        'pending', 'calculated', 'paid', 'disputed', 'cancelled',
        name='commissionstatus'
    )
    commission_status_enum.create(op.get_bind()
    
    health_status_enum = postgresql.ENUM()
        'healthy', 'degraded', 'unhealthy', 'unknown',
        name='healthstatus'
    )
    health_status_enum.create(op.get_bind()
    
    alert_severity_enum = postgresql.ENUM()
        'info', 'warning', 'critical', 'error',
        name='alertseverity'
    )
    alert_severity_enum.create(op.get_bind()
    
    alert_status_enum = postgresql.ENUM()
        'active', 'acknowledged', 'resolved', 'suppressed',
        name='alertstatus'
    )
    alert_status_enum.create(op.get_bind()
    
    metric_type_enum = postgresql.ENUM()
        'counter', 'gauge', 'histogram', 'summary',
        name='metrictype'
    )
    metric_type_enum.create(op.get_bind()
    
    tenant_status_enum = postgresql.ENUM()
        'active', 'suspended', 'cancelled', 'pending_activation',
        name='tenantstatus'
    )
    tenant_status_enum.create(op.get_bind()

    # Convert existing string columns to use enum types
    # Users role field
    op.alter_column('users', 'role')
                   type_=postgresql.ENUM('admin', 'user', 'manager', name='userrole'),
                   postgresql_using='role::userrole')
    
    # Tenant invitations status field
    op.alter_column('tenant_invitations', 'status')
                   type_=postgresql.ENUM('pending', 'accepted', 'rejected', 'expired', name='invitationstatus'),
                   postgresql_using='status::invitationstatus')
    
    # Update tables to use enum types (this will be done in subsequent deployments)
    # For now, we've created the types for future use


def downgrade() -> None:
    # Revert columns back to string types
    op.alter_column('tenant_invitations', 'status')
                   type_=sa.String(50),
                   postgresql_using='status::text')
    
    op.alter_column('users', 'role')
                   type_=sa.String(50),
                   postgresql_using='role::text')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS tenantstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS metrictype CASCADE')
    op.execute('DROP TYPE IF EXISTS alertstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS alertseverity CASCADE')
    op.execute('DROP TYPE IF EXISTS healthstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS commissionstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS paymentstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS invoicestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS pricingplantype CASCADE')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS licensestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS licensetier CASCADE')
    op.execute('DROP TYPE IF EXISTS pluginstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS deploymenteventtype CASCADE')
    op.execute('DROP TYPE IF EXISTS resourcetier CASCADE')
    op.execute('DROP TYPE IF EXISTS cloudprovider CASCADE')
    op.execute('DROP TYPE IF EXISTS deploymentstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS invitationstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS userrole CASCADE')