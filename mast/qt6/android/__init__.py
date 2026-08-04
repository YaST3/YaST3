"""Android module package - Qt6 GUI."""

from mast.core.i18n import _
from mast.qt6.module import Module
from mast.qt6.android.window import AndroidWindow


class AndroidModule(Module):
    def __init__(self):
        super().__init__(_("Android"), ("smartphone", "phone"))

    def _create_window(self):
        return AndroidWindow()


__all__ = ["AndroidModule"]