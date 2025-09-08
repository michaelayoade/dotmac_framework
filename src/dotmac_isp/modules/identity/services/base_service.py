"""Base service for identity domain services."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings

logger = logging.getLogger(__name__)


class BaseIdentityService:
    """Base class for identity domain services."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize base service."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)

        logger.info(f"Initialized {self.__class__.__name__} for tenant: {self.tenant_id}")
