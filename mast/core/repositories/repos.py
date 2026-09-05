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
    repo_gpgcheck: bool | None = None
    gpgkey: str = ""
    priority: int = 99
    keep_packages: bool = False
    path: str = ""
    other_options: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Use package GPG checking when repository GPG checking is unspecified."""
        if self.repo_gpgcheck is None:
            self.repo_gpgcheck = self.gpgcheck

    @property
    def filename(self) -> str:
        """Return the repository filename derived from its ID."""
        return f"{self.id}.repo"

    @property
    def url(self) -> str:
        """Return the URL (baseurl or mirrorlist)."""
        return self.baseurl or self.mirrorlist

    @staticmethod
    def parse_file(filepath: str) -> list["RepoEntry"]:
        """Parse all repository entries from a .repo file."""
        entries: list[RepoEntry] = []

        try:
            config = configparser.ConfigParser()
            config.optionxform = str  # Preserve case of keys
            config.read(filepath)

            for section in config.sections():
                entry = RepoEntry(id=section)
                has_repo_gpgcheck = False

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
                    elif key_lower == "repo_gpgcheck":
                        has_repo_gpgcheck = True
                        entry.repo_gpgcheck = value.lower() in ("1", "true", "yes", "on")
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

                if not has_repo_gpgcheck:
                    entry.repo_gpgcheck = entry.gpgcheck
                entries.append(entry)

        except Exception:
            pass

        return entries

    @staticmethod
    def load_repos() -> list["RepoEntry"]:
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
                        entries.extend(RepoEntry.parse_file(filepath))
        except PermissionError:
            raise PermissionError("Cannot read repository directory")

        entries.sort(key=lambda e: e.priority)
        return entries

    def save(
        self, use_pkexec: bool = True
    ) -> Literal["ok", "permission_denied", "pkexec_failed", "error"]:
        """Save this repository entry to its .repo file."""
        filepath = os.path.join(_repository_dir(), self.filename)

        # Check if we need to read existing content
        config = configparser.ConfigParser()
        config.optionxform = str
        if os.path.exists(filepath):
            config.read(filepath)

        # Remove existing section if present
        if self.id in config.sections():
            config.remove_section(self.id)

        # Add new section
        config[self.id] = {}

        # Set values
        if self.name:
            config[self.id]["name"] = self.name
        config[self.id]["enabled"] = "1" if self.enabled else "0"
        config[self.id]["autorefresh"] = "1" if self.autorefresh else "0"
        if self.baseurl:
            config[self.id]["baseurl"] = self.baseurl
        if self.mirrorlist:
            config[self.id]["mirrorlist"] = self.mirrorlist
        config[self.id]["type"] = self.type
        config[self.id]["gpgcheck"] = "1" if self.gpgcheck else "0"
        repo_gpgcheck = self.gpgcheck if self.repo_gpgcheck is None else self.repo_gpgcheck
        config[self.id]["repo_gpgcheck"] = "1" if repo_gpgcheck else "0"
        if self.gpgkey:
            config[self.id]["gpgkey"] = self.gpgkey
        config[self.id]["priority"] = str(self.priority)
        config[self.id]["keep_packages"] = "1" if self.keep_packages else "0"
        if self.path:
            config[self.id]["path"] = self.path

        # Add other options
        for key, value in self.other_options.items():
            config[self.id][key] = value

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

    def delete(
        self, use_pkexec: bool = True
    ) -> Literal["ok", "permission_denied", "pkexec_failed", "error"]:
        """Delete this repository entry from its .repo file."""
        filepath = os.path.join(_repository_dir(), self.filename)

        if not os.path.exists(filepath):
            return "ok"

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(filepath)

        if self.id not in config.sections():
            return "ok"

        # Remove the section
        config.remove_section(self.id)

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
