"""Qt6 openSUSE Build Service module."""

from .window import BuildServiceWindow
from mast.core.i18n import _
from mast.qt6.module import Module


class BuildServiceModule(Module):
    def __init__(self) -> None:
        super().__init__(_("Build Service"), ("package-x-generic", "package"))

    def _create_window(self) -> BuildServiceWindow:
        return BuildServiceWindow()


__all__ = ["BuildServiceModule"]