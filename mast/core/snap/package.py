"""Snap package management core logic."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from mast.core.snap.snap import is_snap_installed, is_snapd_running


@dataclass
class SnapPackage:
    """Represents a snap package from either the store or local system."""

    name: str
    version: str = ""
    revision: str = ""
    tracking: str = ""
    publisher: str = ""
    notes: str = ""
    summary: str = ""


def list_snap_packages() -> list[SnapPackage]:
    """List installed snap packages."""
    if not (is_snap_installed() and is_snapd_running()):
        return []

    result = _run_command(["snap", "list"])
    return _parse_installed_packages(result.stdout)


def search_snap_packages(query: str = "") -> list[SnapPackage]:
    """Search snap packages from the remote catalog."""
    if not (is_snap_installed() and is_snapd_running()):
        return []

    args = ["snap", "find"]
    normalized_query = query.strip()
    if normalized_query:
        args.append(normalized_query)

    result = _run_command(args)
    return _parse_search_packages(result.stdout)


def install_snap_package(name: str) -> None:
    """Install a snap package."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Snap package name is required.")

    _run_command(["snap", "install", normalized_name], use_pkexec=True)


def uninstall_snap_package(name: str) -> None:
    """Uninstall a snap package."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Snap package name is required.")

    _run_command(["snap", "remove", normalized_name], use_pkexec=True)


def _parse_installed_packages(output: str) -> list[SnapPackage]:
    packages: list[SnapPackage] = []
    for fields in _parse_table(output, maxsplit=5):
        if len(fields) < 6:
            continue
        packages.append(
            SnapPackage(
                name=fields[0],
                version=fields[1],
                revision=fields[2],
                tracking=fields[3],
                publisher=fields[4],
                notes=fields[5],
            )
        )
    return packages


def _parse_search_packages(output: str) -> list[SnapPackage]:
    packages: list[SnapPackage] = []
    for fields in _parse_table(output, maxsplit=4):
        if len(fields) < 5:
            continue
        packages.append(
            SnapPackage(
                name=fields[0],
                version=fields[1],
                publisher=fields[2],
                notes=fields[3],
                summary=fields[4],
            )
        )
    return packages


def _parse_table(output: str, maxsplit: int) -> list[list[str]]:
    rows: list[list[str]] = []
    header_skipped = False

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if not header_skipped:
            header_skipped = True
            continue
        if line.startswith("No matching snaps"):
            continue

        fields = [field.strip() for field in re.split(r"\s{2,}", line.strip(), maxsplit=maxsplit)]
        if fields:
            rows.append(fields)

    return rows


def _run_command(args: list[str], use_pkexec: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["pkexec", *args] if use_pkexec else args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(error)
    return result