"""Keyboard module package - Qt6 GUI."""

from mast.core.i18n import _
from mast.qt6.module import Module
from mast.qt6.keyboard.window import KeyboardWindow


class KeyboardModule(Module):
    def __init__(self):
        super().__init__(_("Keyboard"), ("input-keyboard", "preferences-desktop-keyboard"))

    def _create_window(self):
        return KeyboardWindow()


__all__ = ["KeyboardModule"]