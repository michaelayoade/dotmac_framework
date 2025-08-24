"""
Segments SDK for analytics customer segmentation.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError
from ..models.enums import SegmentOperator
from ..models.segments import Segment, SegmentMembership, SegmentRule

logger = logging.getLogger(__name__)


class SegmentsSDK:
    """SDK for analytics segments operations."""

    def __init__(self, tenant_id: str, db: Session):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.db = db

    async def create_segment(
        self,
        name: str,
        display_name: str,
        entity_type: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        is_dynamic: bool = True,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new segment."""
        try:
            segment = Segment(
                tenant_id=self.tenant_id,
                name=name,
                display_name=display_name,
                entity_type=entity_type,
                description=description,
                category=category,
                is_dynamic=is_dynamic,
                owner_id=owner_id or "system",
            )

            self.db.add(segment)
            self.db.commit()
            self.db.refresh(segment)

            return {
                "segment_id": str(segment.id),
                "name": segment.name,
                "display_name": segment.display_name,
                "entity_type": segment.entity_type,
                "created_at": segment.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create segment: {e}")
            raise AnalyticsError(f"Segment creation failed: {str(e)}")

    async def add_segment_rule(
        self,
        segment_id: str,
        field_name: str,
        operator: SegmentOperator,
        value: Any,
        data_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a rule to a segment."""
        try:
            rule = SegmentRule(
                tenant_id=self.tenant_id,
                segment_id=segment_id,
                field_name=field_name,
                operator=operator.value,
                value=value,
                data_source=data_source,
            )

            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)

            return {
                "rule_id": str(rule.id),
                "segment_id": segment_id,
                "field_name": field_name,
                "operator": rule.operator,
                "created_at": rule.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add segment rule: {e}")
            raise AnalyticsError(f"Segment rule creation failed: {str(e)}")

    async def get_segment_members(
        self, segment_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get members of a segment."""
        try:
            memberships = (
                self.db.query(SegmentMembership)
                .filter(
                    SegmentMembership.tenant_id == self.tenant_id,
                    SegmentMembership.segment_id == segment_id,
                )
                .offset(offset)
                .limit(limit)
                .all()
            )

            return [
                {
                    "entity_id": membership.entity_id,
                    "entity_type": membership.entity_type,
                    "joined_at": membership.joined_at,
                    "membership_score": membership.membership_score,
                }
                for membership in memberships
            ]

        except Exception as e:
            logger.error(f"Failed to get segment members: {e}")
            raise AnalyticsError(f"Segment members retrieval failed: {str(e)}")
