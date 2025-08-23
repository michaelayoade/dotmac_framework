"""Notification API routers."""

from .template_router import template_router
from .rule_router import rule_router
from .notification_router import notification_router
from .preference_router import preference_router
from .delivery_router import delivery_router
from .admin_router import admin_router

__all__ = [
    "template_router",
    "rule_router",
    "notification_router",
    "preference_router",
    "delivery_router",
    "admin_router",
]
