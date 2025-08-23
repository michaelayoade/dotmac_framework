"""
Filter builders for interaction queries.
Each filter handles one specific filtering concern.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Query
from sqlalchemy import and_, or_, func, text

from ..models import (
    CommunicationInteraction,
    InteractionStatus,
    CommunicationChannel,
    InteractionType,
)


class QueryFilter(ABC):
    """Base class for all query filters."""
    
    @abstractmethod
    def apply(self, query: Query, value: Any) -> Query:
        """Apply this filter to the query."""
        pass


class CustomerFilter(QueryFilter):
    """Filter interactions by customer ID."""
    
    def apply(self, query: Query, customer_id: UUID) -> Query:
        return query.filter(CommunicationInteraction.customer_id == customer_id)


class ContactFilter(QueryFilter):
    """Filter interactions by contact ID."""
    
    def apply(self, query: Query, contact_id: UUID) -> Query:
        return query.filter(CommunicationInteraction.contact_id == contact_id)


class AgentFilter(QueryFilter):
    """Filter interactions by assigned agent."""
    
    def apply(self, query: Query, agent_id: UUID) -> Query:
        return query.filter(CommunicationInteraction.assigned_agent_id == agent_id)


class StatusFilter(QueryFilter):
    """Filter interactions by status."""
    
    def apply(self, query: Query, status: InteractionStatus) -> Query:
        if isinstance(status, list):
            return query.filter(CommunicationInteraction.status.in_(status))
        return query.filter(CommunicationInteraction.status == status)


class ChannelFilter(QueryFilter):
    """Filter interactions by communication channel."""
    
    def apply(self, query: Query, channel: CommunicationChannel) -> Query:
        if isinstance(channel, list):
            return query.filter(CommunicationInteraction.channel.in_(channel))
        return query.filter(CommunicationInteraction.channel == channel)


class InteractionTypeFilter(QueryFilter):
    """Filter interactions by interaction type."""
    
    def apply(self, query: Query, interaction_type: InteractionType) -> Query:
        if isinstance(interaction_type, list):
            return query.filter(CommunicationInteraction.interaction_type.in_(interaction_type))
        return query.filter(CommunicationInteraction.interaction_type == interaction_type)


class DateRangeFilter(QueryFilter):
    """Filter interactions by date range."""
    
    def apply(self, query: Query, date_range: dict) -> Query:
        start_date = date_range.get('start')
        end_date = date_range.get('end')
        
        conditions = []
        if start_date:
            conditions.append(CommunicationInteraction.created_at >= start_date)
        if end_date:
            conditions.append(CommunicationInteraction.created_at <= end_date)
            
        if conditions:
            return query.filter(and_(*conditions))
        return query


class PriorityFilter(QueryFilter):
    """Filter interactions by priority level."""
    
    def apply(self, query: Query, priority: str) -> Query:
        if isinstance(priority, list):
            return query.filter(CommunicationInteraction.priority.in_(priority))
        return query.filter(CommunicationInteraction.priority == priority)


class TextSearchFilter(QueryFilter):
    """Filter interactions by text content search."""
    
    def apply(self, query: Query, search_text: str) -> Query:
        search_term = f"%{search_text.lower()}%"
        return query.filter(
            or_(
                func.lower(CommunicationInteraction.subject).like(search_term),
                func.lower(CommunicationInteraction.message_content).like(search_term),
                func.lower(CommunicationInteraction.internal_notes).like(search_term)
            )
        )


class TagsFilter(QueryFilter):
    """Filter interactions by tags."""
    
    def apply(self, query: Query, tags: List[str]) -> Query:
        # Assuming tags are stored as JSON or comma-separated
        if isinstance(tags, str):
            tags = [tags]
        
        conditions = []
        for tag in tags:
            conditions.append(
                func.json_contains(CommunicationInteraction.tags, f'"{tag}"')
            )
        
        if conditions:
            return query.filter(or_(*conditions))
        return query


class ResolutionFilter(QueryFilter):
    """Filter interactions by resolution status."""
    
    def apply(self, query: Query, is_resolved: bool) -> Query:
        return query.filter(CommunicationInteraction.is_resolved == is_resolved)


class EscalationFilter(QueryFilter):
    """Filter interactions by escalation status."""
    
    def apply(self, query: Query, is_escalated: bool) -> Query:
        return query.filter(CommunicationInteraction.is_escalated == is_escalated)


class ResponseTimeFilter(QueryFilter):
    """Filter interactions by response time criteria."""
    
    def apply(self, query: Query, response_time_criteria: dict) -> Query:
        operator = response_time_criteria.get('operator', 'gte')  # gte, lte, eq
        threshold_minutes = response_time_criteria.get('minutes', 0)
        
        # Calculate response time in minutes
        response_time_expr = func.timestampdiff(
            text('MINUTE'),
            CommunicationInteraction.created_at,
            CommunicationInteraction.first_response_at
        )
        
        if operator == 'gte':
            return query.filter(response_time_expr >= threshold_minutes)
        elif operator == 'lte':
            return query.filter(response_time_expr <= threshold_minutes)
        elif operator == 'eq':
            return query.filter(response_time_expr == threshold_minutes)
        
        return query


class TeamFilter(QueryFilter):
    """Filter interactions by assigned team."""
    
    def apply(self, query: Query, team_id: UUID) -> Query:
        # Join with agent table to filter by team
        from ..models import OmnichannelAgent
        return query.join(OmnichannelAgent).filter(OmnichannelAgent.team_id == team_id)


class SatisfactionScoreFilter(QueryFilter):
    """Filter interactions by customer satisfaction score."""
    
    def apply(self, query: Query, score_criteria: dict) -> Query:
        operator = score_criteria.get('operator', 'gte')
        score = score_criteria.get('score', 0)
        
        if operator == 'gte':
            return query.filter(CommunicationInteraction.customer_satisfaction_score >= score)
        elif operator == 'lte':
            return query.filter(CommunicationInteraction.customer_satisfaction_score <= score)
        elif operator == 'eq':
            return query.filter(CommunicationInteraction.customer_satisfaction_score == score)
        
        return query


# Filter registry for dynamic filter application
FILTER_REGISTRY = {
    'customer_id': CustomerFilter(),
    'contact_id': ContactFilter(),
    'agent_id': AgentFilter(),
    'assigned_agent_id': AgentFilter(),  # Alias
    'status': StatusFilter(),
    'channel': ChannelFilter(),
    'communication_channel': ChannelFilter(),  # Alias
    'interaction_type': InteractionTypeFilter(),
    'date_range': DateRangeFilter(),
    'start_date': DateRangeFilter(),  # Will be converted to date_range format
    'end_date': DateRangeFilter(),    # Will be converted to date_range format
    'priority': PriorityFilter(),
    'search': TextSearchFilter(),
    'search_text': TextSearchFilter(),  # Alias
    'tags': TagsFilter(),
    'is_resolved': ResolutionFilter(),
    'is_escalated': EscalationFilter(),
    'response_time': ResponseTimeFilter(),
    'team_id': TeamFilter(),
    'satisfaction_score': SatisfactionScoreFilter(),
}


def get_filter(filter_name: str) -> Optional[QueryFilter]:
    """Get a filter by name from the registry."""
    return FILTER_REGISTRY.get(filter_name)