"""Snapper snapshot listing and command helpers."""

from __future__ import annotations

import json
import subprocess

from dataclasses import dataclass


@dataclass(slots=True)
class SnapshotEntry:
    """Represents one snapper snapshot row."""

    number: int
    snapshot_type: str
    date: str
    user: str
    used_space: int | None
    description: str
    cleanup: str


def _to_int(value: object, default: int = -1) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _to_optional_int(value: object) -> int | None:
    if value is None:
        return None
    parsed = _to_int(value, default=-1)
    if parsed < 0:
        return None
    return parsed


def _run_snapper_json(command: list[str], timeout: int | None = None) -> list[dict[str, object]]:
    result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout)
    payload = result.stdout.strip()
    if not payload:
        return []

    data = json.loads(payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        rows = data.get("snapshots") or data.get("data") or []
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
    return []


def _parse_snapshot_entry(item: dict[str, object]) -> SnapshotEntry:
    used_space = _to_optional_int(item.get("used-space", item.get("used_space")))
    return SnapshotEntry(
        number=_to_int(item.get("number", item.get("id", item.get("#", -1)))),
        snapshot_type=str(item.get("type", "")),
        date=str(item.get("date", item.get("timestamp", ""))),
        user=str(item.get("user", "")),
        used_space=used_space,
        description=str(item.get("description", "")),
        cleanup=str(item.get("cleanup", "")),
    )


def list_snapshots(config: str = "root", timeout: int | None = None) -> list[SnapshotEntry]:
    """List snapshots for the selected snapper config."""

    rows = _run_snapper_json(["pkexec", "snapper", "-c", config, "--jsonout", "list"], timeout=timeout)
    snapshots = [_parse_snapshot_entry(item) for item in rows]
    snapshots.sort(key=lambda entry: entry.number, reverse=True)
    return snapshots


def build_snapshot_create_command(description: str, config: str = "root") -> list[str]:
    """Build a command that creates a new snapshot using snapper."""

    clean_description = description.strip()
    if not clean_description:
        raise ValueError("Snapshot description cannot be empty")
    return ["pkexec", "snapper", "-c", config, "create", "--description", clean_description]


def build_snapshot_delete_command(snapshot_number: int, config: str = "root") -> list[str]:
    """Build a command that deletes a snapshot by number."""

    if snapshot_number <= 0:
        raise ValueError("Snapshot number must be a positive integer")
    return ["pkexec", "snapper", "-c", config, "delete", str(snapshot_number)]


def build_snapshot_list_command(config: str = "root") -> list[str]:
    """Build a command that lists snapshots using snapper."""

    return ["pkexec", "snapper", "-c", config, "--jsonout", "list"]


def parse_snapshots_from_json(json_output: str) -> list[SnapshotEntry]:
    """Parse snapshot JSON output into a list of SnapshotEntry objects."""

    if not json_output.strip():
        return []

    data = json.loads(json_output)

    if isinstance(data, list):
        rows = [item for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        rows = data.get("snapshots") or data.get("data")
        if rows is None:
            for value in data.values():
                if isinstance(value, list):
                    rows = value
                    break
        if isinstance(rows, list):
            rows = [item for item in rows if isinstance(item, dict)]
        else:
            rows = []
    else:
        rows = []

    snapshots = [_parse_snapshot_entry(item) for item in rows]
    snapshots.sort(key=lambda entry: entry.number, reverse=True)
    return snapshots



