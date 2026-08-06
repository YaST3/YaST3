"""Compatibility exports for Snap core helpers."""

import shutil
import subprocess


def is_snap_installed() -> bool:
    """Check whether the snap executable is available."""
    return shutil.which("snap") is not None


def install_snap_pkexec() -> None:
    """Install snap using zypper with root permissions."""
    _run_command(["zypper", "--non-interactive", "install", "-y", "snapd"], use_pkexec=True)


def remove_snap_pkexec() -> None:
    """Remove snap using zypper with root permissions."""
    _run_command(["zypper", "--non-interactive", "remove", "-y", "snapd"], use_pkexec=True)


def _run_command(args: list[str], use_pkexec: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["pkexec", *args] if use_pkexec else args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(error)
    return result


__all__ = [
    "install_snap_pkexec",
    "is_snap_installed",
    "remove_snap_pkexec",
]