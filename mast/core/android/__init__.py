"""Android device management module."""

from mast.core.android.adb import (
    DeviceInfo,
    PackageInfo,
    get_device_info,
    is_adb_available,
    list_devices,
    list_packages,
)
from mast.core.android.package_filters import (
    PACKAGE_TYPE_ALL,
    PACKAGE_TYPE_FILTER_IDS,
    PACKAGE_TYPE_FILTER_OPTIONS,
    PACKAGE_TYPE_SYSTEM,
    PACKAGE_TYPE_USER,
    matches_package_type,
)

__all__ = [
    "DeviceInfo",
    "PackageInfo",
    "get_device_info",
    "is_adb_available",
    "list_devices",
    "list_packages",
    "PACKAGE_TYPE_ALL",
    "PACKAGE_TYPE_SYSTEM",
    "PACKAGE_TYPE_USER",
    "PACKAGE_TYPE_FILTER_IDS",
    "PACKAGE_TYPE_FILTER_OPTIONS",
    "matches_package_type",
]