"""TUI openSUSE Build Service module."""

from mast.core.i18n import _
from mast.tui.module import Module
from mast.tui.buildservice.window import BuildServiceWindow


class BuildServiceModule(Module):
    def __init__(self) -> None:
        super().__init__(_("Build Service"), "📦")

    def create_window(self) -> BuildServiceWindow:
        return BuildServiceWindow()


__all__ = ["BuildServiceModule"]