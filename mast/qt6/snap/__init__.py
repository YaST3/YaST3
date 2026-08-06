"""Snap module package - Qt6 GUI."""

from mast.core.i18n import _
from mast.qt6.module import Module
from mast.qt6.snap.window import SnapWindow


class SnapModule(Module):
    def __init__(self):
        super().__init__(_("Snap"), ("snapd", "package-x-generic"))

    def _create_window(self):
        return SnapWindow()


__all__ = ["SnapModule"]