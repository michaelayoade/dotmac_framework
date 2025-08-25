"""Add missing unique constraints

Revision ID: 004_add_unique_constraints  
Revises: 003_add_infrastructure_templates
Create Date: 2025-08-25 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_unique_constraints'
down_revision: Union[str, None] = '002_add_deployment_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraints that exist in models but not in database
    
    # Plugin categories
    op.create_unique_constraint('uq_plugin_categories_slug', 'plugin_categories', ['slug'])
    
    # Plugins  
    op.create_unique_constraint('uq_plugins_slug', 'plugins', ['slug'])
    
    # Users (already exist in table creation)
    # email and username unique constraints already exist
    
    # User sessions
    op.create_unique_constraint('uq_user_sessions_session_token', 'user_sessions', ['session_token'])
    op.create_unique_constraint('uq_user_sessions_refresh_token', 'user_sessions', ['refresh_token'])
    
    # User invitations
    op.create_unique_constraint('uq_user_invitations_invitation_token', 'user_invitations', ['invitation_token'])
    
    # Tenants (already exists)
    # slug unique constraint already exists
    
    # Billing plans
    op.create_unique_constraint('uq_billing_plans_slug', 'billing_plans', ['slug'])
    
    # Invoices
    op.create_unique_constraint('uq_invoices_invoice_number', 'invoices', ['invoice_number'])


def downgrade() -> None:
    # Drop unique constraints
    op.drop_constraint('uq_invoices_invoice_number', 'invoices', type_='unique')
    op.drop_constraint('uq_billing_plans_slug', 'billing_plans', type_='unique')
    op.drop_constraint('uq_user_invitations_invitation_token', 'user_invitations', type_='unique')
    op.drop_constraint('uq_user_sessions_refresh_token', 'user_sessions', type_='unique')
    op.drop_constraint('uq_user_sessions_session_token', 'user_sessions', type_='unique')
    op.drop_constraint('uq_plugins_slug', 'plugins', type_='unique')
    op.drop_constraint('uq_plugin_categories_slug', 'plugin_categories', type_='unique')