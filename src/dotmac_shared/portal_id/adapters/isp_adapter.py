"""ISP Framework adapter for portal ID collision checking."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.service import PortalIdCollisionChecker

logger = logging.getLogger(__name__)


class ISPPortalIdCollisionChecker(PortalIdCollisionChecker):
    """Collision checker for ISP Framework portal IDs."""

    def __init__(self, db_session: Session, tenant_id: Optional[str] = None):
        self.db_session = db_session
        self.tenant_id = tenant_id

    async def check_collision(self, portal_id: str) -> bool:
        """
        Check if portal ID exists in ISP Framework tables.

        Checks:
        - customers.portal_id
        - portal_accounts.portal_id (if portal_management module exists)
        """
        try:
            # Check customers table
            customer_query = text(
                "SELECT 1 FROM customers WHERE portal_id = :portal_id"
                + (" AND tenant_id = :tenant_id" if self.tenant_id else "")
                + " LIMIT 1"
            )
            params = {"portal_id": portal_id}
            if self.tenant_id:
                params["tenant_id"] = self.tenant_id

            result = self.db_session.execute(customer_query, params).fetchone()
            if result:
                logger.debug(
                    f"Portal ID collision found in customers table: {portal_id}"
                )
                return True

            # Check portal_accounts table if it exists
            try:
                portal_account_query = text(
                    "SELECT 1 FROM portal_accounts WHERE portal_id = :portal_id"
                    + (" AND tenant_id = :tenant_id" if self.tenant_id else "")
                    + " LIMIT 1"
                )
                result = self.db_session.execute(
                    portal_account_query, params
                ).fetchone()
                if result:
                    logger.debug(
                        f"Portal ID collision found in portal_accounts table: {portal_id}"
                    )
                    return True
            except Exception:
                # Table might not exist, ignore
                pass

            return False

        except Exception as e:
            logger.error(f"Error checking portal ID collision: {e}")
            # On error, assume collision to be safe
            return True


class ISPLegacyCollisionChecker(PortalIdCollisionChecker):
    """Legacy collision checker for backward compatibility."""

    def __init__(self, existing_ids: set):
        self.existing_ids = existing_ids

    async def check_collision(self, portal_id: str) -> bool:
        """Check collision against provided set of existing IDs."""
        return portal_id in self.existing_ids
