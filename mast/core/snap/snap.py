"""Compatibility exports for Snap core helpers."""

import platform
import shutil


def is_snap_installed() -> bool:
    """Check whether the snap executable is available."""
    return shutil.which("snap") is not None

def install_snap_command() -> list[str]:
    """Return the command to install snap using the appropriate package manager with root permissions."""

    os_release = platform.freedesktop_os_release()
    os_id = os_release.get("ID")

    if os_id in ("debian", "ubuntu"):
        return ["pkexec", "bash", "-c", "apt-get update && apt-get install -y snapd"]

    if os_id == "opensuse-tumbleweed":
        return ["pkexec", "bash", "-c", "zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Tumbleweed/system:snappy.repo && zypper --non-interactive install -y snapd"]

    if os_id == "opensuse-slowroll":
        return ["pkexec", "bash", "-c", "zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Slowroll/system:snappy.repo && zypper --non-interactive install -y snapd"]

    if os_id == "opensuse-leap":
        return ["pkexec", "bash", "-c", f"zypper addrepo https://download.opensuse.org/repositories/system:snappy/openSUSE_Leap_{os_release.get("VERSION_ID")}/system:snappy.repo && zypper --non-interactive install -y snapd"]

    if os_id == "fedora":
        return ["pkexec", "dnf", "install", "-y", "snapd"]

    if os_id == "centos":
        return ["pkexec", "bash", "-c", "dnf install -y epel-release && dnf install -y snapd"]

    if os_id == "arch":
        return ["pkexec", "pacman", "-S", "--noconfirm", "snapd"]

    return ["pkexec", "zypper", "--non-interactive", "install", "-y", "snapd"]


def remove_snap_command() -> list[str]:
    """Return the command to remove snap using the appropriate package manager with root permissions."""

    os_release = platform.freedesktop_os_release()
    os_id = os_release.get("ID")

    if os_id in ("debian", "ubuntu"):
        return ["pkexec", "apt-get", "remove", "-y", "snapd"]

    if os_id in ("fedora", "centos"):
        return ["pkexec", "dnf", "remove", "-y", "snapd"]

    if os_id == "arch":
        return ["pkexec", "pacman", "-R", "--noconfirm", "snapd"]

    return ["pkexec", "zypper", "--non-interactive", "remove", "-y", "snapd"]
