"""Android module package - GTK4 GUI."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.module import Module
from mast.gtk4.android.window import AndroidWindow


class AndroidModule(Module):
    def __init__(self):
        super().__init__(_("Android"), ("smartphone", "phone"))

    def _create_window(self) -> Gtk.Window:
        return AndroidWindow()


__all__ = ["AndroidModule"]