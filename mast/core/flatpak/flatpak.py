"""Compatibility exports for Flatpak core helpers."""

import os
import shutil
import subprocess

from bytesize import Size


FLATPAK_CACHE_DIR = "/var/cache/flatpak/"


def is_flatpak_installed() -> bool:
    """Check whether the flatpak executable is available."""
    return shutil.which("flatpak") is not None


def install_flatpak_pkexec() -> None:
    """Install Flatpak using zypper with root permissions."""
    _run_command(["zypper", "--non-interactive", "install", "-y", "flatpak"], use_pkexec=True)


def remove_flatpak_pkexec() -> None:
    """Remove Flatpak using zypper with root permissions."""
    _run_command(["zypper", "--non-interactive", "remove", "-y", "flatpak"], use_pkexec=True)


def _run_command(args: list[str], use_pkexec: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["pkexec", *args] if use_pkexec else args
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(error)
    return result


def get_flatpak_cache_size() -> str:
    """Return the total size of the flatpak cache directory in human-readable format."""
    total = 0
    if os.path.isdir(FLATPAK_CACHE_DIR):
        for dirpath, _dirnames, filenames in os.walk(FLATPAK_CACHE_DIR):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return Size(total).human_readable()


def clear_flatpak_cache_command() -> list[str]:
    """Return the command to clear the flatpak cache directory with root permissions."""
    return ["pkexec", "bash", "-c", f"rm -rf {FLATPAK_CACHE_DIR}*"]


__all__ = [
    "clear_flatpak_cache_command",
    "get_flatpak_cache_size",
    "install_flatpak_pkexec",
    "is_flatpak_installed",
    "remove_flatpak_pkexec",
]
