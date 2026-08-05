"""Keyboard module package - GTK4 GUI."""

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from mast.core.i18n import _
from mast.gtk4.module import Module
from mast.gtk4.keyboard.window import KeyboardWindow


class KeyboardModule(Module):
    def __init__(self):
        super().__init__(_("Keyboard"), ("input-keyboard", "preferences-desktop-keyboard"))

    def _create_window(self) -> Gtk.Window:
        return KeyboardWindow()


__all__ = ["KeyboardModule"]