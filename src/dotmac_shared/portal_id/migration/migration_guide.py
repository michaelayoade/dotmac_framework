"""
Migration guide for moving from duplicated portal ID generation to unified service.

This module provides migration utilities and examples for updating existing code
to use the new unified portal ID service.
"""

import logging
from typing import Optional, Set

from sqlalchemy.orm import Session

from ..adapters import ISPPortalIdCollisionChecker
from ..core.service import PortalIdServiceFactory

logger = logging.getLogger(__name__)


def migrate_isp_identity_repository(
    db_session: Session, tenant_id: Optional[str] = None
):
    """
    Migration example for dotmac_isp.modules.identity.repository._generate_portal_id

    BEFORE (duplicated in repository.py):
    ```python
    def _generate_portal_id(self) -> str:
        import secrets
        import string
        max_attempts = 10
        for _ in range(max_attempts):
            characters = string.ascii_uppercase + string.digits
            characters = characters.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
            portal_id = "".join(secrets.choice(characters) for _ in range(8))
            existing = self.db.query(Customer).filter(Customer.portal_id == portal_id).first()
            if not existing:
                return portal_id
        raise ValueError("Could not generate unique portal ID")
    ```

    AFTER (using unified service):
    """
    collision_checker = ISPPortalIdCollisionChecker(db_session, tenant_id)
    service = PortalIdServiceFactory.create_isp_service(collision_checker)

    # This replaces the entire _generate_portal_id method
    return service.generate_portal_id_sync()


def migrate_portal_management_models():
    """
    Migration example for dotmac_isp.modules.portal_management.models._generate_portal_id

    BEFORE (duplicated in models.py):
    ```python
    @staticmethod
    def _generate_portal_id() -> str:
        import secrets
        import string
        characters = string.ascii_uppercase + string.digits
        characters = characters.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
        return "".join(secrets.choice(characters) for _ in range(8))
    ```

    AFTER (using unified service):
    """
    from dotmac_shared.portal_id import generate_portal_id

    # This replaces the entire _generate_portal_id static method
    return generate_portal_id(service_type="isp")


def migrate_portal_management_service():
    """
    Migration example for dotmac_isp.modules.portal_management.service._generate_portal_id

    BEFORE (duplicated timestamp-based generation):
    ```python
    def _generate_portal_id(self) -> str:
        timestamp = int(datetime.now(timezone.utc).timestamp())
        random_chars = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        return f"PRT-{timestamp}-{random_chars}"
    ```

    AFTER (using unified service):
    """
    from dotmac_shared.portal_id import generate_portal_id

    # This replaces the entire _generate_portal_id method
    return generate_portal_id(service_type="legacy")


def migrate_isp_identity_service(existing_portal_ids: Set[str]):
    """
    Migration example for dotmac_isp.modules.identity.service usage

    BEFORE:
    ```python
    from dotmac_isp.modules.identity.portal_id_generator import get_portal_id_generator
    portal_id = get_portal_id_generator().generate_portal_id(existing_portal_ids)
    ```

    AFTER:
    """
    from dotmac_shared.portal_id import generate_portal_id

    # Much simpler and consolidated
    return generate_portal_id(existing_ids=existing_portal_ids, service_type="isp")


class MigrationHelper:
    """Helper class for migrating existing portal ID generation code."""

    @staticmethod
    def get_replacement_imports() -> dict:
        """Get import replacements for migration."""
        return {
            # Old imports -> New imports
            "from dotmac_isp.modules.identity.portal_id_generator import get_portal_id_generator": "from dotmac_shared.portal_id import generate_portal_id",
            "from dotmac_isp.modules.identity.portal_id_generator import generate_portal_id": "from dotmac_shared.portal_id import generate_portal_id",
            "get_portal_id_generator().generate_portal_id(existing_ids)": "generate_portal_id(existing_ids=existing_ids)",
        }

    @staticmethod
    def get_method_replacements() -> dict:
        """Get method call replacements for migration."""
        return {
            # Old method calls -> New method calls
            "self._generate_portal_id()": "generate_portal_id(service_type='isp')",
            "PortalAccount._generate_portal_id()": "generate_portal_id(service_type='isp')",
            "get_portal_id_generator().generate_portal_id": "generate_portal_id",
        }

    @staticmethod
    def validate_migration(
        old_implementation_callable,
        new_service_type: str = "isp",
        iterations: int = 100,
    ):
        """
        Validate that migration produces similar results to old implementation.

        Args:
            old_implementation_callable: Function that generates portal ID using old method
            new_service_type: Service type for new implementation
            iterations: Number of test iterations
        """
        from dotmac_shared.portal_id import generate_portal_id

        old_ids = set()
        new_ids = set()

        # Generate IDs with both implementations
        for _ in range(iterations):
            try:
                old_id = old_implementation_callable()
                old_ids.add(old_id)
            except Exception as e:
                logger.warning(f"Old implementation failed: {e}")

            try:
                new_id = generate_portal_id(service_type=new_service_type)
                new_ids.add(new_id)
            except Exception as e:
                logger.error(f"New implementation failed: {e}")

        # Validate characteristics
        results = {
            "old_unique_count": len(old_ids),
            "new_unique_count": len(new_ids),
            "old_avg_length": (
                sum(len(id) for id in old_ids) / len(old_ids) if old_ids else 0
            ),
            "new_avg_length": (
                sum(len(id) for id in new_ids) / len(new_ids) if new_ids else 0
            ),
            "old_sample": list(old_ids)[:5],
            "new_sample": list(new_ids)[:5],
            "migration_successful": len(new_ids) > 0 and len(new_ids) == iterations,
        }

        logger.info(f"Migration validation results: {results}")
        return results


def create_migration_checklist():
    """Create a checklist for migrating to unified portal ID service."""
    return {
        "files_to_update": [
            "src/dotmac_isp/modules/identity/repository.py - Remove _generate_portal_id method",
            "src/dotmac_isp/modules/portal_management/models.py - Remove _generate_portal_id static method",
            "src/dotmac_isp/modules/portal_management/service.py - Remove _generate_portal_id method",
            "src/dotmac_isp/modules/identity/service.py - Update to use unified service",
            "Any test files that mock these methods",
        ],
        "import_updates": [
            "Replace portal_id_generator imports with dotmac_shared.portal_id imports",
            "Update any direct method calls to use new convenience functions",
        ],
        "configuration_updates": [
            "Move portal ID settings to unified configuration if using advanced features",
            "Set up collision checkers for async generation if needed",
        ],
        "testing": [
            "Run migration validation helper",
            "Test portal ID uniqueness across platforms",
            "Verify collision checking works correctly",
            "Check that existing portal IDs remain valid",
        ],
    }
