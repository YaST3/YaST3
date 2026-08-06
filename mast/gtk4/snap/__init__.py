"""Snap module package - GTK4 GUI."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.module import Module
from mast.gtk4.snap.window import SnapWindow


class SnapModule(Module):
    def __init__(self):
        super().__init__(_("Snap"), ("snapd", "package-x-generic"))

    def _create_window(self) -> Gtk.Window:
        return SnapWindow()


__all__ = ["SnapModule"]