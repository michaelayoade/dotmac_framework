"""
Sort builders for interaction queries.
"""

from typing import Dict, Callable
from sqlalchemy.orm import Query
from sqlalchemy import desc, asc, func

from ..models import CommunicationInteraction


class InteractionSortBuilder:
    """Handles sorting logic for interaction queries."""
    
    def __init__(self):
        self._sort_fields = {
            'created_at': CommunicationInteraction.created_at,
            'updated_at': CommunicationInteraction.updated_at,
            'priority': CommunicationInteraction.priority,
            'status': CommunicationInteraction.status,
            'channel': CommunicationInteraction.channel,
            'customer_id': CommunicationInteraction.customer_id,
            'agent_id': CommunicationInteraction.assigned_agent_id,
            'subject': CommunicationInteraction.subject,
            'satisfaction_score': CommunicationInteraction.customer_satisfaction_score,
            'response_time': self._response_time_expression,
        }
    
    def _response_time_expression(self):
        """Calculate response time for sorting."""
        return func.timestampdiff(
            'MINUTE',
            CommunicationInteraction.created_at,
            CommunicationInteraction.first_response_at
        )
    
    def apply_sort(self, query: Query, sort_field: str, sort_direction: str = 'desc') -> Query:
        """Apply sorting to the query."""
        if sort_field not in self._sort_fields:
            # Default to created_at if unknown field
            sort_field = 'created_at'
        
        field_expr = self._sort_fields[sort_field]
        if callable(field_expr):
            field_expr = field_expr()
        
        if sort_direction.lower() == 'asc':
            return query.order_by(asc(field_expr))
        else:
            return query.order_by(desc(field_expr))
    
    def get_available_sort_fields(self) -> list[str]:
        """Get list of available sort fields."""
        return list(self._sort_fields.keys())