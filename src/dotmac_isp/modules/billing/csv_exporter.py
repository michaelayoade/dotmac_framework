"""
Minimal CSV exporter stubs for tests.
"""

from __future__ import annotations

from typing import Any


def export_invoices_csv(*args: Any, **kwargs: Any) -> str:  # noqa: ANN001
    # Use secure temp directory instead of hardcoded /tmp
    import tempfile
    return str(tempfile.mkdtemp() + "/invoices.csv")


def export_payments_csv(*args: Any, **kwargs: Any) -> str:  # noqa: ANN001
    # Use secure temp directory instead of hardcoded /tmp
    import tempfile
    return str(tempfile.mkdtemp() + "/payments.csv")


__all__ = ["export_invoices_csv", "export_payments_csv"]
