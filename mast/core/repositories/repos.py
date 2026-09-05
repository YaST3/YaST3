"""Repository file reading and writing logic."""

from __future__ import annotations

import configparser
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Literal

from mast.core.distro import read_os_release


def _repository_dir() -> str:
    """Return the repository directory for the current distribution."""
    if read_os_release().get("ID", "").lower() == "fedora":
        return "/etc/yum.repos.d"
    return "/etc/zypp/repos.d"


@dataclass
class RepoEntry:
    """Represents a single repository entry."""

    id: str
    name: str = ""
    enabled: bool = True
    autorefresh: bool = True
    baseurl: str = ""
    mirrorlist: str = ""
    type: str = "rpm-md"
    gpgcheck: bool = True
    gpgkey: str = ""
    priority: int = 99
    keep_packages: bool = False
    path: str = ""
    other_options: dict = field(default_factory=dict)

    @property
    def filename(self) -> str:
        """Return the repository filename derived from its ID."""
        return f"{self.id}.repo"

    @property
    def url(self) -> str:
        """Return the URL (baseurl or mirrorlist)."""
        return self.baseurl or self.mirrorlist


def parse_repo_file(filepath: str) -> list[RepoEntry]:
    """Parse a single .repo file using configparser."""
    entries: list[RepoEntry] = []

    try:
        config = configparser.ConfigParser()
        config.optionxform = str  # Preserve case of keys
        config.read(filepath)

        for section in config.sections():
            entry = RepoEntry(id=section)

            for key, value in config.items(section):
                key_lower = key.lower()

                if key_lower == "name":
                    entry.name = value
                elif key_lower == "enabled":
                    entry.enabled = value.lower() in ("1", "true", "yes", "on")
                elif key_lower == "autorefresh":
                    entry.autorefresh = value.lower() in ("1", "true", "yes", "on")
                elif key_lower == "baseurl":
                    entry.baseurl = value
                elif key_lower == "mirrorlist":
                    entry.mirrorlist = value
                elif key_lower == "type":
                    entry.type = value
                elif key_lower == "gpgcheck":
                    entry.gpgcheck = value.lower() in ("1", "true", "yes", "on")
                elif key_lower == "gpgkey":
                    entry.gpgkey = value
                elif key_lower == "priority":
                    try:
                        entry.priority = int(value)
                    except ValueError:
                        pass
                elif key_lower == "keep_packages":
                    entry.keep_packages = value.lower() in ("1", "true", "yes", "on")
                elif key_lower == "path":
                    entry.path = value
                else:
                    entry.other_options[key] = value

            entries.append(entry)

    except Exception:
        pass

    return entries


def load_repos() -> list[RepoEntry]:
    """Load all repositories from the system repository directory."""
    entries: list[RepoEntry] = []
    repos_dir = _repository_dir()

    if not os.path.isdir(repos_dir):
        return entries

    try:
        for filename in os.listdir(repos_dir):
            if filename.endswith(".repo"):
                filepath = os.path.join(repos_dir, filename)
                if os.path.isfile(filepath):
                    entries.extend(parse_repo_file(filepath))
    except PermissionError:
        raise PermissionError("Cannot read repository directory")

    # Sort by priority (ascending, lower number = higher priority)
    entries.sort(key=lambda e: e.priority)
    return entries


def save_repo_entry(
    entry: RepoEntry, use_pkexec: bool = True
) -> Literal["ok", "permission_denied", "pkexec_failed", "error"]:
    """Save a single repository entry to its .repo file."""
    filepath = os.path.join(_repository_dir(), entry.filename)

    # Check if we need to read existing content
    config = configparser.ConfigParser()
    config.optionxform = str
    if os.path.exists(filepath):
        config.read(filepath)

    # Remove existing section if present
    if entry.id in config.sections():
        config.remove_section(entry.id)

    # Add new section
    config[entry.id] = {}

    # Set values
    if entry.name:
        config[entry.id]["name"] = entry.name
    config[entry.id]["enabled"] = "1" if entry.enabled else "0"
    config[entry.id]["autorefresh"] = "1" if entry.autorefresh else "0"
    if entry.baseurl:
        config[entry.id]["baseurl"] = entry.baseurl
    if entry.mirrorlist:
        config[entry.id]["mirrorlist"] = entry.mirrorlist
    config[entry.id]["type"] = entry.type
    config[entry.id]["gpgcheck"] = "1" if entry.gpgcheck else "0"
    if entry.gpgkey:
        config[entry.id]["gpgkey"] = entry.gpgkey
    config[entry.id]["priority"] = str(entry.priority)
    config[entry.id]["keep_packages"] = "1" if entry.keep_packages else "0"
    if entry.path:
        config[entry.id]["path"] = entry.path

    # Add other options
    for key, value in entry.other_options.items():
        config[entry.id][key] = value

    # Try direct write first
    try:
        with open(filepath, "w") as f:
            config.write(f)
        return "ok"
    except PermissionError:
        if not use_pkexec:
            return "permission_denied"
    except Exception:
        return "error"

    # Use pkexec to get root permission
    try:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".repo", delete=False) as tmp:
            tmp_path = tmp.name
            config.write(tmp)
            os.chmod(tmp_path, 0o664)

        result = subprocess.run(
            ["pkexec", "cp", tmp_path, filepath],
            capture_output=True,
            text=True,
        )

        subprocess.run(["rm", "-f", tmp_path], capture_output=True)

        if result.returncode == 0:
            return "ok"
        else:
            return "pkexec_failed"
    except Exception:
        return "error"


def delete_repo_entry(
    entry: RepoEntry, use_pkexec: bool = True
) -> Literal["ok", "permission_denied", "pkexec_failed", "error"]:
    """Delete a repository entry from its .repo file."""
    filepath = os.path.join(_repository_dir(), entry.filename)

    if not os.path.exists(filepath):
        return "ok"

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(filepath)

    if entry.id not in config.sections():
        return "ok"

    # Remove the section
    config.remove_section(entry.id)

    # If no sections remain, delete the file
    if not config.sections():
        try:
            os.remove(filepath)
            return "ok"
        except PermissionError:
            if not use_pkexec:
                return "permission_denied"
        except Exception:
            return "error"

        # Use pkexec
        try:
            result = subprocess.run(
                ["pkexec", "rm", filepath],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return "ok"
            else:
                return "pkexec_failed"
        except Exception:
            return "error"

    # Otherwise, write remaining sections
    try:
        with open(filepath, "w") as f:
            config.write(f)
        return "ok"
    except PermissionError:
        if not use_pkexec:
            return "permission_denied"
    except Exception:
        return "error"

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".repo", delete=False) as tmp:
            config.write(tmp)
            tmp_path = tmp.name

        result = subprocess.run(
            ["pkexec", "cp", tmp_path, filepath],
            capture_output=True,
            text=True,
        )

        subprocess.run(["rm", "-f", tmp_path], capture_output=True)

        if result.returncode == 0:
            return "ok"
        else:
            return "pkexec_failed"
    except Exception:
        return "error"
