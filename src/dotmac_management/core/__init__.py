"""
DotMac Management Platform Core Module

This module provides core functionality for the management platform including
configuration, database, and shared utilities.
"""

from .settings import ManagementPlatformSettings, get_settings

__all__ = [
    "ManagementPlatformSettings",
    "get_settings",
]
