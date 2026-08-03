"""Shared package filter definitions for Android package views."""

from __future__ import annotations

APP_TYPE_ALL = "all"
APP_TYPE_SYSTEM = "system"
APP_TYPE_USER = "user"

APP_TYPE_FILTER_IDS = (
    APP_TYPE_ALL,
    APP_TYPE_SYSTEM,
    APP_TYPE_USER,
)

APP_TYPE_FILTER_OPTIONS = [
    (APP_TYPE_ALL, "All"),
    (APP_TYPE_SYSTEM, "System"),
    (APP_TYPE_USER, "User"),
]


def matches_app_type(is_system: bool, app_type: str | None) -> bool:
    if app_type == APP_TYPE_SYSTEM:
        return is_system
    if app_type == APP_TYPE_USER:
        return not is_system
    return True
