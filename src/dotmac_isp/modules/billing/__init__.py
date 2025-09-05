"""Billing module - Invoices, payments, and subscription management."""

import asyncio

from .csv_exporter import export_invoices_csv, export_payments_csv
from .pdf_generator import generate_invoice_pdf, generate_receipt_pdf
from .router import billing_router
from .shared_event_adapter import create_shared_billing_event_publisher
from .websocket_manager import initialize_websocket_manager, websocket_manager
from .websocket_router import billing_websocket_notifier, websocket_router

try:
    from dotmac.communications.events import EventBus

    _event_bus = EventBus()
    # For backward compatibility, we'll create the shared event publisher
    # In production, the system will be properly dependency-injected
    try:
        loop = asyncio.get_event_loop()
        event_publisher = loop.run_until_complete(
            create_shared_billing_event_publisher(_event_bus, websocket_manager)
        )
    except RuntimeError:
        # No event loop, will be initialized later
        event_publisher = None
except ImportError:
    # Fallback to original event publisher if shared services not available
    from .websocket_manager import event_publisher

# Optional file handler (requires aiofiles)
try:
    from .file_handler import file_upload_service
except ImportError:
    file_upload_service = None

__all__ = [
    "billing_router",
    "websocket_router",
    "billing_websocket_notifier",
    "websocket_manager",
    "event_publisher",
    "initialize_websocket_manager",
    "generate_invoice_pdf",
    "generate_receipt_pdf",
    "export_invoices_csv",
    "export_payments_csv",
    "file_upload_service",
]
