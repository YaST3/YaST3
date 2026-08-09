"""Compatibility exports for Snap core helpers."""

import os
import platform
import shutil
import subprocess

import snap_http
from bytesize import Size
from snap_http import http as snap_http_http


SNAP_CACHE_DIR = "/var/lib/snapd/cache/"
SNAP_SNAPS_DIR = "/var/lib/snapd/snaps/"


def is_snap_installed() -> bool:
    """Check whether the snap executable is available."""
    return shutil.which("snap") is not None


def is_snapd_running() -> bool:
    """Check whether the snapd daemon is running and reachable."""
    return os.path.exists("/run/snapd.socket")


def start_snapd_command() -> list[str]:
    """Return the command to enable and start the snapd service with root permissions."""
    return ["pkexec", "systemctl", "enable", "--now", "snapd.socket"]


def get_snap_cache_size() -> str:
    """Return the total size of the snap cache directory in human-readable format."""
    total = 0
    if os.path.isdir(SNAP_CACHE_DIR):
        for dirpath, _dirnames, filenames in os.walk(SNAP_CACHE_DIR):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return Size(total).human_readable()


def clear_snap_cache_command() -> list[str]:
    """Return the command to clear the snap cache directory with root permissions."""
    return ["pkexec", "bash", "-c", f"rm -rf {SNAP_CACHE_DIR}*"]


def get_snap_retain_count() -> int:
    """Return the current number of snap revisions retained per package."""
    try:
        response = snap_http.get_conf("system", keys=["refresh.retain"])
        result = response.result
        if isinstance(result, dict):
            refresh = result.get("refresh", {})
            if isinstance(refresh, dict):
                return int(refresh.get("retain", 2))
    except (snap_http_http.SnapdHttpException, ValueError, TypeError):
        pass
    return 2


def set_snap_retain_command(count: int) -> list[str]:
    """Return the command to set the maximum number of snap revisions to retain."""
    return ["pkexec", "snap", "set", "system", f"refresh.retain={count}"]


def get_snap_old_versions_size() -> str:
    """Return the total size of disabled (old) snap revisions in human-readable format."""
    try:
        result = subprocess.run(
            ["snap", "list", "--all"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return Size(0).human_readable()
    except subprocess.SubprocessError:
        return Size(0).human_readable()

    total = 0
    for line in result.stdout.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 6 and parts[-1] == "disabled":
            name = parts[0]
            rev = parts[2]
            snap_file = os.path.join(SNAP_SNAPS_DIR, f"{name}_{rev}.snap")
            try:
                total += os.path.getsize(snap_file)
            except OSError:
                pass
    return Size(total).human_readable()


def clear_snap_old_versions_command() -> list[str]:
    """Return the command to remove all disabled (old) snap revisions."""
    return [
        "pkexec", "bash", "-c",
        "snap list --all | awk '/disabled/{print $1, $3}' | "
        "while read name rev; do snap remove \"$name\" --revision=\"$rev\"; done",
    ]


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
        return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && apt-get remove -y snapd && rm -rf /var/lib/snapd /var/snap"]

    if os_id in ("fedora", "centos"):
        return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && dnf remove -y snapd && rm -rf /var/lib/snapd /var/snap"]

    if os_id == "arch":
        return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && pacman -R --noconfirm snapd && rm -rf /var/lib/snapd /var/snap"]

    return ["pkexec", "bash", "-c", "systemctl disable --now snapd.socket && zypper --non-interactive remove -y snapd && rm -rf /var/lib/snapd /var/snap"]
