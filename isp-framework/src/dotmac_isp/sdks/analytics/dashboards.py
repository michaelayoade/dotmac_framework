"""
Dashboards SDK for analytics visualization management.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError
from ..models.dashboards import Dashboard, Widget

logger = logging.getLogger(__name__)


class DashboardsSDK:
    """SDK for analytics dashboards operations."""

    def __init__(self, tenant_id: str, db: Session):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.db = db

    async def create_dashboard(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        is_public: bool = False,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new dashboard."""
        try:
            dashboard = Dashboard(
                tenant_id=self.tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                category=category,
                layout=layout or {},
                is_public=is_public,
                owner_id=owner_id or "system",
            )

            self.db.add(dashboard)
            self.db.commit()
            self.db.refresh(dashboard)

            return {
                "dashboard_id": str(dashboard.id),
                "name": dashboard.name,
                "display_name": dashboard.display_name,
                "created_at": dashboard.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create dashboard: {e}")
            raise AnalyticsError(f"Dashboard creation failed: {str(e)}")

    async def create_widget(  # noqa: PLR0913
        self,
        dashboard_id: str,
        name: str,
        title: str,
        widget_type: str,
        query_config: Dict[str, Any],
        visualization_config: Optional[Dict[str, Any]] = None,
        position_x: int = 0,
        position_y: int = 0,
        width: int = 4,
        height: int = 3,
    ) -> Dict[str, Any]:
        """Create a new widget."""
        try:
            widget = Widget(
                tenant_id=self.tenant_id,
                dashboard_id=dashboard_id,
                name=name,
                title=title,
                widget_type=widget_type,
                query_config=query_config,
                visualization_config=visualization_config or {},
                position_x=position_x,
                position_y=position_y,
                width=width,
                height=height,
            )

            self.db.add(widget)
            self.db.commit()
            self.db.refresh(widget)

            return {
                "widget_id": str(widget.id),
                "dashboard_id": dashboard_id,
                "name": widget.name,
                "title": widget.title,
                "created_at": widget.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create widget: {e}")
            raise AnalyticsError(f"Widget creation failed: {str(e)}")

    async def get_dashboards(
        self,
        category: Optional[str] = None,
        owner_id: Optional[str] = None,
        is_public: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get dashboards with filtering."""
        try:
            query = self.db.query(Dashboard).filter(
                Dashboard.tenant_id == self.tenant_id
            )

            if category:
                query = query.filter(Dashboard.category == category)

            if owner_id:
                query = query.filter(Dashboard.owner_id == owner_id)

            if is_public is not None:
                query = query.filter(Dashboard.is_public == is_public)

            dashboards = query.offset(offset).limit(limit).all()

            return [
                {
                    "id": str(dashboard.id),
                    "name": dashboard.name,
                    "display_name": dashboard.display_name,
                    "description": dashboard.description,
                    "category": dashboard.category,
                    "is_public": dashboard.is_public,
                    "owner_id": dashboard.owner_id,
                    "view_count": dashboard.view_count,
                    "created_at": dashboard.created_at,
                }
                for dashboard in dashboards
            ]

        except Exception as e:
            logger.error(f"Failed to get dashboards: {e}")
            raise AnalyticsError(f"Dashboards retrieval failed: {str(e)}")
