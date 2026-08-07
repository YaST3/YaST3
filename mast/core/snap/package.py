"""Snap package management core logic."""

from __future__ import annotations

import time
from dataclasses import dataclass

import snap_http
from snap_http import http as snap_http_http
from snap_http.types import COMPLETE_STATUSES

from mast.core.snap.snap import is_snap_installed, is_snapd_running


@dataclass
class SnapPackage:
    """Represents a snap package from either the store or local system."""

    name: str
    version: str = ""
    revision: str = ""
    tracking: str = ""
    publisher: str = ""
    summary: str = ""


def list_snap_packages() -> list[SnapPackage]:
    """List installed snap packages."""
    if not (is_snap_installed() and is_snapd_running()):
        return []

    try:
        response = snap_http.list()
    except snap_http_http.SnapdHttpException as e:
        raise RuntimeError(_extract_error(e)) from e

    result = response.result if isinstance(response.result, list) else []
    return [_snap_from_dict(snap) for snap in result if isinstance(snap, dict)]


def search_snap_packages(query: str = "") -> list[SnapPackage]:
    """Search snap packages from the remote catalog.

    When *query* is empty, featured snaps from the store are returned
    (equivalent to ``snap find`` without arguments).
    """
    if not (is_snap_installed() and is_snapd_running()):
        return []

    normalized_query = query.strip()

    try:
        if normalized_query:
            raw = snap_http_http._make_request(
                "/find", "GET", query_params={"q": normalized_query}
            )
        else:
            raw = snap_http_http._make_request(
                "/find", "GET", query_params={"scope": "wide", "section": "featured"}
            )
    except snap_http_http.SnapdHttpException as e:
        raise RuntimeError(_extract_error(e)) from e

    result = raw.get("result", []) if isinstance(raw, dict) else []
    if not isinstance(result, list):
        result = []
    return [_snap_from_dict(snap) for snap in result if isinstance(snap, dict)]


def install_snap_package(name: str) -> None:
    """Install a snap package."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Snap package name is required.")

    try:
        response = snap_http.install(normalized_name)
        if response.type == "async" and response.change:
            _wait_for_change(response.change)
    except snap_http_http.SnapdHttpException as e:
        raise RuntimeError(_extract_error(e)) from e


def uninstall_snap_package(name: str) -> None:
    """Uninstall a snap package."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Snap package name is required.")

    try:
        response = snap_http.remove(normalized_name)
        if response.type == "async" and response.change:
            _wait_for_change(response.change)
    except snap_http_http.SnapdHttpException as e:
        raise RuntimeError(_extract_error(e)) from e


def _wait_for_change(change_id: str) -> None:
    """Poll snapd change until it reaches a terminal status."""
    while True:
        response = snap_http.check_change(change_id)
        status = response.result.get("status", "") if isinstance(response.result, dict) else ""
        if status in COMPLETE_STATUSES:
            if status != "Done":
                err = response.result.get("err", "Operation failed") if isinstance(response.result, dict) else "Operation failed"
                raise RuntimeError(err)
            return
        time.sleep(0.5)


def _snap_from_dict(data: dict) -> SnapPackage:
    """Convert a snap dict from snapd API to SnapPackage."""
    publisher_data = data.get("publisher") or {}
    publisher = publisher_data.get("display-name") or publisher_data.get("username", "")
    return SnapPackage(
        name=data.get("name", ""),
        version=data.get("version", ""),
        revision=str(data.get("revision", "")),
        tracking=data.get("tracking-channel", ""),
        publisher=publisher,
        summary=data.get("summary", ""),
    )


def _extract_error(e: snap_http_http.SnapdHttpException) -> str:
    """Extract a human-readable error message from a SnapdHttpException."""
    if e.json and isinstance(e.json, dict):
        result = e.json.get("result", {})
        if isinstance(result, dict) and "message" in result:
            return result["message"]
    return str(e)
