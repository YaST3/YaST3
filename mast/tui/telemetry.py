"""TUI telemetry helpers."""

from mast.core.telemetry import track_app_started as _track_app_started
from mast.core.telemetry import track_module_started as _track_module_started


def track_app_started() -> None:
    """Track one TUI application startup."""
    _track_app_started("tui")


def track_module_started(module_key: str) -> None:
    """Track one TUI module launch."""
    _track_module_started("tui", module_key)