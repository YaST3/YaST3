"""Shared telemetry utilities for Aptabase tracking."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from typing import Any

from aptabase import Aptabase

from mast.core import __version__
from mast.core.distro.os_release import read_os_release

APTABASE_APP_KEY = "A-EU-2272148359"

_CONFIG_DIR_NAME = "mast"
_CONFIG_FILE_NAME = "telemetry.json"


def _config_file_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_root = Path(xdg_config_home)
    else:
        config_root = Path.home() / ".config"
    return config_root / _CONFIG_DIR_NAME / _CONFIG_FILE_NAME


def get_telemetry_consent() -> bool | None:
    """Return telemetry consent state.

    Returns:
        True or False when user made a decision, None when unset.
    """
    config_path = _config_file_path()
    if not config_path.exists():
        return None

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    enabled = data.get("telemetry_enabled")
    if isinstance(enabled, bool):
        return enabled
    return None


def set_telemetry_consent(enabled: bool) -> None:
    """Persist telemetry consent."""
    config_path = _config_file_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"telemetry_enabled": enabled}
    config_path.write_text(json.dumps(payload), encoding="utf-8")


def is_telemetry_enabled() -> bool:
    """Return True when telemetry is explicitly enabled."""
    return get_telemetry_consent() is True


def track_event(event_name: str, props: dict[str, Any] | None = None) -> None:
    """Track one telemetry event if user consent is enabled."""
    if not is_telemetry_enabled():
        return

    worker = threading.Thread(
        target=_send_event_with_sdk,
        args=(event_name, _with_os_release_props(props)),
        daemon=True,
    )
    worker.start()


def _with_os_release_props(props: dict[str, Any] | None) -> dict[str, Any]:
    event_props: dict[str, Any] = dict(props or {})
    os_release_info = read_os_release()

    os_id = os_release_info.get("ID")
    if os_id:
        event_props["os_id"] = os_id

    os_version_id = os_release_info.get("VERSION_ID")
    if os_version_id:
        event_props["os_version_id"] = os_version_id

    return event_props


def _send_event_with_sdk(event_name: str, props: dict[str, Any] | None = None) -> None:
    asyncio.run(_track_and_flush(event_name, props))


async def _track_and_flush(event_name: str, props: dict[str, Any] | None = None) -> None:
    client = Aptabase(APTABASE_APP_KEY, app_version=__version__, is_debug=False)
    try:
        await client.start()
        await client.track(event_name, props)
        await client.flush()
        await client.stop()
    except Exception:
        # Telemetry should never break the main app flow.
        return


def track_app_started(app_variant: str) -> None:
    """Track one application startup."""
    track_event("app_started", {"app_variant": app_variant})


def track_module_started(app_variant: str, module_key: str) -> None:
    """Track one module launch."""
    track_event("module_started", {"app_variant": app_variant, "module": module_key})
