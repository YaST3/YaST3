"""Compatibility exports for Snap core helpers."""

import platform
import shutil
import subprocess


def is_snap_installed() -> bool:
    """Check whether the snap executable is available."""
    return shutil.which("snap") is not None

def install_snap_command() -> list[str]:
    """Return the command to install snap using zypper with root permissions."""

    os_release = platform.freedesktop_os_release()

    if os_release.get("ID") == "opensuse-tumbleweed":
        return ["pkexec", "bash", "-c", "zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Tumbleweed/system:snappy.repo && zypper --non-interactive install -y snapd"]

    if os_release.get("ID") == "opensuse-slowroll":
        return ["pkexec", "bash", "-c", "zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Slowroll/system:snappy.repo && zypper --non-interactive install -y snapd"]

    if os_release.get("ID") == "opensuse-leap":
        return ["pkexec", "bash", "-c", f"zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Leap_{os_release.get("VERSION_ID")}/system:snappy.repo && zypper --non-interactive install -y snapd"]

    if os_release.get("ID") == "fedora":
        return ["pkexec", "dnf", "install", "-y", "snapd"]

    return ["pkexec", "zypper", "--non-interactive", "install", "-y", "snapd"]

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