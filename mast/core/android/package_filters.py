"""Shared package filter definitions for Android package views."""

from mast.core.i18n import _

PACKAGE_TYPE_ALL = "all"
PACKAGE_TYPE_SYSTEM = "system"
PACKAGE_TYPE_USER = "user"

PACKAGE_TYPE_FILTER_IDS = (
    PACKAGE_TYPE_ALL,
    PACKAGE_TYPE_SYSTEM,
    PACKAGE_TYPE_USER,
)

PACKAGE_TYPE_FILTER_OPTIONS = [
    (PACKAGE_TYPE_ALL, _("All")),
    (PACKAGE_TYPE_SYSTEM, _("System")),
    (PACKAGE_TYPE_USER, _("User")),
]


def matches_package_type(is_system: bool, package_type: str | None) -> bool:
    if package_type == PACKAGE_TYPE_SYSTEM:
        return is_system
    if package_type == PACKAGE_TYPE_USER:
        return not is_system
    return True
