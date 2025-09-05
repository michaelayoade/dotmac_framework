"""Dashboard models for analytics."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ChartType(str, Enum):
    """Chart type enumeration."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    GAUGE = "gauge"
    TABLE = "table"


@dataclass
class ChartWidget:
    """Dashboard chart widget."""

    id: str
    title: str
    chart_type: ChartType
    data_source: str
    config: dict[str, Any]
    position: dict[str, int] = None  # x, y, width, height

    def __post_init__(self):
        """Post Init   operation."""
        if self.position is None:
            self.position = {"x": 0, "y": 0, "width": 4, "height": 3}


@dataclass
class Dashboard:
    """Analytics dashboard model."""

    id: str
    name: str
    description: str = ""
    widgets: list[ChartWidget] = None
    is_public: bool = False
    owner_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Post Init   operation."""
        if self.widgets is None:
            self.widgets = []

    def add_widget(self, widget: ChartWidget):
        """Add a widget to the dashboard."""
        self.widgets.append(widget)

    def remove_widget(self, widget_id: str):
        """Remove a widget from the dashboard."""
        self.widgets = [w for w in self.widgets if w.id != widget_id]

    def get_widget(self, widget_id: str) -> Optional[ChartWidget]:
        """Get a widget by ID."""
        for widget in self.widgets:
            if widget.id == widget_id:
                return widget
        return None


# Alias for backward compatibility
Widget = ChartWidget
