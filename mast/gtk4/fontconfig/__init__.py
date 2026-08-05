"""Font Config module package - GTK4 GUI."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.fontconfig.window import FontConfigWindow
from mast.gtk4.module import Module


class FontConfigModule(Module):
    def __init__(self):
        super().__init__(_("Font Config"), ("preferences-desktop-font", "preferences-desktop"))

    def _create_window(self) -> Gtk.Window:
        return FontConfigWindow()


__all__ = ["FontConfigModule"]
