"""Management Platform adapter for portal ID collision checking."""

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.service import PortalIdCollisionChecker

logger = logging.getLogger(__name__)


class ManagementPortalIdCollisionChecker(PortalIdCollisionChecker):
    """Collision checker for Management Platform portal IDs."""

    def __init__(self, db_session: Session, tenant_id: Optional[str] = None):
        self.db_session = db_session
        self.tenant_id = tenant_id

    async def check_collision(self, portal_id: str) -> bool:
        """
        Check if portal ID exists in Management Platform tables.

        Checks:
        - users.portal_id (if column exists)
        - partners.portal_id (if table/column exists)
        - tenant_users.portal_id (if column exists)
        """
        try:
            # Check users table for portal_id column
            try:
                user_query = text(
                    "SELECT 1 FROM users WHERE portal_id = :portal_id"
                    + (" AND tenant_id = :tenant_id" if self.tenant_id else "")
                    + " LIMIT 1"
                )
                params = {"portal_id": portal_id}
                if self.tenant_id:
                    params["tenant_id"] = self.tenant_id

                result = self.db_session.execute(user_query, params).fetchone()
                if result:
                    logger.debug(
                        f"Portal ID collision found in users table: {portal_id}"
                    )
                    return True
            except Exception:
                # Column might not exist, ignore
                pass

            # Check partners table if it exists
            try:
                partner_query = text(
                    "SELECT 1 FROM partners WHERE portal_id = :portal_id"
                    + (" AND tenant_id = :tenant_id" if self.tenant_id else "")
                    + " LIMIT 1"
                )
                result = self.db_session.execute(partner_query, params).fetchone()
                if result:
                    logger.debug(
                        f"Portal ID collision found in partners table: {portal_id}"
                    )
                    return True
            except Exception:
                # Table/column might not exist, ignore
                pass

            # Check tenant_users table if it exists
            try:
                tenant_user_query = text(
                    "SELECT 1 FROM tenant_users WHERE portal_id = :portal_id"
                    + (" AND tenant_id = :tenant_id" if self.tenant_id else "")
                    + " LIMIT 1"
                )
                result = self.db_session.execute(tenant_user_query, params).fetchone()
                if result:
                    logger.debug(
                        f"Portal ID collision found in tenant_users table: {portal_id}"
                    )
                    return True
            except Exception:
                # Table/column might not exist, ignore
                pass

            return False

        except Exception as e:
            logger.error(
                f"Error checking portal ID collision in Management Platform: {e}"
            )
            # On error, assume collision to be safe
            return True
