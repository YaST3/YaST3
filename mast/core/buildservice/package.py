"""Search and install packages published by the openSUSE Build Service."""

from __future__ import annotations

import platform
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass


OBS_API_URL = "https://api.opensuse.org/search/published/binary/id"
OBS_PROXY_URL = "https://opi-proxy.opensuse.org/"
OBS_DOWNLOAD_URL = "https://download.opensuse.org/repositories"
IGNORED_SUFFIXES = ("-debuginfo", "-debugsource", "-devel", "-lang", "-docs")


@dataclass(frozen=True)
class BuildServicePackage:
    """A binary package published by OBS."""

    name: str
    version: str
    release: str
    arch: str
    project: str
    repository: str
    package: str = ""

    @property
    def download_url(self) -> str:
        project = self.project.replace(":", ":/")
        return f"{OBS_DOWNLOAD_URL}/{project}/{self.repository}/{self.arch}/{self.name}.rpm"


def _distribution() -> str:
    values: dict[str, str] = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as stream:
            for line in stream:
                key, separator, value = line.rstrip().partition("=")
                if separator:
                    values[key] = value.strip('"')
    except OSError:
        pass

    name = values.get("NAME", "")
    version = values.get("VERSION_ID", "")
    if "Slowroll" in name:
        return "openSUSE:Slowroll"
    if "Tumbleweed" in name or "MicroOS" in name:
        return "openSUSE:Factory"
    if "Leap" in name:
        return f"openSUSE:Leap:{version}"
    if name.startswith("SLES") or name.startswith("SLE"):
        return f"SLE{version}"
    return "openSUSE:Factory"


def _architecture() -> str:
    machine = platform.machine()
    return {"amd64": "x86_64"}.get(machine, machine)


def _matches_query(name: str, query: str) -> bool:
    terms = [term.casefold() for term in query.split() if term.strip()]
    return bool(terms) and all(term in name.casefold() for term in terms)


def _is_compatible_repository(repository: str, architecture: str) -> bool:
    """Exclude OBS repositories built for a different CPU family."""
    repository_name = repository.casefold()
    repository_architectures = {
        "arm": ("arm", "aarch64"),
        "powerpc": ("ppc", "powerpc"),
        "zsystems": ("s390", "zsystems"),
        "riscv": ("risc", "riscv"),
        "loongarch": ("loongarch",),
    }
    for repository_family, markers in repository_architectures.items():
        if any(marker in repository_name for marker in markers):
            if repository_family == "arm":
                return architecture.startswith("arm") or architecture == "aarch64"
            if repository_family == "powerpc":
                return architecture.startswith("ppc") or architecture == "powerpc"
            if repository_family == "zsystems":
                return architecture.startswith("s390")
            if repository_family == "riscv":
                return architecture.startswith("risc")
            return architecture.startswith("loongarch")
    return True


def search_packages(query: str, *, timeout: float = 15.0) -> list[BuildServicePackage]:
    """Search OBS binaries matching all words in *query*."""
    normalized = query.strip()
    if not normalized:
        raise ValueError("Search query is required.")

    match = " and ".join(
        f"contains-ic(@name, '{term.replace(chr(39), chr(39) * 2)}')"
        for term in normalized.split()
    )
    match = f"({match}) and path/project='{_distribution()}'"
    url = f"{OBS_API_URL}?{urllib.parse.urlencode({'match': match, 'limit': 0})}"

    proxy_url = f"{OBS_PROXY_URL}?{urllib.parse.urlencode({'obs_api_link': url, 'obs_instance': 'openSUSE'})}"
    request = urllib.request.Request(proxy_url, headers={"User-Agent": "MaST/BuildService"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        root = ET.fromstring(response.read())

    distribution = _distribution()
    print(distribution)
    architecture = _architecture()
    packages: list[BuildServicePackage] = []
    seen: set[tuple[str, str, str]] = set()
    for binary in root.findall(".//binary"):
        data = binary.attrib
        name = data.get("name", "")
        arch = data.get("arch", "")
        project = data.get("project", "")
        repository = data.get("repository", "")
        if (
            not name
            or arch not in (architecture, "noarch")
            or not _is_compatible_repository(repository, architecture)
            or not _matches_query(name, normalized)
        ):
            continue
        if ":branches:" in project or name.endswith(IGNORED_SUFFIXES):
            continue
        key = (name, project, repository)
        if key in seen:
            continue
        seen.add(key)
        packages.append(
            BuildServicePackage(
                name=name,
                version=data.get("version", ""),
                release=data.get("release", ""),
                arch=arch,
                project=project,
                repository=repository,
                package=data.get("package", name),
            )
        )

    return sorted(packages, key=lambda package: (package.name.casefold(), package.project.casefold()))


def build_install_command(package: BuildServicePackage) -> list[str]:
    """Return a privileged, non-interactive zypper command for *package*."""
    return ["pkexec", "zypper", "--non-interactive", "install", "-y", package.download_url]