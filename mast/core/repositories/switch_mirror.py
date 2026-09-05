"""Switch mirror functionality for repositories."""

from __future__ import annotations

import argparse
import subprocess
import sys
import os

from mast.core.repositories.opensuse_mirrors import opensuse_mirrors
from mast.core.repositories.packman_mirrors import packman_mirrors
from mast.core.repositories.repos import RepoEntry, save_repo_entry


def switch_mirror(
    opensuse_mirror_url: str,
    packman_mirror_url: str,
) -> None:
    """Switch mirrors for openSUSE and Packman repositories.

    Args:
        opensuse_mirror_url: The new mirror URL for openSUSE repositories (with protocol).
        packman_mirror_url: The new mirror URL for Packman repository (with protocol).

    Returns:
        None.
    """
    opensuse_repos = ["repo-oss", "repo-non-oss", "repo-update", "repo-debug", "repo-source"]
    packman_repos = ["packman"]

    entries = RepoEntry.load_repos()

    modified_entries: list[RepoEntry] = []

    for entry in entries:
        if entry.id in opensuse_repos and entry.baseurl:
            new_baseurl = _replace_opensuse_mirror_prefix(entry.baseurl, opensuse_mirror_url)
            if new_baseurl != entry.baseurl:
                entry.baseurl = new_baseurl
                modified_entries.append(entry)
        elif entry.id in packman_repos and entry.baseurl:
            new_baseurl = _replace_packman_mirror_prefix(entry.baseurl, packman_mirror_url)
            if new_baseurl != entry.baseurl:
                entry.baseurl = new_baseurl
                modified_entries.append(entry)

    if not modified_entries:
        return

    for entry in modified_entries:
        save_repo_entry(entry)


def _replace_opensuse_mirror_prefix(url: str, new_prefix: str) -> str:
    """Replace the openSUSE mirror prefix in a URL with a new prefix.

    Three-tier fallback strategy:
    1. Match known openSUSE mirror patterns
    2. Search for '/opensuse/' in URL path and replace everything before it
    3. Fall back to replacing the domain with new prefix

    Args:
        url: The original repository URL.
        new_prefix: The new openSUSE mirror URL prefix (with protocol).

    Returns:
        The URL with the new mirror prefix.
    """
    url_lower = url.lower()
    patterns = []

    for mirror in opensuse_mirrors:
        for proto in mirror.protocols:
            patterns.append(f"{proto}://{mirror.url}".lower())

    for pattern in patterns:
        if url_lower.startswith(pattern):
            remainder = url[len(pattern):]
            if remainder and not remainder.startswith("/"):
                remainder = "/" + remainder
            return new_prefix.rstrip("/") + remainder

    idx = url_lower.find('/opensuse/')
    if idx != -1:
        remainder = url[idx + len('/opensuse/'):]
        return new_prefix.rstrip("/") + "/" + remainder

    parsed = url.split("/", 3)
    if len(parsed) >= 4:
        path = parsed[3]
        return new_prefix.rstrip("/") + "/" + path

    return url


def _replace_packman_mirror_prefix(url: str, new_prefix: str) -> str:
    """Replace the Packman mirror prefix in a URL with a new prefix.

    Three-tier fallback strategy:
    1. Match known Packman mirror patterns
    2. Search for '/packman/' in URL path and replace everything before it
    3. Fall back to replacing the domain with new prefix

    Args:
        url: The original repository URL.
        new_prefix: The new Packman mirror URL prefix (with protocol).

    Returns:
        The URL with the new mirror prefix.
    """
    url_lower = url.lower()
    patterns = []

    for mirror in packman_mirrors:
        for proto in mirror.protocols:
            patterns.append(f"{proto}://{mirror.url}".lower())

    for pattern in patterns:
        if url_lower.startswith(pattern):
            remainder = url[len(pattern):]
            if remainder and not remainder.startswith("/"):
                remainder = "/" + remainder
            return new_prefix.rstrip("/") + remainder

    idx = url_lower.find('/packman/')
    if idx != -1:
        remainder = url[idx + len('/packman/'):]
        return new_prefix.rstrip("/") + "/" + remainder

    parsed = url.split("/", 3)
    if len(parsed) >= 4:
        path = parsed[3]
        return new_prefix.rstrip("/") + "/" + path

    return url

def _status_to_exit_code(status: str) -> int:
    """Convert a status string to an exit code.

    Args:
        status: The status string.

    Returns:
        The corresponding exit code.
    """
    status_map = {
        "ok": 0,
        "permission_denied": 1,
        "pkexec_failed": 2,
        "error": 3,
    }
    return status_map.get(status, 3)


def switch_mirror_pkexec(
    opensuse_mirror_url: str,
    packman_mirror_url: str,
) -> str:
    """Switch mirrors for openSUSE and Packman repositories using pkexec.

    Args:
        opensuse_mirror_url: The new mirror URL for openSUSE repositories (with protocol).
        packman_mirror_url: The new mirror URL for Packman repository (with protocol).

    Returns:
        The status string: "ok", "permission_denied", "pkexec_failed", or "error".
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", '..')) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        ["pkexec", '--keep-cwd', sys.executable, '-m', 'mast.core.repositories.switch_mirror', '--opensuse', opensuse_mirror_url, '--packman', packman_mirror_url],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return "ok"
    elif result.returncode == 1:
        return "permission_denied"
    elif result.returncode == 2:
        return "pkexec_failed"
    else:
        return "error"

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Switch mirrors for openSUSE and Packman repositories.")
    parser.add_argument('--opensuse', type=str, required=True, help="New openSUSE mirror URL (with protocol).")
    parser.add_argument('--packman', type=str, required=True, help="New Packman mirror URL (with protocol).")
    args = parser.parse_args()

    switch_mirror(args.opensuse, args.packman)
    sys.exit(0)
