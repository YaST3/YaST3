"""Shared package filter definitions for Android package views."""

from mast.core.android.bloatware_config import (
    BLOATWARE_PACKAGE_IDS,
    BLOATWARE_PACKAGE_PREFIXES,
)
from mast.core.i18n import _

PACKAGE_TYPE_ALL = "all"
PACKAGE_TYPE_SYSTEM = "system"
PACKAGE_TYPE_USER = "user"
PACKAGE_TYPE_BLOATWARE = "bloatware"

PACKAGE_TYPE_FILTER_IDS = (
    PACKAGE_TYPE_ALL,
    PACKAGE_TYPE_SYSTEM,
    PACKAGE_TYPE_USER,
    PACKAGE_TYPE_BLOATWARE,
)

PACKAGE_TYPE_FILTER_OPTIONS = [
    (PACKAGE_TYPE_ALL, _("All")),
    (PACKAGE_TYPE_SYSTEM, _("System")),
    (PACKAGE_TYPE_USER, _("User")),
    (PACKAGE_TYPE_BLOATWARE, _("Bloatware")),
]


def is_bloatware_package(package_name: str) -> bool:
    if package_name in BLOATWARE_PACKAGE_IDS:
        return True
    return package_name.startswith(BLOATWARE_PACKAGE_PREFIXES)


def matches_package_type(
    is_system: bool,
    package_type: str | None,
    package_name: str | None = None,
) -> bool:
    if package_type == PACKAGE_TYPE_SYSTEM:
        return is_system
    if package_type == PACKAGE_TYPE_USER:
        return not is_system
    if package_type == PACKAGE_TYPE_BLOATWARE:
        if not package_name:
            return False
        return is_bloatware_package(package_name)
    return True
