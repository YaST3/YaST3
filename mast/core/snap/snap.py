"""Compatibility exports for Snap core helpers."""

import os
import platform
import shutil


def is_snap_installed() -> bool:
    """Check whether the snap executable is available."""
    return shutil.which("snap") is not None


def is_snapd_running() -> bool:
    """Check whether the snapd daemon is running and reachable."""
    return os.path.exists("/run/snapd.socket")


def start_snapd_command() -> list[str]:
    """Return the command to enable and start the snapd service with root permissions."""
    return ["pkexec", "systemctl", "enable", "--now", "snapd.socket"]

def install_snap_command() -> list[str]:
    """Return the command to install and start snap using the appropriate package manager with root permissions."""

    os_release = platform.freedesktop_os_release()
    os_id = os_release.get("ID")

    if os_id in ("debian", "ubuntu"):
        return ["pkexec", "bash", "-c", "apt-get update && apt-get install -y snapd && systemctl enable --now snapd.socket"]

    if os_id == "opensuse-tumbleweed":
        return ["pkexec", "bash", "-c", "zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Tumbleweed/system:snappy.repo ; zypper --non-interactive install -y snapd && systemctl enable --now snapd.socket"]

    if os_id == "opensuse-slowroll":
        return ["pkexec", "bash", "-c", "zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Slowroll/system:snappy.repo ; zypper --non-interactive install -y snapd && systemctl enable --now snapd.socket"]

    if os_id == "opensuse-leap":
        return ["pkexec", "bash", "-c", f"zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Leap_{os_release.get("VERSION_ID")}/system:snappy.repo ; zypper --non-interactive install -y snapd && systemctl enable --now snapd.socket"]

    if os_id == "fedora":
        return ["pkexec", "bash", "-c", "dnf install -y snapd && systemctl enable --now snapd.socket"]

    if os_id == "centos":
        return ["pkexec", "bash", "-c", "dnf install -y epel-release && dnf install -y snapd && systemctl enable --now snapd.socket"]

    if os_id == "arch":
        return ["pkexec", "bash", "-c", "pacman -S --noconfirm snapd && systemctl enable --now snapd.socket"]

    return ["pkexec", "bash", "-c", "zypper --non-interactive install -y snapd && systemctl enable --now snapd.socket"]


def remove_snap_command() -> list[str]:
    """Return the command to stop and remove snap using the appropriate package manager with root permissions."""

    os_release = platform.freedesktop_os_release()
    os_id = os_release.get("ID")

    if os_id in ("debian", "ubuntu"):
        return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && apt-get remove -y snapd"]

    if os_id in ("fedora", "centos"):
        return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && dnf remove -y snapd"]

    if os_id == "arch":
        return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && pacman -R --noconfirm snapd"]

    return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && zypper --non-interactive remove -y snapd"]
