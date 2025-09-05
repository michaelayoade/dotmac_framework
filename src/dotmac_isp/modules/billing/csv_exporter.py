"""
Minimal CSV exporter stubs for tests.
"""

from __future__ import annotations

from typing import Any


def export_invoices_csv(*args: Any, **kwargs: Any) -> str:  # noqa: ANN001
    return "/tmp/invoices.csv"


def export_payments_csv(*args: Any, **kwargs: Any) -> str:  # noqa: ANN001
    return "/tmp/payments.csv"


__all__ = ["export_invoices_csv", "export_payments_csv"]
