"""Internationalization support using gettext."""

from __future__ import annotations

import gettext
import os
from typing import Callable

APP_NAME = "mast"

# Locale search paths in priority order
LOCALE_DIRS = [
    # AppImage bundle (the runtime exposes the mount point as $APPDIR)
    os.path.join(os.environ["APPDIR"], "usr", "share", "locale")
    if "APPDIR" in os.environ
    else None,
    # Development path (relative to package)
    os.path.join(os.path.dirname(__file__), "..", "..", "locale"),
    # User local installation
    os.path.expanduser("~/.local/share/locale"),
    # System installation paths
    "/usr/local/share/locale",
    "/usr/share/locale",
]

# Drop placeholder entries produced by conditional appends above.
LOCALE_DIRS = [path for path in LOCALE_DIRS if path is not None]

# Type alias for gettext function
_GettextFunc = Callable[[str], str]


class _TranslationWrapper:
    """A callable wrapper that always delegates to the current translation function.

    This ensures that modules importing '_' from this module will always use
    the correct translation function after init_i18n() is called.
    """

    __slots__ = ('_gettext_func',)

    def __init__(self) -> None:
        self._gettext_func: _GettextFunc = gettext.gettext

    def __call__(self, msgid: str) -> str:
        return self._gettext_func(msgid)

    def set_gettext(self, func: _GettextFunc) -> None:
        """Set the underlying gettext function to use."""
        self._gettext_func = func


# Global translation wrapper instance
_: _TranslationWrapper = _TranslationWrapper()


def _find_locale_dir() -> str | None:
    """Find the first locale directory that exists."""
    for localedir in LOCALE_DIRS:
        if os.path.isdir(localedir):
            return localedir
    return None


def init_i18n() -> None:
    """Initialize gettext translations."""
    localedir = _find_locale_dir()

    if localedir is None:
        translation = gettext.NullTranslations()
        _.set_gettext(translation.gettext)
        return

    try:
        translation = gettext.translation(APP_NAME, localedir=localedir)
        _.set_gettext(translation.gettext)
    except FileNotFoundError:
        translation = gettext.NullTranslations()
        _.set_gettext(translation.gettext)

init_i18n()  # Initialize translations at module load time