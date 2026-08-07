"""Flatpak runtime management core logic."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal


@dataclass
class FlatpakRuntime:
    """Represents an installed Flatpak runtime."""

    runtime_id: str
    remote: str
    name: str = ""
    description: str = ""
    version: str = ""
    branch: str = ""
    installed_size: str = ""
    scope: Literal["system", "user"] = "system"


def list_flatpak_runtimes() -> list[FlatpakRuntime]:
    """List installed Flatpak runtimes."""
    if not _is_flatpak_installed():
        return []

    result = _run_command(
        [
            "flatpak",
            "list",
            "--runtime",
            "--columns=application,name,description,version,branch,origin,size,installation",
        ]
    )

    runtimes: list[FlatpakRuntime] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split("\t")
        runtime_id = parts[0].strip() if len(parts) > 0 else ""
        if not runtime_id:
            continue

        name = parts[1].strip() if len(parts) > 1 else ""
        description = parts[2].strip() if len(parts) > 2 else ""
        version = parts[3].strip() if len(parts) > 3 else ""
        branch = parts[4].strip() if len(parts) > 4 else ""
        remote = parts[5].strip() if len(parts) > 5 else ""
        installed_size = parts[6].strip() if len(parts) > 6 else ""
        installation = parts[7].strip().lower() if len(parts) > 7 else "system"
        scope: Literal["system", "user"] = "user" if "user" in installation else "system"

        runtimes.append(
            FlatpakRuntime(
                runtime_id=runtime_id,
                remote=remote,
                name=name,
                description=description,
                version=version,
                branch=branch,
                installed_size=installed_size,
                scope=scope,
            )
        )

    return runtimes


def uninstall_flatpak_runtime(runtime_id: str, scope: Literal["system", "user"] = "system") -> None:
    """Uninstall a Flatpak runtime."""
    normalized_runtime = runtime_id.strip()
    if not normalized_runtime:
        raise ValueError("Runtime id is required.")

    args = ["flatpak", "uninstall", "-y", f"--{scope}", normalized_runtime]
    _run_command(args, use_pkexec=scope == "system")


def _run_command(args: list[str], use_pkexec: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["pkexec", *args] if use_pkexec else args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(error)
    return result


def _is_flatpak_installed() -> bool:
    return shutil.which("flatpak") is not None
