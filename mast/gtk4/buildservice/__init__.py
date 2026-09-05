"""GTK4 openSUSE Build Service module."""

from mast.core.i18n import _
from mast.gtk4.module import Module
from .window import BuildServiceWindow


class BuildServiceModule(Module):
    def __init__(self) -> None:
        super().__init__(_("Build Service"), ("package-x-generic", "package"))

    def _create_window(self) -> BuildServiceWindow:
        return BuildServiceWindow()


__all__ = ["BuildServiceModule"]