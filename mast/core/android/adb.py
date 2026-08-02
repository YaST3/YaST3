"""ADB (Android Debug Bridge) helper functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ADB_TIMEOUT = 60


@dataclass(slots=True)
class DeviceInfo:
    serial: str
    name: str
    model: str
    manufacturer: str
    android_version: str
    api_level: str
    status: str


@dataclass(slots=True)
class PackageInfo:
    package_name: str
    app_name: str
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
                    model=tags.get("model", ""),
                    manufacturer="",
                    android_version="",
                    api_level="",
                    status=status,
                )
            )
            continue

        model = tags.get("model", "")
        device = tags.get("device", "")
        name = device or model

        try:
            props = get_device_properties(serial)
            devices.append(
                DeviceInfo(
                    serial=serial,
                    name=name,
                    model=props.get("ro.product.model", model),
                    manufacturer=props.get("ro.product.manufacturer", ""),
                    android_version=props.get("ro.build.version.release", ""),
                    api_level=props.get("ro.build.version.sdk", ""),
                    status=status,
                )
            )
        except Exception:
            devices.append(
                DeviceInfo(
                    serial=serial,
                    name=name,
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

    return DeviceInfo(
        serial=serial,
        name=device or model or props.get("ro.product.device", ""),
        model=props.get("ro.product.model", model),
        manufacturer=props.get("ro.product.manufacturer", ""),
        android_version=props.get("ro.build.version.release", ""),
        api_level=props.get("ro.build.version.sdk", ""),
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
        if line.startswith("package:") and "=" in line:
            pkg_name = line.split("=")[1].strip()
            disabled_pkgs.add(pkg_name)

    pm_output = str(
        _get_device(serial).shell(["pm", "list", "packages", "-f"], timeout=ADB_TIMEOUT)
    ).strip()
    path_by_pkg: dict[str, str] = {}
    is_system_by_pkg: dict[str, bool] = {}

    for line in pm_output.splitlines():
        line = line.strip()
        if not line.startswith("package:") or "=" not in line:
            continue

        try:
            path_part, pkg_name = line.split("=", 1)
            path = path_part[8:]
            path_by_pkg[pkg_name] = path
            is_system_by_pkg[pkg_name] = path.startswith("/system/") or path.startswith(
                "/product/"
            )
        except ValueError:
            continue

    dumpsys_output = str(
        _get_device(serial).shell(["dumpsys", "package"], timeout=ADB_TIMEOUT)
    ).strip()

    packages: list[PackageInfo] = []
    current_pkg = None
    app_name = ""
    version_name = ""
    version_code = ""

    for line in dumpsys_output.splitlines():
        line = line.strip()

        if line.startswith("Package [") and line.endswith("]"):
            if current_pkg and current_pkg in path_by_pkg:
                packages.append(
                    PackageInfo(
                        package_name=current_pkg,
                        app_name=app_name or current_pkg,
                        version_name=version_name,
                        version_code=version_code,
                        is_system=is_system_by_pkg.get(current_pkg, False),
                        is_disabled=current_pkg in disabled_pkgs,
                    )
                )

            current_pkg = line[9:-1].strip()
            app_name = ""
            version_name = ""
            version_code = ""
            continue

        if current_pkg is None:
            continue

        if line.startswith("versionName="):
            version_name = line.split("=", 1)[1]
        elif line.startswith("versionCode="):
            version_code = line.split("=", 1)[1]
        elif "label=" in line and not app_name:
            if "label=" in line:
                label_part = line.split("label=", 1)[1]
                if "=" in label_part:
                    label_part = label_part.split("=", 1)[1]
                app_name = label_part.strip().strip('"')

    if current_pkg and current_pkg in path_by_pkg:
        packages.append(
            PackageInfo(
                package_name=current_pkg,
                app_name=app_name or current_pkg,
                version_name=version_name,
                version_code=version_code,
                is_system=is_system_by_pkg.get(current_pkg, False),
                is_disabled=current_pkg in disabled_pkgs,
            )
        )

    return packages


def uninstall_package(serial: str, package_name: str, keep_data: bool = False) -> bool:
    args = ["pm", "uninstall"]
    if keep_data:
        args.append("-k")
    args.append(package_name)

    output = str(_get_device(serial).shell(args, timeout=ADB_TIMEOUT)).strip()
    return "Success" in output


def install_apk(serial: str, apk_path: str) -> bool:
    try:
        _get_device(serial).install(apk_path, silent=True, flags=["-r"])
        return True
    except Exception:
        return False


def is_adb_available() -> bool:
    try:
        _get_adb_client().server_version()
        return True
    except Exception:
        return False
