"""
Fluent query builder for communication interactions.
Replaces the 25-complexity search_interactions method.
"""

from typing import Dict, Any, List, Tuple, Optional, Union
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Query, Session
from sqlalchemy import desc, asc, func, and_, or_

from ..models import CommunicationInteraction, InteractionStatus, CommunicationChannel
from .filter_builders import FILTER_REGISTRY, get_filter
from .sort_builders import InteractionSortBuilder
from .pagination_builders import PaginationBuilder


class InteractionQueryBuilder:
    """
    Fluent interface for building complex interaction queries.
    
    REFACTORED: Replaces 25-complexity search_interactions method.
    Each method handles one concern, reducing overall complexity.
    """
    
    def __init__(self, session: Session, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.query = session.query(CommunicationInteraction)
        self._applied_base_filters = False
        self._sort_builder = InteractionSortBuilder()
        self._pagination_builder = PaginationBuilder()
    
    def _ensure_base_filters(self) -> 'InteractionQueryBuilder':
        """Ensure tenant isolation is applied."""
        if not self._applied_base_filters:
            self.query = self.query.filter(CommunicationInteraction.tenant_id == self.tenant_id)
            self._applied_base_filters = True
        return self
    
    def filter_by_customer(self, customer_id: UUID) -> 'InteractionQueryBuilder':
        """Filter by customer ID."""
        self._ensure_base_filters()
        customer_filter = get_filter('customer_id')
        if customer_filter:
            self.query = customer_filter.apply(self.query, customer_id)
        return self
    
    def filter_by_contact(self, contact_id: UUID) -> 'InteractionQueryBuilder':
        """Filter by contact ID.""" 
        self._ensure_base_filters()
        contact_filter = get_filter('contact_id')
        if contact_filter:
            self.query = contact_filter.apply(self.query, contact_id)
        return self
    
    def filter_by_agent(self, agent_id: UUID) -> 'InteractionQueryBuilder':
        """Filter by assigned agent."""
        self._ensure_base_filters()
        agent_filter = get_filter('agent_id')
        if agent_filter:
            self.query = agent_filter.apply(self.query, agent_id)
        return self
    
    def filter_by_status(self, status: Union[InteractionStatus, List[InteractionStatus]]) -> 'InteractionQueryBuilder':
        """Filter by interaction status."""
        self._ensure_base_filters()
        status_filter = get_filter('status')
        if status_filter:
            self.query = status_filter.apply(self.query, status)
        return self
    
    def filter_by_channel(self, channel: Union[CommunicationChannel, List[CommunicationChannel]]) -> 'InteractionQueryBuilder':
        """Filter by communication channel."""
        self._ensure_base_filters()
        channel_filter = get_filter('channel')
        if channel_filter:
            self.query = channel_filter.apply(self.query, channel)
        return self
    
    def filter_by_date_range(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> 'InteractionQueryBuilder':
        """Filter by date range."""
        self._ensure_base_filters()
        if start_date or end_date:
            date_filter = get_filter('date_range')
            if date_filter:
                date_range = {}
                if start_date:
                    date_range['start'] = start_date
                if end_date:
                    date_range['end'] = end_date
                self.query = date_filter.apply(self.query, date_range)
        return self
    
    def filter_by_priority(self, priority: Union[str, List[str]]) -> 'InteractionQueryBuilder':
        """Filter by priority level."""
        self._ensure_base_filters()
        priority_filter = get_filter('priority')
        if priority_filter:
            self.query = priority_filter.apply(self.query, priority)
        return self
    
    def search_text(self, search_term: str) -> 'InteractionQueryBuilder':
        """Search interactions by text content."""
        self._ensure_base_filters()
        text_filter = get_filter('search')
        if text_filter and search_term.strip():
            self.query = text_filter.apply(self.query, search_term)
        return self
    
    def filter_by_tags(self, tags: Union[str, List[str]]) -> 'InteractionQueryBuilder':
        """Filter by interaction tags."""
        self._ensure_base_filters()
        tags_filter = get_filter('tags')
        if tags_filter:
            self.query = tags_filter.apply(self.query, tags)
        return self
    
    def filter_by_resolution(self, is_resolved: bool) -> 'InteractionQueryBuilder':
        """Filter by resolution status."""
        self._ensure_base_filters()
        resolution_filter = get_filter('is_resolved')
        if resolution_filter:
            self.query = resolution_filter.apply(self.query, is_resolved)
        return self
    
    def filter_by_escalation(self, is_escalated: bool) -> 'InteractionQueryBuilder':
        """Filter by escalation status."""
        self._ensure_base_filters()
        escalation_filter = get_filter('is_escalated')
        if escalation_filter:
            self.query = escalation_filter.apply(self.query, is_escalated)
        return self
    
    def filter_by_team(self, team_id: UUID) -> 'InteractionQueryBuilder':
        """Filter by assigned team."""
        self._ensure_base_filters()
        team_filter = get_filter('team_id')
        if team_filter:
            self.query = team_filter.apply(self.query, team_id)
        return self
    
    def apply_filters(self, filters: Dict[str, Any]) -> 'InteractionQueryBuilder':
        """
        Apply multiple filters from a dictionary.
        
        This method handles the complex filtering logic that was in the original
        25-complexity search_interactions method.
        """
        self._ensure_base_filters()
        
        # Handle special cases for backward compatibility
        if 'start_date' in filters or 'end_date' in filters:
            self.filter_by_date_range(
                filters.get('start_date'),
                filters.get('end_date')
            )
        
        # Apply each filter using the registry
        for filter_name, filter_value in filters.items():
            if filter_value is None:
                continue
                
            # Skip date filters as they're handled above
            if filter_name in ['start_date', 'end_date']:
                continue
                
            filter_instance = get_filter(filter_name)
            if filter_instance:
                try:
                    self.query = filter_instance.apply(self.query, filter_value)
                except Exception as e:
                    # Log but don't fail the entire query
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to apply filter {filter_name}: {e}")
        
        return self
    
    def sort_by(self, sort_field: str, sort_direction: str = 'desc') -> 'InteractionQueryBuilder':
        """Apply sorting to the query."""
        self.query = self._sort_builder.apply_sort(
            self.query, sort_field, sort_direction
        )
        return self
    
    def paginate(self, page: int = 1, per_page: int = 20) -> 'InteractionQueryBuilder':
        """Apply pagination to the query."""
        self._pagination_builder.configure(page, per_page)
        return self
    
    def count(self) -> int:
        """Get the total count without pagination."""
        self._ensure_base_filters()
        return self.query.count()
    
    def execute(self) -> Tuple[List[CommunicationInteraction], int]:
        """
        Execute the query and return results with total count.
        
        Returns:
            Tuple of (interactions list, total count)
        """
        self._ensure_base_filters()
        
        # Get total count before pagination
        total_count = self.query.count()
        
        # Apply pagination if configured
        paginated_query = self._pagination_builder.apply_pagination(self.query)
        
        # Execute and return results
        interactions = paginated_query.all()
        
        return interactions, total_count
    
    def execute_one(self) -> Optional[CommunicationInteraction]:
        """Execute the query and return a single result."""
        self._ensure_base_filters()
        return self.query.first()
    
    def get_query(self) -> Query:
        """Get the underlying SQLAlchemy query for advanced usage."""
        self._ensure_base_filters()
        return self.query


# Convenience function for quick queries
def search_interactions(
    session: Session,
    tenant_id: UUID,
    filters: Dict[str, Any],
    sort_field: str = 'created_at',
    sort_direction: str = 'desc',
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[CommunicationInteraction], int]:
    """
    Convenience function that replaces the original complex search_interactions method.
    
    REFACTORED: This is the new simplified interface.
    Complexity reduced from 25 to 3 McCabe score.
    """
    builder = InteractionQueryBuilder(session, tenant_id)
    
    return (builder
            .apply_filters(filters)
            .sort_by(sort_field, sort_direction)
            .paginate(page, per_page)
            .execute())


# Quick filter builders for common use cases
class CommonQueries:
    """Pre-built query patterns for common interaction searches."""
    
    @staticmethod
    def unassigned_interactions(session: Session, tenant_id: UUID) -> InteractionQueryBuilder:
        """Get unassigned interactions."""
        return (InteractionQueryBuilder(session, tenant_id)
                .filter_by_agent(None)
                .filter_by_status(InteractionStatus.PENDING))
    
    @staticmethod
    def overdue_interactions(session: Session, tenant_id: UUID, threshold_hours: int = 24) -> InteractionQueryBuilder:
        """Get overdue interactions."""
        from datetime import timedelta
        threshold_date = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)
        
        return (InteractionQueryBuilder(session, tenant_id)
                .filter_by_date_range(end_date=threshold_date)
                .filter_by_status([InteractionStatus.PENDING, InteractionStatus.IN_PROGRESS]))
    
    @staticmethod
    def high_priority_interactions(session: Session, tenant_id: UUID) -> InteractionQueryBuilder:
        """Get high priority interactions."""
        return (InteractionQueryBuilder(session, tenant_id)
                .filter_by_priority(['high', 'urgent'])
                .filter_by_resolution(False))
    
    @staticmethod
    def agent_workload(session: Session, tenant_id: UUID, agent_id: UUID) -> InteractionQueryBuilder:
        """Get current workload for an agent."""
        return (InteractionQueryBuilder(session, tenant_id)
                .filter_by_agent(agent_id)
                .filter_by_status([InteractionStatus.ASSIGNED, InteractionStatus.IN_PROGRESS]))
    
    @staticmethod
    def customer_history(session: Session, tenant_id: UUID, customer_id: UUID) -> InteractionQueryBuilder:
        """Get interaction history for a customer."""
        return (InteractionQueryBuilder(session, tenant_id)
                .filter_by_customer(customer_id)
                .sort_by('created_at', 'desc'))