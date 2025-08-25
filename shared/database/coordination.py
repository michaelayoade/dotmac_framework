"""
Database coordination utilities for DotMac Platform.

Manages database migrations across ISP Framework and Management Platform
to ensure consistent schema evolution and prevent conflicts.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class MigrationCoordinator:
    """Coordinates database migrations across multiple services."""
    
    def __init__(self):
        self.services = {
            'management-platform': {
                'database_url': 'postgresql://mgmt_user:mgmt_password@localhost:5432/mgmt_platform',
                'alembic_config': '/home/dotmac_framework/management-platform/alembic.ini',
                'migration_path': '/home/dotmac_framework/management-platform/migrations'
            },
            'isp-framework': {
                'database_url': 'postgresql://isp_user:isp_password@localhost:5432/dotmac_isp',
                'alembic_config': '/home/dotmac_framework/isp-framework/alembic.ini',
                'migration_path': '/home/dotmac_framework/isp-framework/alembic'
            }
        }
        
    def get_migration_order(self) -> List[str]:
        """Get the recommended order for running migrations."""
        return [
            'management-platform',  # Core tenant/user structure first
            'isp-framework'         # ISP-specific tables second
        ]
    
    async def run_coordinated_migration(self) -> Dict[str, bool]:
        """
        Run migrations in coordinated order.
        
        Returns:
            Dict mapping service names to success status
        """
        results = {}
        migration_order = self.get_migration_order()
        
        logger.info(f"Starting coordinated migration for: {migration_order}")
        
        for service in migration_order:
            logger.info(f"Running migration for {service}...")
            
            try:
                success = await self._run_service_migration(service)
                results[service] = success
                
                if not success:
                    logger.error(f"Migration failed for {service}, stopping coordination")
                    break
                    
            except Exception as e:
                logger.error(f"Error running migration for {service}: {e}")
                results[service] = False
                break
        
        return results
    
    async def _run_service_migration(self, service: str) -> bool:
        """Run migration for a specific service."""
        import subprocess
        
        config = self.services[service]
        alembic_config = config['alembic_config']
        
        # Run alembic upgrade head
        cmd = ['alembic', '-c', alembic_config, 'upgrade', 'head']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Migration successful for {service}")
                return True
            else:
                logger.error(f"Migration failed for {service}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Migration timeout for {service}")
            return False
        except Exception as e:
            logger.error(f"Migration error for {service}: {e}")
            return False
    
    def validate_schema_compatibility(self) -> List[str]:
        """
        Validate that schemas between services are compatible.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Check for overlapping table names
        mgmt_tables = self._get_table_list('management-platform')
        isp_tables = self._get_table_list('isp-framework')
        
        overlapping_tables = set(mgmt_tables) & set(isp_tables)
        if overlapping_tables:
            warnings.append(f"Overlapping tables found: {overlapping_tables}")
        
        # Check for foreign key references
        cross_refs = self._check_cross_service_references()
        if cross_refs:
            warnings.append(f"Cross-service foreign key references: {cross_refs}")
        
        return warnings
    
    def _get_table_list(self, service: str) -> List[str]:
        """Get list of tables for a service from migration files."""
        # This would parse migration files to extract table names
        # Simplified implementation
        if service == 'management-platform':
            return ['users', 'tenants', 'billing_plans', 'subscriptions', 'invoices', 'payments']
        elif service == 'isp-framework':
            return ['roles', 'users', 'customers', 'portal_accounts', 'user_roles']
        return []
    
    def _check_cross_service_references(self) -> List[str]:
        """Check for foreign key references between services."""
        # This would check for cross-database foreign keys
        # which are generally not recommended
        return []


# Global coordinator instance
migration_coordinator = MigrationCoordinator()


async def coordinate_migrations():
    """Convenience function to run coordinated migrations."""
    return await migration_coordinator.run_coordinated_migration()


def validate_schemas():
    """Convenience function to validate schema compatibility."""
    return migration_coordinator.validate_schema_compatibility()