"""
Query builder patterns for omnichannel module.
Replaces complex search methods with fluent interface.
"""

from .interaction_query_builder import InteractionQueryBuilder
from .filter_builders import (
    CustomerFilter,
    AgentFilter,
    DateRangeFilter,
    StatusFilter,
    ChannelFilter,
    TextSearchFilter,
)
from .sort_builders import InteractionSortBuilder
from .pagination_builders import PaginationBuilder

__all__ = [
    'InteractionQueryBuilder',
    'CustomerFilter',
    'AgentFilter', 
    'DateRangeFilter',
    'StatusFilter',
    'ChannelFilter',
    'TextSearchFilter',
    'InteractionSortBuilder',
    'PaginationBuilder',
]