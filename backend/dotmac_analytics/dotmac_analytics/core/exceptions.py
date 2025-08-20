"""
Custom exceptions for DotMac Analytics.
"""


class AnalyticsError(Exception):
    """Base exception for analytics operations."""
    pass


class ValidationError(AnalyticsError):
    """Raised when data validation fails."""
    pass


class NotFoundError(AnalyticsError):
    """Raised when requested resource is not found."""
    pass


class ConfigurationError(AnalyticsError):
    """Raised when configuration is invalid."""
    pass


class ProcessingError(AnalyticsError):
    """Raised when data processing fails."""
    pass


class QueryError(AnalyticsError):
    """Raised when query execution fails."""
    pass


class AuthorizationError(AnalyticsError):
    """Raised when authorization fails."""
    pass


class DataSourceError(AnalyticsError):
    """Raised when data source operations fail."""
    pass


class AggregationError(AnalyticsError):
    """Raised when data aggregation fails."""
    pass


class ReportError(AnalyticsError):
    """Raised when report generation fails."""
    pass
