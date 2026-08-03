"""ADB (Android Debug Bridge) helper functions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

ADB_TIMEOUT = 60
PACKAGE_NAME_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$"
)


@dataclass(slots=True)
class DeviceInfo:
    serial: str
    name: str
    code_name: str
    model: str
    manufacturer: str
    android_version: str
    api_level: str
    status: str


@dataclass(slots=True)
class PackageInfo:
    package_name: str
    package_label: str
    version_name: str
    version_code: str
    is_system: bool
    is_disabled: bool


def _get_adb_client() -> Any:
    try:
        import adbutils
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "adbutils is not available. Please install adbutils and its dependencies."
        ) from exc

    return adbutils.adb


def _get_device(serial: str) -> Any:
    return _get_adb_client().device(serial=serial)


def _run_adb_command(serial: str | None, args: list[str]) -> str:
    if serial:
        output = _get_device(serial).shell(args, timeout=ADB_TIMEOUT)
    else:
        # Keep this helper for backward compatibility; host-side commands are
        # handled directly via adbutils client APIs where needed.
        raise ValueError("Host adb commands should use adbutils client APIs directly")
    return str(output).strip()


def _parse_pm_package_line(line: str) -> tuple[str, str] | None:
    if not line.startswith("package:") or "=" not in line:
        return None

    try:
        payload = line[len("package:") :]
        path, pkg_name = payload.rsplit("=", 1)
        pkg_name = pkg_name.strip()
        if not PACKAGE_NAME_RE.match(pkg_name):
            return None
        return path.strip(), pkg_name
    except ValueError:
        return None


def list_devices() -> list[DeviceInfo]:
    devices: list[DeviceInfo] = []

    for info in _get_adb_client().list(extended=True):
        serial = info.serial
        status = info.state
        tags = info.tags or {}

        if status != "device":
            devices.append(
                DeviceInfo(
                    serial=serial,
                    name=tags.get("device", ""),
                    code_name=tags.get("device", "") or "",
                    model=tags.get("model", ""),
                    manufacturer="",
                    android_version="",
                    api_level="",
                    status=status,
                )
            )
            continue

        model = tags.get("model") or ""
        device = tags.get("device") or ""
        name = device or model

        try:
            props = get_device_properties(serial)
            market_name = props.get("ro.product.marketname") or ""
            code_name = props.get("ro.product.device") or device
            resolved_model = props.get("ro.product.model") or model
            resolved_name = market_name or resolved_model or name
            devices.append(
                DeviceInfo(
                    serial=serial,
                    name=resolved_name,
                    code_name=code_name,
                    model=resolved_model,
                    manufacturer=props.get("ro.product.manufacturer") or "",
                    android_version=props.get("ro.build.version.release") or "",
                    api_level=props.get("ro.build.version.sdk") or "",
                    status=status,
                )
            )
        except Exception:
            devices.append(
                DeviceInfo(
                    serial=serial,
                    name=name,
                    code_name=device,
                    model=model,
                    manufacturer="",
                    android_version="",
                    api_level="",
                    status=status,
                )
            )

    return devices


def get_device_properties(serial: str) -> dict[str, str]:
    output = str(_get_device(serial).shell(["getprop"], timeout=ADB_TIMEOUT)).strip()
    props: dict[str, str] = {}

    for line in output.splitlines():
        line = line.strip()
        if not line or "[" not in line:
            continue

        try:
            key_part, value_part = line.split("]: [", 1)
            key = key_part[1:]
            value = value_part.rstrip("]")
            props[key] = value
        except ValueError:
            continue

    return props


def get_device_info(serial: str) -> DeviceInfo:
    props = get_device_properties(serial)

    output = _get_adb_client().list(extended=True)
    model = ""
    device = ""
    for info in output:
        if info.serial == serial:
            model = (info.tags or {}).get("model", "")
            device = (info.tags or {}).get("device", "")
            break

    market_name = props.get("ro.product.marketname") or ""
    code_name = props.get("ro.product.device") or device
    resolved_model = props.get("ro.product.model") or model

    return DeviceInfo(
        serial=serial,
        name=market_name or resolved_model or device or props.get("ro.product.device", ""),
        code_name=code_name,
        model=resolved_model,
        manufacturer=props.get("ro.product.manufacturer") or "",
        android_version=props.get("ro.build.version.release") or "",
        api_level=props.get("ro.build.version.sdk") or "",
        status="device",
    )


def list_packages(serial: str) -> list[PackageInfo]:
    disabled_output = str(
        _get_device(serial).shell(
            ["pm", "list", "packages", "-f", "-d"],
            timeout=ADB_TIMEOUT,
        )
    ).strip()
    disabled_pkgs: set[str] = set()

    for line in disabled_output.splitlines():
        line = line.strip()
        parsed = _parse_pm_package_line(line)
        if parsed:
            _, pkg_name = parsed
            disabled_pkgs.add(pkg_name)

    pm_output = str(
        _get_device(serial).shell(["pm", "list", "packages", "-f"], timeout=ADB_TIMEOUT)
    ).strip()
    path_by_pkg: dict[str, str] = {}
    is_system_by_pkg: dict[str, bool] = {}

    for line in pm_output.splitlines():
        line = line.strip()
        parsed = _parse_pm_package_line(line)
        if not parsed:
            continue

        path, pkg_name = parsed
        path_by_pkg[pkg_name] = path
        is_system_by_pkg[pkg_name] = path.startswith("/system/") or path.startswith(
            "/product/"
        )

    # Build a stable baseline from `pm list packages -f`, which is consistent
    # across Android versions.
    packages_by_name: dict[str, PackageInfo] = {}
    for pkg_name, path in path_by_pkg.items():
        packages_by_name[pkg_name] = PackageInfo(
            package_name=pkg_name,
            package_label=pkg_name,
            version_name="",
            version_code="",
            is_system=is_system_by_pkg.get(pkg_name, False),
            is_disabled=pkg_name in disabled_pkgs,
        )

    # Best-effort metadata enrichment from dumpsys. If format differs or command
    # output is unavailable, we still return the baseline package list above.
    try:
        dumpsys_output = str(
            _get_device(serial).shell(["dumpsys", "package"], timeout=ADB_TIMEOUT)
        ).strip()
    except Exception:
        return sorted(packages_by_name.values(), key=lambda p: p.package_name)

    current_pkg = None
    version_name = ""
    version_code = ""

    header_pattern = re.compile(r"^Package \[([^\]]+)\]")

    def _flush_current_package() -> None:
        if current_pkg and current_pkg in packages_by_name:
            pkg = packages_by_name[current_pkg]
            pkg.version_name = version_name
            pkg.version_code = version_code

    for line in dumpsys_output.splitlines():
        line = line.strip()

        header_match = header_pattern.match(line)
        if header_match:
            _flush_current_package()

            current_pkg = header_match.group(1).strip()
            version_name = ""
            version_code = ""
            continue

        if current_pkg is None:
            continue

        if line.startswith("versionName="):
            version_name = line.split("=", 1)[1]
        elif line.startswith("versionCode="):
            version_code = line.split("=", 1)[1]

    _flush_current_package()

    return sorted(packages_by_name.values(), key=lambda p: p.package_name)
def is_adb_available() -> bool:
    try:
        _get_adb_client().server_version()
        return True
    except Exception:
        return False
