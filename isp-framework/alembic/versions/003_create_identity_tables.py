"""Create identity and customer tables

Revision ID: 003_create_identity_tables
Revises: 002_create_ansible_integration_tables
Create Date: 2025-08-21 09:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_create_identity_tables'
down_revision: Union[str, None] = '002_create_ansible_integration_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create identity and customer related tables."""
    
    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', sa.String(500), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False, default=False),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_roles_tenant_name'),
        sa.Index('ix_roles_tenant_id', 'tenant_id'),
        sa.Index('ix_roles_name', 'name'),
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Core user fields
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        
        # Profile fields
        sa.Column('timezone', sa.String(50), nullable=False, default='UTC'),
        sa.Column('language', sa.String(10), nullable=False, default='en'),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('last_login', sa.DateTime, nullable=True),
        
        # Contact information
        sa.Column('phone_primary', sa.String(20), nullable=True),
        sa.Column('phone_secondary', sa.String(20), nullable=True),
        
        sa.UniqueConstraint('tenant_id', 'username', name='uq_users_tenant_username'),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_users_tenant_email'),
        sa.Index('ix_users_tenant_id', 'tenant_id'),
        sa.Index('ix_users_username', 'username'),
        sa.Index('ix_users_email', 'email'),
    )
    
    # Create user_roles association table
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    # Create customers table
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Core customer fields
        sa.Column('customer_number', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('customer_type', sa.String(20), nullable=False),
        sa.Column('account_status', sa.String(20), nullable=False, default='pending'),
        
        # Contact information
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('company_name', sa.String(200), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        
        # Address information
        sa.Column('street_address', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        
        # Business fields
        sa.Column('credit_limit', sa.String(20), nullable=False, default='0.00'),
        sa.Column('payment_terms', sa.String(50), nullable=False, default='net_30'),
        sa.Column('installation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Portal integration
        sa.Column('portal_id', sa.String(20), nullable=True),
        
        # Relationships
        sa.Column('primary_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        
        sa.UniqueConstraint('tenant_id', 'customer_number', name='uq_customers_tenant_number'),
        sa.UniqueConstraint('portal_id', name='uq_customers_portal_id'),
        sa.Index('ix_customers_tenant_id', 'tenant_id'),
        sa.Index('ix_customers_customer_number', 'customer_number'),
        sa.Index('ix_customers_portal_id', 'portal_id'),
        sa.Index('ix_customers_email', 'email'),
    )
    
    # Create portal_accounts table (as part of customer module)
    op.create_table(
        'portal_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # Portal identification
        sa.Column('portal_id', sa.String(20), nullable=False, unique=True),
        sa.Column('account_type', sa.String(20), nullable=False, default='customer'),
        sa.Column('status', sa.String(20), nullable=False, default='pending_activation'),
        
        # Authentication
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('password_reset_token', sa.String(255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime, nullable=True),
        sa.Column('password_changed_at', sa.DateTime, nullable=True),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, default=True),
        
        # Security
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('two_factor_secret', sa.String(32), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime, nullable=True),
        sa.Column('last_successful_login', sa.DateTime, nullable=True),
        
        # Account preferences
        sa.Column('session_timeout_minutes', sa.Integer(), nullable=False, default=30),
        sa.Column('theme_preference', sa.String(20), nullable=False, default='light'),
        sa.Column('language_preference', sa.String(10), nullable=False, default='en'),
        
        # Relationships
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        
        sa.Index('ix_portal_accounts_tenant_id', 'tenant_id'),
        sa.Index('ix_portal_accounts_portal_id', 'portal_id'),
        sa.Index('ix_portal_accounts_customer_id', 'customer_id'),
    )


def downgrade() -> None:
    """Drop identity and customer related tables."""
    op.drop_table('portal_accounts')
    op.drop_table('customers')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')