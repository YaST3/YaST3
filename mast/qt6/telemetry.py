"""Qt6 telemetry helpers."""

from mast.core.telemetry import track_app_started as _track_app_started
from mast.core.telemetry import track_module_started as _track_module_started


def track_app_started() -> None:
    """Track one Qt6 application startup."""
    _track_app_started("qt6")


def track_module_started(module_key: str) -> None:
    """Track one Qt6 module launch."""
    _track_module_started("qt6", module_key)