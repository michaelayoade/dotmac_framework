"""Create network integration tables

Revision ID: 001_network_integration
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_network_integration'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all network integration tables."""
    
    # Create network locations table
    op.create_table(
        'network_locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('location_type', sa.String(50), nullable=False, index=True),
        sa.Column('code', sa.String(20), nullable=True, unique=True, index=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=8), nullable=True, index=True),
        sa.Column('longitude', sa.Numeric(precision=11, scale=8), nullable=True, index=True),
        sa.Column('elevation_meters', sa.Float, nullable=True),
        sa.Column('facility_size_sqm', sa.Float, nullable=True),
        sa.Column('power_capacity_kw', sa.Float, nullable=True),
        sa.Column('cooling_capacity_tons', sa.Float, nullable=True),
        sa.Column('rack_count', sa.Integer, nullable=True),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('access_hours', sa.String(255), nullable=True),
        sa.Column('access_instructions', sa.Text, nullable=True),
        sa.Column('service_area_radius_km', sa.Float, nullable=True),
        sa.Column('population_served', sa.Integer, nullable=True),
        sa.Column('street_address', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country_code', sa.String(2), default='US', nullable=False),
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
    
    # Create network devices table
    op.create_table(
        'network_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('hostname', sa.String(255), nullable=True, unique=True, index=True),
        sa.Column('device_type', sa.String(50), nullable=False, index=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('vendor', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True, unique=True),
        sa.Column('asset_tag', sa.String(100), nullable=True, unique=True),
        sa.Column('management_ip', postgresql.INET, nullable=True, unique=True, index=True),
        sa.Column('subnet_mask', sa.String(18), nullable=True),
        sa.Column('gateway', postgresql.INET, nullable=True),
        sa.Column('dns_servers', postgresql.JSON, nullable=True),
        sa.Column('snmp_community', sa.String(100), nullable=True),
        sa.Column('snmp_version', sa.String(10), default='v2c', nullable=False),
        sa.Column('snmp_port', sa.Integer, default=161, nullable=False),
        sa.Column('snmp_enabled', sa.Boolean, default=True, nullable=False),
        sa.Column('cpu_count', sa.Integer, nullable=True),
        sa.Column('memory_total_mb', sa.BigInteger, nullable=True),
        sa.Column('storage_total_gb', sa.Integer, nullable=True),
        sa.Column('power_consumption_watts', sa.Integer, nullable=True),
        sa.Column('os_version', sa.String(100), nullable=True),
        sa.Column('firmware_version', sa.String(100), nullable=True),
        sa.Column('last_config_backup', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monitoring_enabled', sa.Boolean, default=True, nullable=False),
        sa.Column('monitoring_interval', sa.Integer, default=300, nullable=False),
        sa.Column('rack_location', sa.String(100), nullable=True),
        sa.Column('rack_unit', sa.String(10), nullable=True),
        sa.Column('datacenter', sa.String(100), nullable=True),
        sa.Column('warranty_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_maintenance', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_maintenance', sa.DateTime(timezone=True), nullable=True),
        sa.Column('street_address', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('country_code', sa.String(2), default='US', nullable=False),
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
    
    # Create network interfaces table
    op.create_table(
        'network_interfaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_devices.id'), nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('interface_type', sa.String(20), nullable=False),
        sa.Column('interface_index', sa.Integer, nullable=True),
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('subnet_mask', sa.String(18), nullable=True),
        sa.Column('vlan_id', sa.Integer, nullable=True),
        sa.Column('mac_address', sa.String(17), nullable=True, index=True),
        sa.Column('speed_mbps', sa.BigInteger, nullable=True),
        sa.Column('duplex', sa.String(10), nullable=True),
        sa.Column('mtu', sa.Integer, default=1500, nullable=False),
        sa.Column('admin_status', sa.String(20), default='up', nullable=False),
        sa.Column('operational_status', sa.String(20), default='down', nullable=False),
        sa.Column('last_change', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bytes_in', sa.BigInteger, default=0, nullable=False),
        sa.Column('bytes_out', sa.BigInteger, default=0, nullable=False),
        sa.Column('packets_in', sa.BigInteger, default=0, nullable=False),
        sa.Column('packets_out', sa.BigInteger, default=0, nullable=False),
        sa.Column('errors_in', sa.BigInteger, default=0, nullable=False),
        sa.Column('errors_out', sa.BigInteger, default=0, nullable=False),
        sa.Column('discards_in', sa.BigInteger, default=0, nullable=False),
        sa.Column('discards_out', sa.BigInteger, default=0, nullable=False),
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
    
    # Create network metrics table
    op.create_table(
        'network_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_devices.id'), nullable=False, index=True),
        sa.Column('interface_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_interfaces.id'), nullable=True, index=True),
        sa.Column('metric_name', sa.String(100), nullable=False, index=True),
        sa.Column('metric_type', sa.String(50), nullable=False, index=True),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('labels', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create network topology table
    op.create_table(
        'network_topology',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('parent_device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_devices.id'), nullable=False, index=True),
        sa.Column('child_device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_devices.id'), nullable=False, index=True),
        sa.Column('connection_type', sa.String(50), nullable=False, index=True),
        sa.Column('parent_interface_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_interfaces.id'), nullable=True),
        sa.Column('child_interface_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_interfaces.id'), nullable=True),
        sa.Column('bandwidth_mbps', sa.Integer, nullable=True),
        sa.Column('distance_meters', sa.Float, nullable=True),
        sa.Column('cable_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create device configurations table
    op.create_table(
        'device_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_devices.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean, default=False, nullable=False),
        sa.Column('is_backup', sa.Boolean, default=False, nullable=False),
        sa.Column('configuration_data', sa.Text, nullable=False),
        sa.Column('configuration_hash', sa.String(64), nullable=True, index=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('deployment_status', sa.String(50), default='draft', nullable=False),
        sa.Column('deployment_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('syntax_validated', sa.Boolean, default=False, nullable=False),
        sa.Column('validation_errors', postgresql.JSON, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create network alerts table
    op.create_table(
        'network_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_devices.id'), nullable=True, index=True),
        sa.Column('interface_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('network_interfaces.id'), nullable=True, index=True),
        sa.Column('alert_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False, index=True),
        sa.Column('is_acknowledged', sa.Boolean, default=False, nullable=False),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metric_name', sa.String(100), nullable=True),
        sa.Column('threshold_value', sa.Float, nullable=True),
        sa.Column('current_value', sa.Float, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create device groups table
    op.create_table(
        'device_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('group_type', sa.String(50), nullable=False, index=True),
        sa.Column('monitoring_template', sa.String(255), nullable=True),
        sa.Column('alert_rules', postgresql.JSON, nullable=True),
        sa.Column('maintenance_schedule', postgresql.JSON, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create network services table
    op.create_table(
        'network_services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('service_type', sa.String(100), nullable=False, index=True),
        sa.Column('protocol', sa.String(20), nullable=False),
        sa.Column('port', sa.Integer, nullable=True),
        sa.Column('listen_address', postgresql.INET, nullable=True),
        sa.Column('configuration', postgresql.JSON, nullable=True),
        sa.Column('health_check_enabled', sa.Boolean, default=True, nullable=False),
        sa.Column('health_check_interval', sa.Integer, default=60, nullable=False),
        sa.Column('health_check_timeout', sa.Integer, default=10, nullable=False),
        sa.Column('dependencies', postgresql.JSON, nullable=True),
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
    
    # Create maintenance windows table
    op.create_table(
        'maintenance_windows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('maintenance_type', sa.String(50), nullable=False, index=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('timezone', sa.String(50), default='UTC', nullable=False),
        sa.Column('impact_level', sa.String(20), nullable=False, index=True),
        sa.Column('affected_services', postgresql.JSON, nullable=True),
        sa.Column('approval_status', sa.String(20), default='pending', nullable=False),
        sa.Column('execution_status', sa.String(20), default='scheduled', nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('work_instructions', sa.Text, nullable=True),
        sa.Column('rollback_plan', sa.Text, nullable=True),
        sa.Column('notifications_enabled', sa.Boolean, default=True, nullable=False),
        sa.Column('notification_channels', postgresql.JSON, nullable=True),
        sa.Column('tags', postgresql.JSON, nullable=True),
        sa.Column('custom_fields', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean, default=False, nullable=False),
    )
    
    # Create indexes for better performance
    op.create_index('ix_network_devices_tenant_name', 'network_devices', ['tenant_id', 'name'])
    op.create_index('ix_network_interfaces_device_name', 'network_interfaces', ['device_id', 'name'])
    op.create_index('ix_network_metrics_device_metric_time', 'network_metrics', ['device_id', 'metric_name', 'timestamp'])
    op.create_index('ix_network_alerts_device_severity', 'network_alerts', ['device_id', 'severity', 'is_active'])
    op.create_index('ix_network_topology_parent_child', 'network_topology', ['parent_device_id', 'child_device_id'])


def downgrade() -> None:
    """Drop all network integration tables."""
    
    # Drop indexes first
    op.drop_index('ix_network_topology_parent_child')
    op.drop_index('ix_network_alerts_device_severity')
    op.drop_index('ix_network_metrics_device_metric_time')
    op.drop_index('ix_network_interfaces_device_name')
    op.drop_index('ix_network_devices_tenant_name')
    
    # Drop tables in reverse order of creation to handle foreign key constraints
    op.drop_table('maintenance_windows')
    op.drop_table('network_services')
    op.drop_table('device_groups')
    op.drop_table('network_alerts')
    op.drop_table('device_configurations')
    op.drop_table('network_topology')
    op.drop_table('network_metrics')
    op.drop_table('network_interfaces')
    op.drop_table('network_devices')
    op.drop_table('network_locations')