"""Add partner management tables

Revision ID: 006_add_partner_tables
Revises: 005_add_enum_types
Create Date: 2024-01-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_add_partner_tables'
down_revision: Union[str, None] = '005_add_enum_types'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create partners table
    op.create_table(
        'partners',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_name', sa.String(100), nullable=False),
        sa.Column('partner_code', sa.String(10), nullable=False),
        sa.Column('contact_name', sa.String(100), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('contact_phone', sa.String(20), nullable=False),
        sa.Column('address_street', sa.String(200), nullable=True),
        sa.Column('address_city', sa.String(100), nullable=True),
        sa.Column('address_state', sa.String(2), nullable=True),
        sa.Column('address_zip', sa.String(10), nullable=True),
        sa.Column('address_country', sa.String(2), nullable=True, default='US'),
        sa.Column('territory', sa.String(100), nullable=False),
        sa.Column('tier', sa.String(20), nullable=False, default='bronze'),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('monthly_customer_target', sa.Integer(), nullable=True, default=25),
        sa.Column('monthly_revenue_target', sa.Float(), nullable=True, default=50000.0),
        sa.Column('growth_target', sa.Float(), nullable=True, default=10.0),
        sa.Column('commission_tier', sa.String(20), nullable=False, default='bronze'),
        sa.Column('last_payout_amount', sa.Float(), nullable=True, default=0.0),
        sa.Column('next_payout_date', sa.DateTime(), nullable=True),
        sa.Column('total_lifetime_revenue', sa.Float(), nullable=True, default=0.0),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('partner_code')
    )
    
    # Create indexes for partners table
    op.create_index(op.f('ix_partners_id'), 'partners', ['id'], unique=False)
    op.create_index(op.f('ix_partners_company_name'), 'partners', ['company_name'], unique=False)
    op.create_index(op.f('ix_partners_partner_code'), 'partners', ['partner_code'], unique=True)
    op.create_index(op.f('ix_partners_contact_email'), 'partners', ['contact_email'], unique=False)
    op.create_index(op.f('ix_partners_territory'), 'partners', ['territory'], unique=False)
    op.create_index(op.f('ix_partners_tier'), 'partners', ['tier'], unique=False)
    op.create_index(op.f('ix_partners_status'), 'partners', ['status'], unique=False)
    
    # Create partner_customers table
    op.create_table(
        'partner_customers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('partner_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('address_validated', sa.Boolean(), nullable=True, default=False),
        sa.Column('territory_validated', sa.Boolean(), nullable=True, default=False),
        sa.Column('service_plan', sa.String(50), nullable=False),
        sa.Column('mrr', sa.Float(), nullable=False),
        sa.Column('contract_length', sa.Integer(), nullable=True, default=12),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('connection_status', sa.String(20), nullable=True, default='offline'),
        sa.Column('usage_percentage', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('last_payment_date', sa.DateTime(), nullable=True),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('customer_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create indexes for partner_customers table
    op.create_index(op.f('ix_partner_customers_id'), 'partner_customers', ['id'], unique=False)
    op.create_index(op.f('ix_partner_customers_partner_id'), 'partner_customers', ['partner_id'], unique=False)
    op.create_index(op.f('ix_partner_customers_name'), 'partner_customers', ['name'], unique=False)
    op.create_index(op.f('ix_partner_customers_email'), 'partner_customers', ['email'], unique=True)
    op.create_index(op.f('ix_partner_customers_service_plan'), 'partner_customers', ['service_plan'], unique=False)
    op.create_index(op.f('ix_partner_customers_status'), 'partner_customers', ['status'], unique=False)
    
    # Create commissions table
    op.create_table(
        'commissions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('partner_id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('base_amount', sa.Float(), nullable=False),
        sa.Column('bonus_amount', sa.Float(), nullable=True, default=0.0),
        sa.Column('effective_rate', sa.Float(), nullable=False),
        sa.Column('tier_multiplier', sa.Float(), nullable=True, default=1.0),
        sa.Column('product_multiplier', sa.Float(), nullable=True, default=1.0),
        sa.Column('new_customer_bonus', sa.Float(), nullable=True, default=0.0),
        sa.Column('territory_bonus', sa.Float(), nullable=True, default=0.0),
        sa.Column('contract_length_bonus', sa.Float(), nullable=True, default=0.0),
        sa.Column('promotional_adjustment', sa.Float(), nullable=True, default=0.0),
        sa.Column('commission_type', sa.String(20), nullable=True, default='monthly'),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('payout_batch_id', sa.String(), nullable=True),
        sa.Column('calculation_method', sa.String(50), nullable=True),
        sa.Column('calculation_details', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['partner_customers.id'], ),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for commissions table
    op.create_index(op.f('ix_commissions_id'), 'commissions', ['id'], unique=False)
    op.create_index(op.f('ix_commissions_partner_id'), 'commissions', ['partner_id'], unique=False)
    op.create_index(op.f('ix_commissions_customer_id'), 'commissions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_commissions_status'), 'commissions', ['status'], unique=False)
    
    # Create territories table
    op.create_table(
        'territories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('partner_id', sa.String(), nullable=False),
        sa.Column('zip_codes', sa.JSON(), nullable=True),
        sa.Column('cities', sa.JSON(), nullable=True),
        sa.Column('counties', sa.JSON(), nullable=True),
        sa.Column('states', sa.JSON(), nullable=True),
        sa.Column('coordinates_polygon', sa.JSON(), nullable=True),
        sa.Column('excluded_zip_codes', sa.JSON(), nullable=True),
        sa.Column('excluded_addresses', sa.JSON(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=5),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for territories table
    op.create_index(op.f('ix_territories_id'), 'territories', ['id'], unique=False)
    op.create_index(op.f('ix_territories_partner_id'), 'territories', ['partner_id'], unique=False)
    
    # Create partner_performance_metrics table
    op.create_table(
        'partner_performance_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('partner_id', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('customers_added', sa.Integer(), nullable=True, default=0),
        sa.Column('customers_churned', sa.Integer(), nullable=True, default=0),
        sa.Column('customers_total', sa.Integer(), nullable=True, default=0),
        sa.Column('customers_active', sa.Integer(), nullable=True, default=0),
        sa.Column('revenue_total', sa.Float(), nullable=True, default=0.0),
        sa.Column('revenue_new', sa.Float(), nullable=True, default=0.0),
        sa.Column('revenue_churn', sa.Float(), nullable=True, default=0.0),
        sa.Column('revenue_growth_rate', sa.Float(), nullable=True, default=0.0),
        sa.Column('commissions_earned', sa.Float(), nullable=True, default=0.0),
        sa.Column('commissions_paid', sa.Float(), nullable=True, default=0.0),
        sa.Column('commission_rate_average', sa.Float(), nullable=True, default=0.0),
        sa.Column('customer_goal_achievement', sa.Float(), nullable=True, default=0.0),
        sa.Column('revenue_goal_achievement', sa.Float(), nullable=True, default=0.0),
        sa.Column('average_deal_size', sa.Float(), nullable=True, default=0.0),
        sa.Column('conversion_rate', sa.Float(), nullable=True, default=0.0),
        sa.Column('customer_satisfaction', sa.Float(), nullable=True, default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for partner_performance_metrics table
    op.create_index(op.f('ix_partner_performance_metrics_id'), 'partner_performance_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_partner_performance_metrics_partner_id'), 'partner_performance_metrics', ['partner_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order to avoid foreign key constraint issues
    op.drop_table('partner_performance_metrics')
    op.drop_table('territories')
    op.drop_table('commissions')
    op.drop_table('partner_customers')
    op.drop_table('partners')