"""Flatpak module package - Qt6 GUI."""

from mast.core.i18n import _
from mast.qt6.module import Module
from mast.qt6.flatpak.window import FlatpakWindow


class FlatpakModule(Module):
    def __init__(self):
        super().__init__(_("Flatpak Packages"), ("application-vnd.flatpak.ref", "package-x-generic"))

    def _create_window(self):
        return FlatpakWindow()


__all__ = ["FlatpakModule"]