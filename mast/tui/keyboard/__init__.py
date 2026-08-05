"""Keyboard module package - TUI."""

from textual.screen import Screen

from mast.core.i18n import _
from mast.tui.module import Module
from mast.tui.keyboard.window import KeyboardWindow


class KeyboardModule(Module):
    def __init__(self):
        super().__init__(_("Keyboard"), "⌨️")

    def create_window(self) -> Screen:
        return KeyboardWindow()


__all__ = ["KeyboardModule"]